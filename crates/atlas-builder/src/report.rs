use std::path::Path;

use serde_json::json;

pub fn run_report(release_dir: &Path, out_dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    println!(
        "[atlas-builder:report] Generando reportes en: {:?}",
        out_dir
    );
    std::fs::create_dir_all(out_dir)?;

    // 1. Ejecutar validación para obtener validation-report.json
    let val_summary = crate::validate::run_validate(release_dir)?;
    let val_report_path = out_dir.join("validation-report.json");
    let val_json = serde_json::to_string_pretty(&val_summary)?;
    std::fs::write(&val_report_path, val_json.as_bytes())?;

    // 2. build-report.json
    let manifest_path = release_dir.join("manifest.json");
    let manifest: serde_json::Value = if manifest_path.exists() {
        let txt = std::fs::read_to_string(&manifest_path)?;
        serde_json::from_str(&txt).unwrap_or(json!({}))
    } else {
        json!({})
    };

    let build_report = json!({
        "status": if val_summary.passed { "PASS" } else { "FAIL" },
        "milestone": "M03",
        "atlas_version": manifest.get("atlasVersion").unwrap_or(&json!("0.3.0")),
        "packages_count": manifest.get("packages").and_then(|v| v.as_array()).map(|a| a.len()).unwrap_or(0),
        "source": {
            "repository": "https://github.com/Z-Anatomy/Models-of-human-anatomy",
            "commit": "56016ea6da9de755ee4229f61fafc2b313db66ff",
            "source_blend": "sources/z-anatomy-template/Z-Anatomy/Startup.blend"
        },
        "target_structures": 26,
        "mesh_objects_count": 18,
        "curve_objects_count": 8,
        "bilateral_pairs_count": 9,
        "unpaired_structures_count": 8,
        "packages": manifest.get("packages"),
        "build_timestamp": null,
        "report_reproducible": true
    });

    let build_report_path = out_dir.join("build-report.json");
    std::fs::write(
        &build_report_path,
        serde_json::to_string_pretty(&build_report)?.as_bytes(),
    )?;

    // 3. license-report.json (Obligatorio con commercial_release_allowed = false)
    let license_report = json!({
        "status": "NON_COMMERCIAL_LOCAL_TESTING_ONLY",
        "commercial_release_allowed": false,
        "review_status": "pending_per_asset_clinical_and_license_audit",
        "upstream": {
            "name": "Z-Anatomy",
            "repository": "https://github.com/Z-Anatomy/Models-of-human-anatomy",
            "license": "Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)",
            "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
            "upstream_commit": "56016ea6da9de755ee4229f61fafc2b313db66ff"
        },
        "legal_gate_verdict": "BLOCKED_FOR_COMMERCIAL_DISTRIBUTION",
        "notes": [
            "El uso de estos assets derivados es estrictamente local y para desarrollo del prototipo de investigación.",
            "La fuente Z-Anatomy compila obras de múltiples autores y licencias de terceros, algunas con restricciones NoCommercial.",
            "Ningún activo del atlas se distribuye comercialmente sin una auditoría legal y clínica individual por asset."
        ],
        "attribution_required": "Z-Anatomy (CC BY-SA 4.0) — Models of Human Anatomy"
    });

    let license_report_path = out_dir.join("license-report.json");
    std::fs::write(
        &license_report_path,
        serde_json::to_string_pretty(&license_report)?.as_bytes(),
    )?;

    // 4. Quality evidence is only accepted when produced by the independent
    // rasterized triangle-mask evaluator against exactly THESE release binaries.
    // Never synthesize quality PASS from missing/stale reports or box-corner proxies.
    let qa_path = release_dir.join("silhouette-audit.json");
    let unverified = || {
        json!({
            "status": "NOT_RUN",
            "quality_verdict": "UNVERIFIED",
            "reason": "Run tools/audit_lod_silhouettes.py on this exact release; report requires matching SHA-256 hashes",
            "method": "rasterized_triangle_masks",
        })
    };
    let quality_val = if qa_path.is_file() {
        let qa: serde_json::Value = serde_json::from_slice(&std::fs::read(&qa_path)?)?;
        let expected0 =
            crate::build::compute_sha256(&std::fs::read(release_dir.join("pelvis-base-lod0.glb"))?);
        let expected1 =
            crate::build::compute_sha256(&std::fs::read(release_dir.join("pelvis-lod1.glb"))?);
        if qa.get("status").and_then(|v| v.as_str()) == Some("PASS_MEASURED")
            && qa.get("sha256_lod0").and_then(|v| v.as_str()) == Some(expected0.as_str())
            && qa.get("sha256_lod1").and_then(|v| v.as_str()) == Some(expected1.as_str())
            && qa
                .get("is_real_rasterized_triangle_mask")
                .and_then(|v| v.as_bool())
                == Some(true)
        {
            qa
        } else {
            unverified()
        }
    } else {
        unverified()
    };

    let quality_report_path = out_dir.join("quality-report.json");
    std::fs::write(
        &quality_report_path,
        serde_json::to_string_pretty(&quality_val)?.as_bytes(),
    )?;

    println!(
        "[atlas-builder:report] 4 reportes generados exitosamente en {:?}",
        out_dir
    );
    Ok(())
}
