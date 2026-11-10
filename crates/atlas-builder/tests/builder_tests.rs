use std::path::PathBuf;

use atlas_builder::validate::run_validate;

#[test]
fn test_validate_release_package_passes() {
    let release_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("build")
        .join("atlas")
        .join("release");

    if !release_dir.join("manifest.json").exists() {
        eprintln!("Release package does not exist yet at {:?}, skipping test", release_dir);
        return;
    }

    let report = run_validate(&release_dir).expect("Validation should succeed for release dir");
    assert!(report.passed, "Validation report should pass: {:?}", report.errors);
    assert!(report.errors.is_empty(), "Validation report should have 0 errors");
    assert!(report.checks_count >= 20, "Should have performed at least 20 checks");
}

#[test]
fn test_adversarial_path_traversal_rejected() {
    let temp_dir = std::env::temp_dir().join(format!("anatomia_test_traversal_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).unwrap();

    let malicious_manifest = serde_json::json!({
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": {
            "unit": "meter",
            "up": "+Y",
            "anterior": "+Z",
            "patientLeft": "+X"
        },
        "variants": ["male-adult"],
        "regions": [{ "id": "pelvis", "packages": ["bad-pkg"] }],
        "catalog": { "url": "catalog.json", "sha256": "0000000000000000000000000000000000000000000000000000000000000000", "bytes": 10 },
        "packages": [{
            "id": "bad-pkg",
            "variant": "male-adult",
            "region": "pelvis",
            "system": "pelvis",
            "lod": 0,
            "url": "../../../Windows/System32/cmd.exe",
            "bytes": 100,
            "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
            "encoding": "none",
            "requiredExtensions": []
        }]
    });

    std::fs::write(temp_dir.join("manifest.json"), serde_json::to_string_pretty(&malicious_manifest).unwrap()).unwrap();

    let result = run_validate(&temp_dir);
    let _ = std::fs::remove_dir_all(&temp_dir);

    match result {
        Ok(summary) => {
            assert!(!summary.passed, "Path traversal manifest must not pass validation");
            assert!(
                summary.errors.iter().any(|e| e.contains("ruta sospechosa") || e.contains("no existe")),
                "Expected rejection error for traversal path in errors: {:?}",
                summary.errors
            );
        }
        Err(e) => {
            let msg = e.to_string();
            assert!(msg.contains("ruta sospechosa") || msg.contains("no existe"));
        }
    }
}

#[test]
fn test_adversarial_bad_hash_rejected() {
    let release_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .parent()
        .unwrap()
        .parent()
        .unwrap()
        .join("build")
        .join("atlas")
        .join("release");

    if !release_dir.join("manifest.json").exists() {
        return;
    }

    let temp_dir = std::env::temp_dir().join(format!("anatomia_test_bad_hash_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).unwrap();

    // Copy release files into temp_dir
    for entry in std::fs::read_dir(&release_dir).unwrap() {
        let entry = entry.unwrap();
        if entry.path().is_file() {
            std::fs::copy(entry.path(), temp_dir.join(entry.file_name())).unwrap();
        }
    }

    // Tamper with manifest hash
    let manifest_path = temp_dir.join("manifest.json");
    let mut manifest: serde_json::Value = serde_json::from_str(&std::fs::read_to_string(&manifest_path).unwrap()).unwrap();
    manifest["packages"][0]["sha256"] = serde_json::json!("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff");
    std::fs::write(&manifest_path, serde_json::to_string_pretty(&manifest).unwrap()).unwrap();

    let result = run_validate(&temp_dir);
    let _ = std::fs::remove_dir_all(&temp_dir);

    match result {
        Ok(summary) => {
            assert!(!summary.passed, "Tampered SHA-256 must not pass validation");
            assert!(
                summary.errors.iter().any(|e| e.contains("SHA256") || e.contains("no coincide")),
                "Expected hash mismatch in errors: {:?}",
                summary.errors
            );
        }
        Err(e) => {
            let msg = e.to_string();
            assert!(msg.contains("SHA-256 mismatch") || msg.contains("Validación falló"));
        }
    }
}

#[test]
fn test_adversarial_duplicate_package_id_rejected() {
    let temp_dir = std::env::temp_dir().join(format!("anatomia_test_dup_pkg_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).unwrap();

    let dup_manifest = serde_json::json!({
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": {
            "unit": "meter",
            "up": "+Y",
            "anterior": "+Z",
            "patientLeft": "+X"
        },
        "variants": ["male-adult"],
        "regions": [{ "id": "pelvis", "packages": ["pkg-1"] }],
        "catalog": { "url": "catalog.json", "sha256": "0000000000000000000000000000000000000000000000000000000000000000", "bytes": 10 },
        "packages": [
            {
                "id": "pkg-1",
                "variant": "male-adult",
                "region": "pelvis",
                "system": "pelvis",
                "lod": 0,
                "url": "pkg1.glb",
                "bytes": 100,
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "encoding": "none",
                "requiredExtensions": []
            },
            {
                "id": "pkg-1",
                "variant": "male-adult",
                "region": "pelvis",
                "system": "pelvis",
                "lod": 1,
                "url": "pkg2.glb",
                "bytes": 100,
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "encoding": "none",
                "requiredExtensions": []
            }
        ]
    });

    std::fs::write(temp_dir.join("manifest.json"), serde_json::to_string_pretty(&dup_manifest).unwrap()).unwrap();

    let result = run_validate(&temp_dir);
    let _ = std::fs::remove_dir_all(&temp_dir);

    match result {
        Ok(summary) => {
            assert!(!summary.passed, "Duplicate package ID must not pass validation");
            assert!(
                summary.errors.iter().any(|e| e.contains("duplicado")),
                "Expected duplicate error in errors: {:?}",
                summary.errors
            );
        }
        Err(e) => {
            let msg = e.to_string();
            assert!(msg.contains("duplicado"));
        }
    }
}

#[test]
fn test_adversarial_unlisted_package_in_region_rejected() {
    let temp_dir = std::env::temp_dir().join(format!("anatomia_test_unlisted_{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&temp_dir);
    std::fs::create_dir_all(&temp_dir).unwrap();

    let unlisted_manifest = serde_json::json!({
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": {
            "unit": "meter",
            "up": "+Y",
            "anterior": "+Z",
            "patientLeft": "+X"
        },
        "variants": ["male-adult"],
        "regions": [{ "id": "pelvis", "packages": ["nonexistent-pkg"] }],
        "catalog": { "url": "catalog.json", "sha256": "0000000000000000000000000000000000000000000000000000000000000000", "bytes": 10 },
        "packages": [
            {
                "id": "real-pkg",
                "variant": "male-adult",
                "region": "pelvis",
                "system": "pelvis",
                "lod": 0,
                "url": "pkg.glb",
                "bytes": 100,
                "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                "encoding": "none",
                "requiredExtensions": []
            }
        ]
    });

    std::fs::write(temp_dir.join("manifest.json"), serde_json::to_string_pretty(&unlisted_manifest).unwrap()).unwrap();

    let result = run_validate(&temp_dir);
    let _ = std::fs::remove_dir_all(&temp_dir);

    match result {
        Ok(summary) => {
            assert!(!summary.passed, "Unlisted package in region must not pass validation");
            assert!(
                summary.errors.iter().any(|e| e.contains("paquete inexistente") || e.contains("no existe")),
                "Expected unlisted package error in errors: {:?}",
                summary.errors
            );
        }
        Err(e) => {
            let msg = e.to_string();
            assert!(msg.contains("paquete inexistente") || msg.contains("no existe"));
        }
    }
}
