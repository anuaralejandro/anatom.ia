use std::fs;
use std::path::PathBuf;

use atlas_core::glb::parse_glb;

fn get_fixture_path() -> PathBuf {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    manifest_dir
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("reports")
        .join("experimental")
        .join("pelvis-pbr-core-compat.glb")
}

#[test]
fn test_parse_real_pelvis_pbr_core_compat() {
    let path = get_fixture_path();
    assert!(path.exists(), "Fixture GLB must exist at {:?}", path);

    let bytes = fs::read(&path).expect("Failed to read fixture GLB");
    assert_eq!(
        bytes.len(),
        681_492,
        "Fixture byte size must match contract exactly"
    );

    let scene = parse_glb(&bytes).expect("Valid GLB must parse cleanly without errors");

    // 1. Structure count: exactly 26 nodes with atlas_id
    let mut anatomy_ids: Vec<String> = scene
        .nodes
        .iter()
        .filter_map(|n| n.anatomy_id.clone())
        .collect();
    anatomy_ids.sort();
    anatomy_ids.dedup();

    assert_eq!(
        anatomy_ids.len(),
        26,
        "Scene must contain exactly 26 distinct AnatomyIds"
    );

    // 2. Meshes count: 26
    assert_eq!(scene.meshes.len(), 26, "Must contain exactly 26 meshes");

    // 3. Primitives count: 27 (one mesh has 2 primitives)
    let total_primitives: usize = scene.meshes.iter().map(|m| m.primitives.len()).sum();
    assert_eq!(total_primitives, 27, "Must contain exactly 27 primitives");

    // 4. Triangles count: 38,605
    let total_triangles: usize = scene
        .meshes
        .iter()
        .flat_map(|m| &m.primitives)
        .map(|p| p.indices.len() / 3)
        .sum();
    assert_eq!(
        total_triangles, 38_605,
        "Must contain exactly 38,605 indexed triangles"
    );

    // 5. Check bilateral structures exist
    assert!(anatomy_ids.contains(&"ta2:4301:left".to_string()));
    assert!(anatomy_ids.contains(&"ta2:4301:right".to_string()));
    assert!(anatomy_ids.contains(&"ta2:6522:left".to_string()));
    assert!(anatomy_ids.contains(&"ta2:6522:right".to_string()));
    assert!(anatomy_ids.contains(&"ta2:1071".to_string())); // Sacrum
    assert!(anatomy_ids.contains(&"ta2:3401".to_string())); // Bladder

    // 6. Scene bounds are valid
    assert!(scene.bounds.is_valid(), "Scene bounding box must be valid");
    let size = scene.bounds.size();
    assert!(size.x > 0.0 && size.y > 0.0 && size.z > 0.0);
}

#[test]
fn test_parse_corrupt_headers() {
    // Empty
    assert!(parse_glb(&[]).is_err());

    // Less than 12 bytes
    assert!(parse_glb(&[0; 8]).is_err());

    // Invalid magic
    let mut bad_magic = vec![0u8; 24];
    bad_magic[0..4].copy_from_slice(b"NOPE");
    bad_magic[4..8].copy_from_slice(&2u32.to_le_bytes());
    bad_magic[8..12].copy_from_slice(&24u32.to_le_bytes());
    assert!(parse_glb(&bad_magic).is_err());

    // Unsupported version (version 1)
    let mut bad_version = vec![0u8; 24];
    bad_version[0..4].copy_from_slice(b"glTF");
    bad_version[4..8].copy_from_slice(&1u32.to_le_bytes());
    bad_version[8..12].copy_from_slice(&24u32.to_le_bytes());
    assert!(parse_glb(&bad_version).is_err());

    // Truncated length in header
    let mut truncated = vec![0u8; 24];
    truncated[0..4].copy_from_slice(b"glTF");
    truncated[4..8].copy_from_slice(&2u32.to_le_bytes());
    truncated[8..12].copy_from_slice(&1000u32.to_le_bytes()); // Claims 1000 bytes
    assert!(parse_glb(&truncated).is_err());
}
