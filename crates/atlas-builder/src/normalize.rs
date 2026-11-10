use std::path::{Path, PathBuf};
use std::process::Command;

use crate::inspect::find_blender;

pub fn run_normalize(
    fixture_path: &Path,
    crosswalk_path: &Path,
    workdir: &Path,
) -> Result<PathBuf, Box<dyn std::error::Error>> {
    println!(
        "[atlas-builder:normalize] Normalizando fixture: {:?}",
        fixture_path
    );

    if !fixture_path.exists() {
        return Err(format!("Fixture no encontrado: {:?}", fixture_path).into());
    }
    if !crosswalk_path.exists() {
        return Err(format!("Crosswalk no encontrado: {:?}", crosswalk_path).into());
    }

    std::fs::create_dir_all(workdir)?;
    let out_glb = workdir.join("pelvis-normalized.glb");
    let out_report = workdir.join("normalization-report.json");

    let blender =
        find_blender().map_err(|e| std::io::Error::new(std::io::ErrorKind::NotFound, e))?;
    let script = PathBuf::from("tools/blender/export_normalized.py");
    if !script.exists() {
        return Err(format!("Script de normalización no encontrado: {:?}", script).into());
    }

    let source_blend = PathBuf::from("sources/z-anatomy-template/Z-Anatomy/Startup.blend");
    if !source_blend.exists() {
        return Err(format!("Startup.blend no encontrado: {:?}", source_blend).into());
    }

    let mut cmd = Command::new(blender);
    cmd.arg("--background")
        .arg("--disable-autoexec")
        .arg(&source_blend)
        .arg("--python")
        .arg(&script)
        .arg("--")
        .arg("--fixture")
        .arg(fixture_path)
        .arg("--crosswalk")
        .arg(crosswalk_path)
        .arg("--out")
        .arg(&out_glb)
        .arg("--report")
        .arg(&out_report);

    println!("[atlas-builder:normalize] Ejecutando exportación normalizada en Blender...");
    let status = cmd.status()?;
    if !status.success() {
        return Err(format!("Blender normalize falló con código: {:?}", status.code()).into());
    }

    if !out_glb.exists() {
        return Err("El archivo GLB normalizado no fue generado.".into());
    }

    // Validación preliminar con parser de atlas-core
    let glb_bytes = std::fs::read(&out_glb)?;
    let scene = atlas_core::glb::parse_glb(&glb_bytes)
        .map_err(|e| format!("Validación del GLB normalizado falló en atlas-core: {}", e))?;

    let aids_count = scene
        .nodes
        .iter()
        .filter(|n| n.anatomy_id.is_some())
        .count();

    println!(
        "[atlas-builder:normalize] OK: GLB normalizado verificado ({} bytes, {} nodos con anatomy_id, {} mallas).",
        glb_bytes.len(),
        aids_count,
        scene.meshes.len()
    );

    Ok(out_glb)
}
