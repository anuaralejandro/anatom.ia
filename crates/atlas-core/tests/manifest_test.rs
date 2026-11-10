use atlas_core::manifest::{ManifestSnapshot, is_safe_relative_url, verify_sha256, verify_size};
use atlas_core::types::ErrorCode;

#[test]
fn test_parse_real_release_manifest() {
    let manifest_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("build")
        .join("atlas")
        .join("release")
        .join("manifest.json");

    if !manifest_path.exists() {
        return;
    }

    let manifest_str = std::fs::read_to_string(&manifest_path).unwrap();
    let snapshot =
        ManifestSnapshot::parse_json(&manifest_str).expect("Valid manifest should parse");

    assert_eq!(snapshot.schema_version, 1);
    assert_eq!(snapshot.coordinate_system.up, "+Y");
    assert_eq!(snapshot.coordinate_system.anterior, "+Z");
    assert_eq!(snapshot.coordinate_system.patient_left, "+X");

    // Test selection LOD 0
    let pkg_lod0 = snapshot
        .select_package("pelvis", "male-adult", Some(0))
        .expect("Should select LOD0");
    assert_eq!(pkg_lod0.id, "pelvis-base-lod0");
    assert_eq!(pkg_lod0.lod, 0);
    assert_eq!(pkg_lod0.encoding, "none");

    // Test selection LOD 1
    let pkg_lod1 = snapshot
        .select_package("pelvis", "male-adult", Some(1))
        .expect("Should select LOD1");
    assert_eq!(pkg_lod1.id, "pelvis-lod1");
    assert_eq!(pkg_lod1.lod, 1);
    assert_eq!(pkg_lod1.encoding, "none");

    // Create load plan
    let plan = snapshot
        .create_load_plan("pelvis", "male-adult", Some(1))
        .expect("Should create plan");
    assert_eq!(plan.package_id, "pelvis-lod1");
    assert_eq!(plan.catalog_url, "catalog.json");
    assert!(plan.expected_package_bytes > 0);
}

#[test]
fn test_safe_relative_url_rules() {
    assert!(is_safe_relative_url("pelvis-base-lod0.glb"));
    assert!(is_safe_relative_url("catalog.json"));
    assert!(is_safe_relative_url("packages/male/pelvis.glb"));
    assert!(is_safe_relative_url("a_b-c.1.glb"));

    // Path traversal
    assert!(!is_safe_relative_url("../secret.bin"));
    assert!(!is_safe_relative_url("dir/../../secret.bin"));

    // Absolute paths
    assert!(!is_safe_relative_url("/etc/passwd"));
    assert!(!is_safe_relative_url("\\Windows\\System32"));
    assert!(!is_safe_relative_url("C:\\test.glb"));

    // Schemes / protocols
    assert!(!is_safe_relative_url("data:model/gltf-binary;base64,AAAA"));
    assert!(!is_safe_relative_url("javascript:alert(1)"));
    assert!(!is_safe_relative_url("http://example.com/asset.glb"));
    assert!(!is_safe_relative_url("https://example.com/asset.glb"));

    // Spaces and strange characters
    assert!(!is_safe_relative_url("file name with space.glb"));
    assert!(!is_safe_relative_url("file?query=1"));
    assert!(!is_safe_relative_url("file#hash"));
}

#[test]
fn test_reject_unsupported_meshopt_when_only_meshopt_available() {
    let manifest_json = r#"{
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": { "unit": "meter", "up": "+Y", "anterior": "+Z", "patientLeft": "+X" },
        "variants": ["male-adult"],
        "regions": [{ "id": "pelvis", "packages": ["pelvis-meshopt"] }],
        "catalog": { "url": "catalog.json", "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", "bytes": 100 },
        "packages": [{
            "id": "pelvis-meshopt",
            "variant": "male-adult",
            "region": "pelvis",
            "system": "pelvis",
            "lod": 0,
            "url": "pelvis-meshopt.glb",
            "bytes": 500,
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "encoding": "meshopt",
            "requiredExtensions": ["EXT_meshopt_compression"]
        }]
    }"#;

    let snapshot = ManifestSnapshot::parse_json(manifest_json).expect("Manifest syntax is valid");
    let err = snapshot
        .select_package("pelvis", "male-adult", None)
        .expect_err("Should reject meshopt package");

    assert_eq!(err.code, ErrorCode::AssetUnsupportedExtension);
    assert!(err.detail.unwrap().contains("EXT_meshopt_compression"));
}

#[test]
fn test_reject_unsupported_region_and_variant() {
    let manifest_json = r#"{
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": { "unit": "meter", "up": "+Y", "anterior": "+Z", "patientLeft": "+X" },
        "variants": ["male-adult"],
        "regions": [{ "id": "pelvis", "packages": ["pelvis-base"] }],
        "catalog": { "url": "catalog.json", "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", "bytes": 100 },
        "packages": [{
            "id": "pelvis-base",
            "variant": "male-adult",
            "region": "pelvis",
            "system": "pelvis",
            "lod": 0,
            "url": "pelvis-base.glb",
            "bytes": 500,
            "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "encoding": "none",
            "requiredExtensions": []
        }]
    }"#;

    let snapshot = ManifestSnapshot::parse_json(manifest_json).unwrap();

    let err_reg = snapshot
        .select_package("thorax", "male-adult", None)
        .expect_err("Should reject unpublished thorax region");
    assert_eq!(err_reg.code, ErrorCode::RegionUnavailable);

    let err_var = snapshot
        .select_package("pelvis", "female-adult", None)
        .expect_err("Should reject unpublished female-adult variant");
    assert_eq!(err_var.code, ErrorCode::RegionUnavailable);
}

#[test]
fn test_adversarial_malicious_urls_rejected() {
    let traversal_json = r#"{
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": { "unit": "meter", "up": "+Y", "anterior": "+Z", "patientLeft": "+X" },
        "variants": ["male-adult"],
        "regions": [{ "id": "pelvis", "packages": ["p1"] }],
        "catalog": { "url": "../secret.json", "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef", "bytes": 100 },
        "packages": [{
            "id": "p1", "variant": "male-adult", "region": "pelvis", "system": "pelvis", "lod": 0,
            "url": "p1.glb", "bytes": 100, "sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "encoding": "none", "requiredExtensions": []
        }]
    }"#;

    let err =
        ManifestSnapshot::parse_json(traversal_json).expect_err("Traversal catalog must fail");
    assert_eq!(err.code, ErrorCode::AssetCorrupt);
}

#[test]
fn test_verify_sha256_and_size() {
    let data = b"anatom.ia asset streaming M04 verification";
    // Real sha256 of data
    let mut hasher = sha2::Sha256::default();
    sha2::Digest::update(&mut hasher, data);
    let real_sha = format!("{:x}", sha2::Digest::finalize(hasher));

    assert!(verify_sha256(&real_sha, data).is_ok());
    assert!(verify_size(data.len() as u64, data.len()).is_ok());

    // Corrupted digest
    let err_hash = verify_sha256(
        "0000000000000000000000000000000000000000000000000000000000000000",
        data,
    )
    .expect_err("Corrupted digest must fail");
    assert_eq!(err_hash.code, ErrorCode::AssetCorrupt);

    // Wrong size
    let err_size = verify_size(99999, data.len()).expect_err("Wrong size must fail");
    assert_eq!(err_size.code, ErrorCode::AssetCorrupt);
}

#[test]
fn test_resolved_load_plan_rejects_forged_variant_and_hash() {
    let manifest_json = serde_json::json!({
        "schemaVersion":1,
        "atlasVersion":"0.3.0",
        "coordinateSystem":{"unit":"meter","up":"+Y","anterior":"+Z","patientLeft":"+X"},
        "variants":["male-adult"],
        "regions":[{"id":"pelvis","packages":["pelvis-base"]}],
        "catalog":{"url":"catalog.json","sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef","bytes":100},
        "packages":[{"id":"pelvis-base","variant":"male-adult","region":"pelvis",
            "system":"pelvis","lod":0,"url":"pelvis-base.glb","bytes":100,
            "sha256":"0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "encoding":"none","requiredExtensions":[]}]
    }).to_string();
    let manifest = ManifestSnapshot::parse_json(&manifest_json).unwrap();
    let canonical = manifest
        .create_load_plan("pelvis", "male-adult", Some(0))
        .unwrap();
    assert!(manifest.validate_load_plan(&canonical).is_ok());

    let mut variant_forgery = canonical.clone();
    variant_forgery.variant_id = "female-adult".into();
    let err = manifest.validate_load_plan(&variant_forgery).unwrap_err();
    assert_eq!(err.code, ErrorCode::RegionUnavailable);

    let mut hash_forgery = canonical.clone();
    hash_forgery.expected_package_sha256 = "0".repeat(64);
    let err = manifest.validate_load_plan(&hash_forgery).unwrap_err();
    assert_eq!(err.code, ErrorCode::AssetCorrupt);

    let mut url_forgery = canonical.clone();
    url_forgery.package_url = "alternate.glb".into();
    let err = manifest.validate_load_plan(&url_forgery).unwrap_err();
    assert_eq!(err.code, ErrorCode::AssetCorrupt);
}
