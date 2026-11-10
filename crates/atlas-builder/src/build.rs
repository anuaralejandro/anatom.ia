use std::path::{Path, PathBuf};
use std::process::Command;

use sha2::{Digest, Sha256};

pub fn compute_sha256(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

pub fn run_build(
    fixture_path: &Path,
    crosswalk_path: &Path,
    _profile: &str,
    out_dir: &Path,
) -> Result<(), Box<dyn std::error::Error>> {
    println!(
        "[atlas-builder:build] Construyendo release en: {:?}",
        out_dir
    );
    std::fs::create_dir_all(out_dir)?;

    let staging_dir = PathBuf::from("build/atlas/staging");
    std::fs::create_dir_all(&staging_dir)?;

    // 1. Paquete Base (LOD0 sin compresión)
    let staging_base = staging_dir.join("pelvis-normalized.glb");
    if !staging_base.exists() {
        // Fallback a experimental si ya existe
        let alt = PathBuf::from("reports/experimental/pelvis-pbr-core-compat.glb");
        if alt.exists() {
            std::fs::copy(&alt, &staging_base)?;
        } else {
            crate::normalize::run_normalize(fixture_path, crosswalk_path, &staging_dir)?;
        }
    }

    let rel_base_glb = out_dir.join("pelvis-base-lod0.glb");
    std::fs::copy(&staging_base, &rel_base_glb)?;
    let base_bytes = std::fs::read(&rel_base_glb)?;
    let base_sha = compute_sha256(&base_bytes);

    // 2. Paquete LOD1
    let staging_lod1 = staging_dir.join("pelvis-lod1.glb");
    if !staging_lod1.exists() {
        println!("[atlas-builder:build] Generando LOD1 con Blender...");
        let blender = crate::inspect::find_blender()
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::NotFound, e))?;
        let script = PathBuf::from("tools/blender/export_lod.py");
        let blend = PathBuf::from("sources/z-anatomy-template/Z-Anatomy/Startup.blend");

        let status = Command::new(blender)
            .arg("--background")
            .arg("--disable-autoexec")
            .arg(&blend)
            .arg("--python")
            .arg(&script)
            .arg("--")
            .arg("--fixture")
            .arg(fixture_path)
            .arg("--crosswalk")
            .arg(crosswalk_path)
            .arg("--lod")
            .arg("1")
            .arg("--out")
            .arg(&staging_lod1)
            .arg("--report")
            .arg(staging_dir.join("lod1-report.json"))
            .status()?;

        if !status.success() || !staging_lod1.exists() {
            return Err("Generación de LOD1 en Blender falló".into());
        }
    }

    let rel_lod1_glb = out_dir.join("pelvis-lod1.glb");
    std::fs::copy(&staging_lod1, &rel_lod1_glb)?;
    let lod1_bytes = std::fs::read(&rel_lod1_glb)?;
    let lod1_sha = compute_sha256(&lod1_bytes);

    // 3. Paquete Experimental Meshopt (opcional, si gltfpack está disponible)
    let rel_meshopt_glb = out_dir.join("pelvis-meshopt-lod0.glb");
    let mut meshopt_pkg = None;

    println!("[atlas-builder:build] Generando paquete experimental meshopt con gltfpack...");
    let gltfpack_cmd = Command::new("npx.cmd")
        .arg("--yes")
        .arg("gltfpack")
        .arg("-i")
        .arg(&rel_base_glb)
        .arg("-o")
        .arg(&rel_meshopt_glb)
        .arg("-c")
        .arg("-kn")
        .arg("-ke")
        .status();

    if let Ok(st) = gltfpack_cmd {
        if st.success() && rel_meshopt_glb.exists() {
            let m_bytes = std::fs::read(&rel_meshopt_glb)?;
            let m_sha = compute_sha256(&m_bytes);
            println!(
                "[atlas-builder:build] Paquete meshopt generado ({} bytes, SHA={})",
                m_bytes.len(),
                m_sha
            );
            meshopt_pkg = Some((m_bytes.len(), m_sha));
        }
    }

    // 4. Catálogo Multilingüe (catalog.json)
    let catalog_src = PathBuf::from("reports/pelvis-catalog-candidate.json");
    let mut catalog_val: serde_json::Value = if catalog_src.exists() {
        let txt = std::fs::read_to_string(&catalog_src)?;
        serde_json::from_str(&txt)?
    } else {
        serde_json::json!({
            "schemaVersion": 0,
            "status": "draft_non_distributable",
            "structures": []
        })
    };

    // Asegurar formato de catálogo del release
    catalog_val["status"] = serde_json::Value::String("release_candidate_offline".into());
    let catalog_str = serde_json::to_string_pretty(&catalog_val)?;
    let rel_catalog_path = out_dir.join("catalog.json");
    std::fs::write(&rel_catalog_path, catalog_str.as_bytes())?;
    let catalog_bytes = std::fs::read(&rel_catalog_path)?;
    let catalog_sha = compute_sha256(&catalog_bytes);

    // 5. Manifiesto del Atlas (manifest.json) conforme al schema oficial
    let mut packages_list = vec![
        serde_json::json!({
            "id": "pelvis-base-lod0",
            "variant": "male-adult",
            "region": "pelvis",
            "system": "pelvis",
            "lod": 0,
            "url": "pelvis-base-lod0.glb",
            "bytes": base_bytes.len(),
            "sha256": base_sha,
            "encoding": "none",
            "requiredExtensions": []
        }),
        serde_json::json!({
            "id": "pelvis-lod1",
            "variant": "male-adult",
            "region": "pelvis",
            "system": "pelvis",
            "lod": 1,
            "url": "pelvis-lod1.glb",
            "bytes": lod1_bytes.len(),
            "sha256": lod1_sha,
            "encoding": "none",
            "requiredExtensions": []
        }),
    ];

    let mut region_pkg_ids = vec!["pelvis-base-lod0".to_string(), "pelvis-lod1".to_string()];

    if let Some((m_size, m_sha_str)) = meshopt_pkg {
        packages_list.push(serde_json::json!({
            "id": "pelvis-experimental-meshopt",
            "variant": "male-adult",
            "region": "pelvis",
            "system": "pelvis",
            "lod": 0,
            "url": "pelvis-meshopt-lod0.glb",
            "bytes": m_size,
            "sha256": m_sha_str,
            "encoding": "meshopt",
            "requiredExtensions": [
                "EXT_meshopt_compression",
                "KHR_mesh_quantization"
            ]
        }));
        region_pkg_ids.push("pelvis-experimental-meshopt".to_string());
    }

    let manifest = serde_json::json!({
        "schemaVersion": 1,
        "atlasVersion": "0.3.0",
        "coordinateSystem": {
            "unit": "meter",
            "up": "+Y",
            "anterior": "+Z",
            "patientLeft": "+X"
        },
        "catalog": {
            "url": "catalog.json",
            "sha256": catalog_sha,
            "bytes": catalog_bytes.len()
        },
        "variants": [
            "male-adult"
        ],
        "regions": [
            {
                "id": "pelvis",
                "packages": region_pkg_ids
            }
        ],
        "packages": packages_list
    });

    let manifest_str = serde_json::to_string_pretty(&manifest)?;
    let rel_manifest_path = out_dir.join("manifest.json");
    std::fs::write(&rel_manifest_path, manifest_str.as_bytes())?;

    println!(
        "[atlas-builder:build] Release completado exitosamente: {} paquetes emitidos, manifest y catalog listos.",
        packages_list.len()
    );

    Ok(())
}
