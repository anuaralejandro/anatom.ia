from pathlib import Path
p=Path(r"C:\Users\datam\Documents\anatom.ia\crates\atlas-core\src\glb.rs")
s=p.read_text(encoding="utf-8")
original=s

def swap(a,b):
    global s
    n=s.count(a)
    if n!=1: raise ValueError("Expected exactly one match, got "+str(n)+": "+a[:100])
    s=s.replace(a,b,1)

swap("const COMPONENT_TYPE_FLOAT: u64 = 5126;",'''const COMPONENT_TYPE_FLOAT: u64 = 5126;

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
    let view_idx: usize = acc.get("bufferView").and_then(Value::as_u64)
        .ok_or_else(|| corrupt("Accessor missing bufferView"))?
        .try_into().map_err(|_| corrupt("Accessor bufferView index exceeds platform size"))?;
    let view = views.get(view_idx).ok_or_else(|| corrupt("Accessor bufferView out of bounds"))?;
    let buffer_idx = view.get("buffer").and_then(Value::as_u64)
        .ok_or_else(|| corrupt("BufferView missing buffer"))?;
    if buffer_idx != 0 {
        return Err(corrupt("Only embedded GLB buffer 0 is supported"));
    }
    let view_offset: usize = view.get("byteOffset").and_then(Value::as_u64).unwrap_or(0)
        .try_into().map_err(|_| corrupt("BufferView offset exceeds platform size"))?;
    let view_len: usize = view.get("byteLength").and_then(Value::as_u64)
        .ok_or_else(|| corrupt("BufferView missing byteLength"))?
        .try_into().map_err(|_| corrupt("BufferView length exceeds platform size"))?;
    let acc_offset: usize = acc.get("byteOffset").and_then(Value::as_u64).unwrap_or(0)
        .try_into().map_err(|_| corrupt("Accessor offset exceeds platform size"))?;
    let stride: usize = view.get("byteStride").and_then(Value::as_u64)
        .unwrap_or(element_bytes as u64)
        .try_into().map_err(|_| corrupt("BufferView stride exceeds platform size"))?;
    if stride < element_bytes || stride > 4096 || stride % 4 != 0
        || view_offset % 4 != 0 || acc_offset % 4 != 0 {
        return Err(corrupt("Invalid accessor alignment or stride"));
    }
    let required_bytes = if count == 0 { 0 } else {
        (count - 1).checked_mul(stride)
            .and_then(|n| n.checked_add(element_bytes))
            .ok_or_else(|| corrupt("Accessor size overflow"))?
    };
    let end_in_view = acc_offset.checked_add(required_bytes)
        .ok_or_else(|| corrupt("Accessor offset overflow"))?;
    let end_of_view = view_offset.checked_add(view_len)
        .ok_or_else(|| corrupt("BufferView size overflow"))?;
    let start = view_offset.checked_add(acc_offset)
        .ok_or_else(|| corrupt("BufferView/accessor offset overflow"))?;
    let end = start.checked_add(required_bytes)
        .ok_or_else(|| corrupt("Accessor end overflow"))?;
    if end_in_view > view_len || end_of_view > bin_len || end > bin_len {
        return Err(corrupt("Accessor exceeds its bufferView or GLB binary payload"));
    }
    Ok((start, stride))
}
''')
swap('''    if bytes.len() < 12 {
        return Err(EngineError::new(''','''    if bytes.len() > MAX_GLB_BYTES {
        return Err(corrupt("GLB exceeds per-package size limit"));
    }
    if bytes.len() < 12 {
        return Err(EngineError::new(''')
swap('''    if bytes.len() < total_length {''','''    if bytes.len() != total_length {''')
swap('''    // Read chunks
    let mut offset = 12;''','''    // Read chunks; GLB chunk lengths are required to be multiples of four.
    let mut offset = 12;''')
swap('''    while offset + 8 <= total_length {
        let chunk_length =
            u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap()) as usize;
        let chunk_type = u32::from_le_bytes(bytes[offset + 4..offset + 8].try_into().unwrap());
        offset += 8;

        if offset + chunk_length > total_length {''','''    while offset.checked_add(8).is_some_and(|n| n <= total_length) {
        let chunk_length =
            u32::from_le_bytes(bytes[offset..offset + 4].try_into().unwrap()) as usize;
        let chunk_type = u32::from_le_bytes(bytes[offset + 4..offset + 8].try_into().unwrap());
        offset += 8;

        if chunk_length % 4 != 0
            || offset.checked_add(chunk_length).is_none_or(|n| n > total_length) {''')
swap('''    let json_bytes = json_data.ok_or_else(|| {''','''    if offset != total_length {
        return Err(corrupt("GLB contains trailing or truncated chunk header"));
    }
    let json_bytes = json_data.ok_or_else(|| {''')
swap('''    let bin = bin_data.unwrap_or(&[]);''','''    if json_bytes.len() > MAX_JSON_BYTES {
        return Err(corrupt("GLB JSON exceeds metadata size limit"));
    }
    let bin = bin_data.unwrap_or(&[]);''')
swap('''    parse_gltf_structure(&gltf, bin)
}''','''    if gltf.get("extensionsRequired").and_then(Value::as_array)
        .is_some_and(|extensions| !extensions.is_empty()) {
        return Err(EngineError::new(
            ErrorCode::AssetUnsupportedExtension,
            "This core-only prototype does not decode required glTF extensions",
            false,
        ));
    }
    if let Some(buffers) = gltf.get("buffers").and_then(Value::as_array) {
        if buffers.len() != 1 || buffers[0].get("uri").is_some() {
            return Err(corrupt("Only a single embedded GLB BIN buffer is supported"));
        }
        let declared: usize = buffers[0].get("byteLength").and_then(Value::as_u64)
            .ok_or_else(|| corrupt("GLB buffer missing byteLength"))?
            .try_into().map_err(|_| corrupt("GLB buffer exceeds platform size"))?;
        if declared > bin.len() || bin.len().saturating_sub(declared) > 3 {
            return Err(corrupt("GLB binary payload differs from buffer declared size"));
        }
    } else {
        return Err(corrupt("GLB missing buffers array"));
    }
    parse_gltf_structure(&gltf, bin)
}''')
start=s.index("    // Helper to read accessor data")
end=s.index("    // 3. Materials",start)
s=s[:start]+'''    // Strict accessor decoding; no unchecked multiplications or unbounded reserves.
    let read_accessor_floats = |acc_idx: usize, expected_type: &str|
        -> Result<Vec<f32>, EngineError> {
        let acc = accessors.get(acc_idx).ok_or_else(|| corrupt("Accessor index out of bounds"))?;
        let count: usize = acc.get("count").and_then(Value::as_u64)
            .ok_or_else(|| corrupt("Accessor missing count"))?
            .try_into().map_err(|_| corrupt("Accessor count exceeds platform size"))?;
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
            "SCALAR" => 1, "VEC2" => 2, "VEC3" => 3, "VEC4" => 4,
            _ => return Err(corrupt("Unsupported accessor shape")),
        };
        let total = count.checked_mul(comps).ok_or_else(|| corrupt("Accessor float count overflow"))?;
        let (start, stride) = accessor_window(acc, buffer_views, bin.len(), comps * 4, count)?;
        let mut floats = Vec::with_capacity(total);
        for i in 0..count {
            let base = start + i * stride;
            for c in 0..comps {
                let idx = base + c * 4;
                let val = f32::from_le_bytes(bin[idx..idx + 4].try_into().unwrap());
                if !val.is_finite() { return Err(corrupt("Non-finite accessor float")); }
                floats.push(val);
            }
        }
        Ok(floats)
    };

    let read_indices = |acc_idx: usize| -> Result<Vec<u32>, EngineError> {
        let acc = accessors.get(acc_idx).ok_or_else(|| corrupt("Accessor index out of bounds"))?;
        let count: usize = acc.get("count").and_then(Value::as_u64)
            .ok_or_else(|| corrupt("Index accessor missing count"))?
            .try_into().map_err(|_| corrupt("Index count exceeds platform size"))?;
        if count > MAX_ACCESSOR_ELEMENTS {
            return Err(corrupt("Index accessor exceeds element limit"));
        }
        if count % 3 != 0 { return Err(corrupt("TRIANGLES index count must be divisible by 3")); }
        let component = acc.get("componentType").and_then(Value::as_u64)
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
                u16::from_le_bytes(bin[idx..idx+2].try_into().unwrap()) as u32
            } else {
                u32::from_le_bytes(bin[idx..idx+4].try_into().unwrap())
            };
            indices.push(val);
        }
        Ok(indices)
    };

'''+s[end:]
# Inline mesh & node count protection.
swap('''    let mut meshes = Vec::with_capacity(gltf_meshes.len());''','''    if gltf_meshes.len() > MAX_SCENE_NODES {
        return Err(corrupt("GLB has too many meshes"));
    }
    let mut meshes = Vec::with_capacity(gltf_meshes.len());''')
swap('''        let mut primitives = Vec::with_capacity(primitives_arr.len());''','''        if primitives_arr.len() > MAX_SCENE_NODES {
            return Err(corrupt("GLB mesh has too many primitives"));
        }
        let mut primitives = Vec::with_capacity(primitives_arr.len());''')
swap('''    let mut nodes = Vec::with_capacity(gltf_nodes.len());''','''    if gltf_nodes.len() > MAX_SCENE_NODES {
        return Err(corrupt("GLB has too many nodes"));
    }
    let mut nodes = Vec::with_capacity(gltf_nodes.len());''')
# Validate index before get_structure_bounds etc.
swap('''        let mesh_index = node_val
            .get("mesh")
            .and_then(|v| v.as_u64())
            .map(|v| v as usize);''','''        let mesh_index = node_val
            .get("mesh")
            .and_then(Value::as_u64)
            .map(|v| usize::try_from(v).map_err(|_| corrupt("Mesh index too large")))
            .transpose()?;
        if mesh_index.is_some_and(|idx| idx >= meshes.len()) {
            return Err(corrupt("Node references missing mesh"));
        }''')
# Guard matrix malformed
swap('''            if mat_arr.len() == 16 {
                let mut m = [0.0f32; 16];
                for i in 0..16 {
                    m[i] = mat_arr[i].as_f64().unwrap_or(0.0) as f32;
                }
                Mat4::from_cols_array(&m)
            } else {
                Mat4::IDENTITY
            }''','''            if mat_arr.len() != 16 {
                return Err(corrupt("Node matrix must have 16 values"));
            }
            let mut m = [0.0f32; 16];
            for i in 0..16 {
                m[i] = mat_arr[i].as_f64().ok_or_else(|| corrupt("Invalid node matrix value"))? as f32;
                if !m[i].is_finite() { return Err(corrupt("Non-finite node matrix")); }
            }
            Mat4::from_cols_array(&m)''')
# t/r/s bounds and finite through precheck (avoids index panic)
swap('''        } else {
            let translation =
                if let Some(t) = node_val.get("translation").and_then(|v| v.as_array()) {''','''        } else {
            for (key, expected) in [("translation", 3), ("rotation", 4), ("scale", 3)] {
                if let Some(arr) = node_val.get(key) {
                    let vals = arr.as_array().ok_or_else(|| corrupt("Node TRS must be arrays"))?;
                    if vals.len() != expected || vals.iter().any(|v| v.as_f64().is_none_or(|v| !v.is_finite())) {
                        return Err(corrupt(format!("Invalid node {} values", key)));
                    }
                }
            }
            let translation =
                if let Some(t) = node_val.get("translation").and_then(|v| v.as_array()) {''')
swap('''                    children.push(c);
                    child_to_parent.insert(c, node_idx);''','''                    if c >= gltf_nodes.len() || c == node_idx {
                        return Err(corrupt("Invalid or self-referential child node index"));
                    }
                    if child_to_parent.insert(c, node_idx).is_some() {
                        return Err(corrupt("Node cannot have multiple parents"));
                    }
                    children.push(c);''')
swap('''                root_nodes.push(n_idx as usize);''','''                let index: usize = n_idx.try_into().map_err(|_| corrupt("Scene root index too large"))?;
                if index >= nodes.len() { return Err(corrupt("Scene root out of bounds")); }
                root_nodes.push(index);''')
swap('''    let mut scene = Scene {
        nodes,''','''    // Reject cycles and extreme hierarchy depth before recursive world transforms.
    fn verify_graph(nodes: &[Node], idx: usize, depth: usize, color: &mut [u8]) -> Result<(), EngineError> {
        if depth > MAX_GRAPH_DEPTH { return Err(corrupt("GLB node hierarchy exceeds depth limit")); }
        if color[idx] == 1 { return Err(corrupt("GLB cyclic node graph")); }
        if color[idx] == 2 { return Ok(()); }
        color[idx] = 1;
        for &child in &nodes[idx].children {
            verify_graph(nodes, child, depth + 1, color)?;
        }
        color[idx] = 2;
        Ok(())
    }
    let mut color = vec![0u8; nodes.len()];
    for i in 0..nodes.len() {
        if color[i] == 0 { verify_graph(&nodes, i, 0, &mut color)?; }
    }

    let mut scene = Scene {
        nodes,''')
# Reject invalid material refs
swap('''            let material_index = prim_val
                .get("material")
                .and_then(|v| v.as_u64())
                .map(|v| v as usize);

            primitives.push(Primitive {''','''            let material_index = prim_val.get("material").and_then(Value::as_u64)
                .map(|v| usize::try_from(v).map_err(|_| corrupt("Material index too large")))
                .transpose()?;
            if material_index.is_some_and(|idx| idx >= materials.len()) {
                return Err(corrupt("Primitive material reference out of bounds"));
            }

            primitives.push(Primitive {''')
# write patch
p.write_text(s,encoding="utf-8")
print("PATCHED",p,"size",len(original),"->",len(s),"lines",s.count("\n"))
