//! Adversarial tests for rejected glTF/GLB inputs, not just corrupt headers.
use std::fs;
use std::path::PathBuf;

use atlas_core::glb::parse_glb;
use serde_json::{Value, json};

fn baseline() -> Vec<u8> {
    let root = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    fs::read(
        root.parent()
            .unwrap()
            .parent()
            .unwrap()
            .join("reports/experimental/pelvis-pbr-core-compat.glb"),
    )
    .unwrap()
}

fn mutate_json(f: impl FnOnce(&mut Value)) -> Vec<u8> {
    let original = baseline();
    let json_length = u32::from_le_bytes(original[12..16].try_into().unwrap()) as usize;
    let json = &original[20..20 + json_length];
    let mut document: Value = serde_json::from_slice(json).unwrap();
    f(&mut document);
    let mut encoded = serde_json::to_vec(&document).unwrap();
    while !encoded.len().is_multiple_of(4) {
        encoded.push(b' ');
    }
    let payload = &original[20 + json_length..];
    let length = 20 + encoded.len() + payload.len();
    let mut out = Vec::with_capacity(length);
    out.extend_from_slice(b"glTF");
    out.extend_from_slice(&2u32.to_le_bytes());
    out.extend_from_slice(&(length as u32).to_le_bytes());
    out.extend_from_slice(&(encoded.len() as u32).to_le_bytes());
    out.extend_from_slice(&0x4E4F534Au32.to_le_bytes());
    out.extend_from_slice(&encoded);
    out.extend_from_slice(payload);
    out
}

fn assert_rejected_without_panic(bytes: &[u8], kind: &str) {
    let outcome = std::panic::catch_unwind(|| parse_glb(bytes));
    assert!(outcome.is_ok(), "Parser panicked on {kind}");
    assert!(
        outcome.unwrap().is_err(),
        "Parser accepted invalid input: {kind}"
    );
}

#[test]
fn malformed_node_transform_rejected() {
    let bytes = mutate_json(|doc| doc["nodes"][0]["translation"] = json!([0.1]));
    assert_rejected_without_panic(&bytes, "short translation");
}

#[test]
fn node_out_of_bounds_mesh_rejected() {
    let bytes = mutate_json(|doc| doc["nodes"][0]["mesh"] = json!(999999));
    assert_rejected_without_panic(&bytes, "missing mesh");
}

#[test]
fn cyclic_node_graph_rejected() {
    let bytes = mutate_json(|doc| {
        doc["nodes"][0]["children"] = json!([1]);
        doc["nodes"][1]["children"] = json!([0]);
    });
    assert_rejected_without_panic(&bytes, "node cycle");
}

#[test]
fn huge_accessor_count_rejected() {
    let bytes = mutate_json(|doc| doc["accessors"][0]["count"] = json!(u64::MAX));
    assert_rejected_without_panic(&bytes, "unbounded accessor");
}

#[test]
fn buffer_view_escapes_its_bounds_rejected() {
    let bytes = mutate_json(|doc| doc["bufferViews"][0]["byteLength"] = json!(1));
    assert_rejected_without_panic(&bytes, "bufferView containment");
}

#[test]
fn unsupported_required_extension_rejected() {
    let bytes = mutate_json(|doc| {
        doc["extensionsRequired"] = json!(["EXT_meshopt_compression"]);
        doc["extensionsUsed"] = json!(["EXT_meshopt_compression"]);
    });
    assert_rejected_without_panic(&bytes, "required extension without decoder");
}

#[test]
fn primitive_bad_material_reference_rejected() {
    let bytes = mutate_json(|doc| doc["meshes"][0]["primitives"][0]["material"] = json!(9_999_999));
    assert_rejected_without_panic(&bytes, "invalid material");
}

#[test]
fn invalid_buffer_view_stride_rejected() {
    let bytes = mutate_json(|doc| doc["bufferViews"][0]["byteStride"] = json!(u64::MAX));
    assert_rejected_without_panic(&bytes, "invalid stride");
}

#[test]
fn trailing_inconsistent_header_rejected() {
    let mut bytes = baseline();
    bytes.extend_from_slice(&[0, 0, 0, 0]);
    assert_rejected_without_panic(&bytes, "extra bytes without header update");
}
