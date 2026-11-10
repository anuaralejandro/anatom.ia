use std::collections::HashMap;

use glam::{Mat4, Quat, Vec3};
use serde_json::Value;

use crate::scene::{AABB, Material, Mesh, Node, Primitive, Scene, Vertex};
use crate::types::{EngineError, ErrorCode};

const GLB_MAGIC: u32 = 0x4654_6C67; // "glTF"
const CHUNK_TYPE_JSON: u32 = 0x4E4F_534A; // "JSON"
const CHUNK_TYPE_BIN: u32 = 0x004E_4942; // "BIN\0"

const COMPONENT_TYPE_UNSIGNED_SHORT: u64 = 5123;
const COMPONENT_TYPE_UNSIGNED_INT: u64 = 5125;
const COMPONENT_TYPE_FLOAT: u64 = 5126;

// Conservative limits for a single *region* asset, not the whole anatomical atlas.
// A production builder must split larger releases into separately validated packages.
const MAX_GLB_BYTES: usize = 64 * 1024 * 1024;
const MAX_JSON_BYTES: usize = 8 * 1024 * 1024;
const MAX_ACCESSOR_ELEMENTS: usize = 5_000_000;
const MAX_SCENE_NODES: usize = 100_000;
const MAX_GRAPH_DEPTH: usize = 256;

fn corrupt(detail: impl Into<String>) -> EngineError {
    EngineError::new(ErrorCode::AssetCorrupt, detail, false)
}

// Reject malicious offsets/strides/lengths *before* allocating a Vec or slicing BIN.
fn accessor_window(
    acc: &Value,
    views: &[Value],
    bin_len: usize,
    element_bytes: usize,
    count: usize,
) -> Result<(usize, usize), EngineError> {
    let view_idx: usize = acc
        .get("bufferView")
        .and_then(Value::as_u64)
        .ok_or_else(|| corrupt("Accessor missing bufferView"))?
        .try_into()
        .map_err(|_| corrupt("Accessor bufferView index exceeds platform size"))?;
    let view = views
        .get(view_idx)
        .ok_or_else(|| corrupt("Accessor bufferView out of bounds"))?;
    let buffer_idx = view
        .get("buffer")
        .and_then(Value::as_u64)
        .ok_or_else(|| corrupt("BufferView missing buffer"))?;
    if buffer_idx != 0 {
        return Err(corrupt("Only embedded GLB buffer 0 is supported"));
    }
    let view_offset: usize = view
        .get("byteOffset")
        .and_then(Value::as_u64)
        .unwrap_or(0)
        .try_into()
        .map_err(|_| corrupt("BufferView offset exceeds platform size"))?;
    let view_len: usize = view
        .get("byteLength")
        .and_then(Value::as_u64)
        .ok_or_else(|| corrupt("BufferView missing byteLength"))?
        .try_into()
        .map_err(|_| corrupt("BufferView length exceeds platform size"))?;
    let acc_offset: usize = acc
        .get("byteOffset")
        .and_then(Value::as_u64)
        .unwrap_or(0)
        .try_into()
        .map_err(|_| corrupt("Accessor offset exceeds platform size"))?;
    let stride: usize = view
        .get("byteStride")
        .and_then(Value::as_u64)
        .unwrap_or(element_bytes as u64)
        .try_into()
        .map_err(|_| corrupt("BufferView stride exceeds platform size"))?;
    // Packed u16 index accessors have a natural two-byte stride; only
    // *explicit* interleaved byteStride is required to align to four bytes.
    let alignment = if element_bytes == 2 { 2 } else { 4 };
    if stride < element_bytes
        || stride > 4096
        || (view.get("byteStride").is_some() && !stride.is_multiple_of(4))
        || !view_offset.is_multiple_of(4)
        || !acc_offset.is_multiple_of(alignment)
    {
        return Err(corrupt("Invalid accessor alignment or stride"));
    }
    let required_bytes = if count == 0 {
        0
    } else {
        (count - 1)
            .checked_mul(stride)
            .and_then(|n| n.checked_add(element_bytes))
            .ok_or_else(|| corrupt("Accessor size overflow"))?
    };
    let end_in_view = acc_offset
        .checked_add(required_bytes)
        .ok_or_else(|| corrupt("Accessor offset overflow"))?;
    let end_of_view = view_offset
        .checked_add(view_len)
        .ok_or_else(|| corrupt("BufferView size overflow"))?;
    let start = view_offset
        .checked_add(acc_offset)
        .ok_or_else(|| corrupt("BufferView/accessor offset overflow"))?;
    let end = start
        .checked_add(required_bytes)
        .ok_or_else(|| corrupt("Accessor end overflow"))?;
    if end_in_view > view_len || end_of_view > bin_len || end > bin_len {
        return Err(corrupt(
            "Accessor exceeds its bufferView or GLB binary payload",
        ));
    }
    Ok((start, stride))
}

pub fn parse_glb(bytes: &[u8]) -> Result<Scene, EngineError> {
    if bytes.len() > MAX_GLB_BYTES {
        return Err(corrupt("GLB exceeds per-package size limit"));
    }
    if bytes.len() < 12 {
        return Err(EngineError::new(
            ErrorCode::AssetCorrupt,
            "GLB file too small to contain a valid header (< 12 bytes)",
            false,
        ));
    }

    let magic = u32::from_le_bytes(bytes[0..4].try_into().unwrap());
    if magic != GLB_MAGIC {
        return Err(EngineError::new(
            ErrorCode::AssetCorrupt,
            format!(
                "Invalid GLB magic: expected 0x46546C67, found 0x{:08X}",
                magic
            ),
            false,
        ));
    }

    let version = u32::from_le_bytes(bytes[4..8].try_into().unwrap());
    if version != 2 {
        return Err(EngineError::new(
            ErrorCode::AssetUnsupportedExtension,
            format!("Unsupported glTF version: {}", version),
            false,
        ));
    }

    let total_length = u32::from_le_bytes(bytes[8..12].try_into().unwrap()) as usize;
    if bytes.len() != total_length {
        return Err(EngineError::new(
            ErrorCode::AssetCorrupt,
            format!(
                "Truncated GLB: header specifies {} bytes, but buffer has {} bytes",
                total_length,
                bytes.len()
            ),
            false,
        ));
    }

    // Read chunks; GLB chunk lengths are required to be multiples of four.
    let mut offset: usize = 12;
    let mut json_data: Option<&[u8]> = None;
    let mut bin_data: Option<&[u8]> = None;

    while offset.checked_add(8).is_some_and(|n| n <= total_length) {
        let chunk_length =
            u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap()) as usize;
        let chunk_type = u32::from_le_bytes(bytes[offset + 4..offset + 8].try_into().unwrap());
        offset += 8;

        if !chunk_length.is_multiple_of(4)
            || offset
                .checked_add(chunk_length)
                .is_none_or(|n| n > total_length)
        {
            return Err(EngineError::new(
                ErrorCode::AssetCorrupt,
                "GLB chunk exceeds total file length",
                false,
            ));
        }

        let chunk_bytes = &bytes[offset..offset + chunk_length];
        offset += chunk_length;

        match chunk_type {
            CHUNK_TYPE_JSON if json_data.is_none() => {
                json_data = Some(chunk_bytes);
            }
            CHUNK_TYPE_BIN if bin_data.is_none() => {
                bin_data = Some(chunk_bytes);
            }
            _ => {
                // Ignore unknown or duplicate chunk types per glTF specification
            }
        }
    }

    if offset != total_length {
        return Err(corrupt("GLB contains trailing or truncated chunk header"));
    }
    let json_bytes = json_data.ok_or_else(|| {
        EngineError::new(
            ErrorCode::AssetCorrupt,
            "GLB missing required JSON chunk",
            false,
        )
    })?;

    if json_bytes.len() > MAX_JSON_BYTES {
        return Err(corrupt("GLB JSON exceeds metadata size limit"));
    }
    let bin = bin_data.unwrap_or(&[]);

    let gltf: Value = serde_json::from_slice(json_bytes).map_err(|e| {
        EngineError::new(
            ErrorCode::AssetCorrupt,
            format!("Invalid JSON in glTF chunk: {}", e),
            false,
        )
    })?;

    if gltf
        .get("extensionsRequired")
        .and_then(Value::as_array)
        .is_some_and(|extensions| !extensions.is_empty())
    {
        return Err(EngineError::new(
            ErrorCode::AssetUnsupportedExtension,
            "This core-only prototype does not decode required glTF extensions",
            false,
        ));
    }
    if let Some(buffers) = gltf.get("buffers").and_then(Value::as_array) {
        if buffers.len() != 1 || buffers[0].get("uri").is_some() {
            return Err(corrupt(
                "Only a single embedded GLB BIN buffer is supported",
            ));
        }
        let declared: usize = buffers[0]
            .get("byteLength")
            .and_then(Value::as_u64)
            .ok_or_else(|| corrupt("GLB buffer missing byteLength"))?
            .try_into()
            .map_err(|_| corrupt("GLB buffer exceeds platform size"))?;
        if declared > bin.len() || bin.len().saturating_sub(declared) > 3 {
            return Err(corrupt(
                "GLB binary payload differs from buffer declared size",
            ));
        }
    } else {
        return Err(corrupt("GLB missing buffers array"));
    }
    parse_gltf_structure(&gltf, bin)
}

fn parse_gltf_structure(gltf: &Value, bin: &[u8]) -> Result<Scene, EngineError> {
    // 1. Buffer Views
    let buffer_views = gltf
        .get("bufferViews")
        .and_then(|v| v.as_array())
        .ok_or_else(|| {
            EngineError::new(
                ErrorCode::AssetCorrupt,
                "Missing bufferViews in glTF",
                false,
            )
        })?;

    // 2. Accessors
    let accessors = gltf
        .get("accessors")
        .and_then(|v| v.as_array())
        .ok_or_else(|| {
            EngineError::new(ErrorCode::AssetCorrupt, "Missing accessors in glTF", false)
        })?;

    // Strict accessor decoding; no unchecked multiplications or unbounded reserves.
    let read_accessor_floats =
        |acc_idx: usize, expected_type: &str| -> Result<Vec<f32>, EngineError> {
            let acc = accessors
                .get(acc_idx)
                .ok_or_else(|| corrupt("Accessor index out of bounds"))?;
            let count: usize = acc
                .get("count")
                .and_then(Value::as_u64)
                .ok_or_else(|| corrupt("Accessor missing count"))?
                .try_into()
                .map_err(|_| corrupt("Accessor count exceeds platform size"))?;
            if count > MAX_ACCESSOR_ELEMENTS {
                return Err(corrupt("Accessor exceeds element limit"));
            }
            if acc.get("componentType").and_then(Value::as_u64) != Some(COMPONENT_TYPE_FLOAT) {
                return Err(corrupt("Unsupported float accessor component type"));
            }
            if acc.get("type").and_then(Value::as_str) != Some(expected_type) {
                return Err(corrupt("Accessor type mismatch"));
            }
            let comps: usize = match expected_type {
                "SCALAR" => 1,
                "VEC2" => 2,
                "VEC3" => 3,
                "VEC4" => 4,
                _ => return Err(corrupt("Unsupported accessor shape")),
            };
            let total = count
                .checked_mul(comps)
                .ok_or_else(|| corrupt("Accessor float count overflow"))?;
            let (start, stride) = accessor_window(acc, buffer_views, bin.len(), comps * 4, count)?;
            let mut floats = Vec::with_capacity(total);
            for i in 0..count {
                let base = start + i * stride;
                for c in 0..comps {
                    let idx = base + c * 4;
                    let val = f32::from_le_bytes(bin[idx..idx + 4].try_into().unwrap());
                    if !val.is_finite() {
                        return Err(corrupt("Non-finite accessor float"));
                    }
                    floats.push(val);
                }
            }
            Ok(floats)
        };

    let read_indices = |acc_idx: usize| -> Result<Vec<u32>, EngineError> {
        let acc = accessors
            .get(acc_idx)
            .ok_or_else(|| corrupt("Accessor index out of bounds"))?;
        let count: usize = acc
            .get("count")
            .and_then(Value::as_u64)
            .ok_or_else(|| corrupt("Index accessor missing count"))?
            .try_into()
            .map_err(|_| corrupt("Index count exceeds platform size"))?;
        if count > MAX_ACCESSOR_ELEMENTS {
            return Err(corrupt("Index accessor exceeds element limit"));
        }
        if !count.is_multiple_of(3) {
            return Err(corrupt("TRIANGLES index count must be divisible by 3"));
        }
        let component = acc
            .get("componentType")
            .and_then(Value::as_u64)
            .ok_or_else(|| corrupt("Index accessor missing componentType"))?;
        if acc.get("type").and_then(Value::as_str) != Some("SCALAR") {
            return Err(corrupt("Indices must be SCALAR"));
        }
        let elem_bytes = match component {
            COMPONENT_TYPE_UNSIGNED_SHORT => 2,
            COMPONENT_TYPE_UNSIGNED_INT => 4,
            _ => return Err(corrupt("Unsupported index component type")),
        };
        let (start, stride) = accessor_window(acc, buffer_views, bin.len(), elem_bytes, count)?;
        let mut indices = Vec::with_capacity(count);
        for i in 0..count {
            let idx = start + i * stride;
            let val = if elem_bytes == 2 {
                u16::from_le_bytes(bin[idx..idx + 2].try_into().unwrap()) as u32
            } else {
                u32::from_le_bytes(bin[idx..idx + 4].try_into().unwrap())
            };
            indices.push(val);
        }
        Ok(indices)
    };

    // 3. Materials
    let mut materials = Vec::new();
    if let Some(mats) = gltf.get("materials").and_then(|v| v.as_array()) {
        for mat in mats {
            let name = mat.get("name").and_then(|v| v.as_str()).map(String::from);
            let double_sided = mat
                .get("doubleSided")
                .and_then(|v| v.as_bool())
                .unwrap_or(true);

            let mut base_color = [0.8f32, 0.8, 0.8, 1.0];
            let mut roughness = 0.5f32;
            let mut metallic = 0.0f32;

            if let Some(pbr) = mat.get("pbrMetallicRoughness") {
                if let Some(bc) = pbr
                    .get("baseColorFactor")
                    .and_then(|v| v.as_array())
                    .filter(|a| a.len() >= 4)
                {
                    base_color[0] = bc[0].as_f64().unwrap_or(0.8) as f32;
                    base_color[1] = bc[1].as_f64().unwrap_or(0.8) as f32;
                    base_color[2] = bc[2].as_f64().unwrap_or(0.8) as f32;
                    base_color[3] = bc[3].as_f64().unwrap_or(1.0) as f32;
                }
                if let Some(rf) = pbr.get("roughnessFactor").and_then(|v| v.as_f64()) {
                    roughness = rf as f32;
                }
                if let Some(mf) = pbr.get("metallicFactor").and_then(|v| v.as_f64()) {
                    metallic = mf as f32;
                }
            }

            materials.push(Material {
                name,
                base_color,
                roughness,
                metallic,
                double_sided,
            });
        }
    }
    if materials.is_empty() {
        materials.push(Material::default());
    }

    // 4. Meshes
    let gltf_meshes = gltf
        .get("meshes")
        .and_then(|v| v.as_array())
        .ok_or_else(|| {
            EngineError::new(ErrorCode::AssetCorrupt, "Missing meshes in glTF", false)
        })?;

    if gltf_meshes.len() > MAX_SCENE_NODES {
        return Err(corrupt("GLB has too many meshes"));
    }
    let mut meshes = Vec::with_capacity(gltf_meshes.len());

    for mesh_val in gltf_meshes {
        let name = mesh_val
            .get("name")
            .and_then(|v| v.as_str())
            .map(String::from);
        let primitives_arr = mesh_val
            .get("primitives")
            .and_then(|v| v.as_array())
            .ok_or_else(|| {
                EngineError::new(ErrorCode::AssetCorrupt, "Mesh missing primitives", false)
            })?;

        if primitives_arr.len() > MAX_SCENE_NODES {
            return Err(corrupt("GLB mesh has too many primitives"));
        }
        let mut primitives = Vec::with_capacity(primitives_arr.len());

        for prim_val in primitives_arr {
            let mode = prim_val.get("mode").and_then(|v| v.as_u64()).unwrap_or(4);
            if mode != 4 {
                return Err(EngineError::new(
                    ErrorCode::AssetUnsupportedExtension,
                    format!(
                        "Unsupported primitive mode: expected 4 (TRIANGLES), got {}",
                        mode
                    ),
                    false,
                ));
            }

            let attributes = prim_val.get("attributes").ok_or_else(|| {
                EngineError::new(
                    ErrorCode::AssetCorrupt,
                    "Primitive missing attributes",
                    false,
                )
            })?;

            let pos_acc = attributes
                .get("POSITION")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| {
                    EngineError::new(
                        ErrorCode::AssetCorrupt,
                        "Primitive missing POSITION attribute",
                        false,
                    )
                })? as usize;

            let norm_acc = attributes
                .get("NORMAL")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| {
                    EngineError::new(
                        ErrorCode::AssetCorrupt,
                        "Primitive missing NORMAL attribute",
                        false,
                    )
                })? as usize;

            let pos_floats = read_accessor_floats(pos_acc, "VEC3")?;
            let norm_floats = read_accessor_floats(norm_acc, "VEC3")?;

            if pos_floats.len() != norm_floats.len() {
                return Err(EngineError::new(
                    ErrorCode::AssetCorrupt,
                    "POSITION and NORMAL attribute counts mismatch",
                    false,
                ));
            }

            let vertex_count = pos_floats.len() / 3;
            let mut vertices = Vec::with_capacity(vertex_count);
            let mut bounds = AABB::default();

            for i in 0..vertex_count {
                let px = pos_floats[i * 3];
                let py = pos_floats[i * 3 + 1];
                let pz = pos_floats[i * 3 + 2];

                let nx = norm_floats[i * 3];
                let ny = norm_floats[i * 3 + 1];
                let nz = norm_floats[i * 3 + 2];

                let pos_v = Vec3::new(px, py, pz);
                bounds.expand(pos_v);

                vertices.push(Vertex {
                    position: [px, py, pz],
                    normal: [nx, ny, nz],
                });
            }

            let indices_acc = prim_val
                .get("indices")
                .and_then(|v| v.as_u64())
                .ok_or_else(|| {
                    EngineError::new(ErrorCode::AssetCorrupt, "Primitive missing indices", false)
                })? as usize;

            let indices = read_indices(indices_acc)?;

            // Verify indices are within bounds of vertex array
            for &idx in &indices {
                if idx as usize >= vertex_count {
                    return Err(EngineError::new(
                        ErrorCode::AssetCorrupt,
                        format!("Index {} exceeds vertex count {}", idx, vertex_count),
                        false,
                    ));
                }
            }

            let material_index = prim_val
                .get("material")
                .and_then(Value::as_u64)
                .map(|v| usize::try_from(v).map_err(|_| corrupt("Material index too large")))
                .transpose()?;
            if material_index.is_some_and(|idx| idx >= materials.len()) {
                return Err(corrupt("Primitive material reference out of bounds"));
            }

            primitives.push(Primitive {
                vertices,
                indices,
                material_index,
                bounds,
            });
        }

        meshes.push(Mesh { name, primitives });
    }

    // 5. Nodes
    let gltf_nodes = gltf
        .get("nodes")
        .and_then(|v| v.as_array())
        .ok_or_else(|| EngineError::new(ErrorCode::AssetCorrupt, "Missing nodes in glTF", false))?;

    if gltf_nodes.len() > MAX_SCENE_NODES {
        return Err(corrupt("GLB has too many nodes"));
    }
    let mut nodes = Vec::with_capacity(gltf_nodes.len());
    let mut child_to_parent: HashMap<usize, usize> = HashMap::new();

    for (node_idx, node_val) in gltf_nodes.iter().enumerate() {
        let name = node_val
            .get("name")
            .and_then(|v| v.as_str())
            .map(String::from);

        // Extract extras.atlas_id
        let anatomy_id = node_val
            .get("extras")
            .and_then(|e| e.get("atlas_id"))
            .and_then(|v| v.as_str())
            .map(String::from);

        let mesh_index = node_val
            .get("mesh")
            .and_then(Value::as_u64)
            .map(|v| usize::try_from(v).map_err(|_| corrupt("Mesh index too large")))
            .transpose()?;
        if mesh_index.is_some_and(|idx| idx >= meshes.len()) {
            return Err(corrupt("Node references missing mesh"));
        }

        // Transform: matrix or TRS
        let local_transform = if let Some(mat_arr) =
            node_val.get("matrix").and_then(|v| v.as_array())
        {
            if mat_arr.len() != 16 {
                return Err(corrupt("Node matrix must have 16 values"));
            }
            let mut m = [0.0f32; 16];
            for i in 0..16 {
                m[i] = mat_arr[i]
                    .as_f64()
                    .ok_or_else(|| corrupt("Invalid node matrix value"))?
                    as f32;
                if !m[i].is_finite() {
                    return Err(corrupt("Non-finite node matrix"));
                }
            }
            Mat4::from_cols_array(&m)
        } else {
            for (key, expected) in [("translation", 3), ("rotation", 4), ("scale", 3)] {
                if let Some(arr) = node_val.get(key) {
                    let vals = arr
                        .as_array()
                        .ok_or_else(|| corrupt("Node TRS must be arrays"))?;
                    if vals.len() != expected
                        || vals
                            .iter()
                            .any(|v| v.as_f64().is_none_or(|v| !v.is_finite()))
                    {
                        return Err(corrupt(format!("Invalid node {} values", key)));
                    }
                }
            }
            let translation =
                if let Some(t) = node_val.get("translation").and_then(|v| v.as_array()) {
                    Vec3::new(
                        t[0].as_f64().unwrap_or(0.0) as f32,
                        t[1].as_f64().unwrap_or(0.0) as f32,
                        t[2].as_f64().unwrap_or(0.0) as f32,
                    )
                } else {
                    Vec3::ZERO
                };

            let rotation = if let Some(r) = node_val.get("rotation").and_then(|v| v.as_array()) {
                Quat::from_xyzw(
                    r[0].as_f64().unwrap_or(0.0) as f32,
                    r[1].as_f64().unwrap_or(0.0) as f32,
                    r[2].as_f64().unwrap_or(0.0) as f32,
                    r[3].as_f64().unwrap_or(1.0) as f32,
                )
            } else {
                Quat::IDENTITY
            };

            let scale = if let Some(s) = node_val.get("scale").and_then(|v| v.as_array()) {
                Vec3::new(
                    s[0].as_f64().unwrap_or(1.0) as f32,
                    s[1].as_f64().unwrap_or(1.0) as f32,
                    s[2].as_f64().unwrap_or(1.0) as f32,
                )
            } else {
                Vec3::ONE
            };

            Mat4::from_scale_rotation_translation(scale, rotation, translation)
        };

        let mut children = Vec::new();
        if let Some(ch_arr) = node_val.get("children").and_then(|v| v.as_array()) {
            for ch in ch_arr {
                if let Some(c_idx) = ch.as_u64() {
                    let c = c_idx as usize;
                    if c >= gltf_nodes.len() || c == node_idx {
                        return Err(corrupt("Invalid or self-referential child node index"));
                    }
                    if child_to_parent.insert(c, node_idx).is_some() {
                        return Err(corrupt("Node cannot have multiple parents"));
                    }
                    children.push(c);
                }
            }
        }

        nodes.push(Node {
            name,
            anatomy_id,
            mesh_index,
            local_transform,
            world_transform: local_transform,
            children,
            visible: true,
        });
    }

    // Determine root nodes
    let mut root_nodes = Vec::new();
    let active_scene_idx = gltf.get("scene").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    if let Some(sc_nodes) = gltf
        .get("scenes")
        .and_then(|v| v.as_array())
        .and_then(|scenes| scenes.get(active_scene_idx))
        .and_then(|sc| sc.get("nodes"))
        .and_then(|v| v.as_array())
    {
        for n in sc_nodes {
            if let Some(n_idx) = n.as_u64() {
                let index: usize = n_idx
                    .try_into()
                    .map_err(|_| corrupt("Scene root index too large"))?;
                if index >= nodes.len() {
                    return Err(corrupt("Scene root out of bounds"));
                }
                root_nodes.push(index);
            }
        }
    }

    if root_nodes.is_empty() {
        for i in 0..nodes.len() {
            if !child_to_parent.contains_key(&i) {
                root_nodes.push(i);
            }
        }
    }

    // Reject cycles and extreme hierarchy depth before recursive world transforms.
    fn verify_graph(
        nodes: &[Node],
        idx: usize,
        depth: usize,
        color: &mut [u8],
    ) -> Result<(), EngineError> {
        if depth > MAX_GRAPH_DEPTH {
            return Err(corrupt("GLB node hierarchy exceeds depth limit"));
        }
        if color[idx] == 1 {
            return Err(corrupt("GLB cyclic node graph"));
        }
        if color[idx] == 2 {
            return Ok(());
        }
        color[idx] = 1;
        for &child in &nodes[idx].children {
            verify_graph(nodes, child, depth + 1, color)?;
        }
        color[idx] = 2;
        Ok(())
    }
    let mut color = vec![0u8; nodes.len()];
    for i in 0..nodes.len() {
        if color[i] == 0 {
            verify_graph(&nodes, i, 0, &mut color)?;
        }
    }

    let mut scene = Scene {
        nodes,
        meshes,
        materials,
        root_nodes,
        selected_id: None,
        bounds: AABB::default(),
        revision: 1,
    };

    scene.update_world_transforms();
    Ok(scene)
}
