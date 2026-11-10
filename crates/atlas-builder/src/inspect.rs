use std::path::{Path, PathBuf};
use std::process::Command;

pub fn find_blender() -> Result<PathBuf, String> {
    if let Ok(p) = std::env::var("BLENDER_PATH") {
        let path = PathBuf::from(p);
        if path.exists() {
            return Ok(path);
        }
    }

    let default_path =
        PathBuf::from(r"C:\Program Files\Blender Foundation\Blender 4.4\blender.exe");
    if default_path.exists() {
        return Ok(default_path);
    }

    // Check PATH
    if let Ok(output) = Command::new("where.exe").arg("blender.exe").output() {
        if output.status.success() {
            let s = String::from_utf8_lossy(&output.stdout);
            if let Some(line) = s.lines().next() {
                let p = PathBuf::from(line.trim());
                if p.exists() {
                    return Ok(p);
                }
            }
        }
    }

    Err("No se encontró el ejecutable de Blender. Configura BLENDER_PATH o instala Blender 4.4 en la ruta estándar.".to_string())
}

pub fn run_inspect(
    source: &Path,
    out_path: &Path,
    fixture_path: Option<&Path>,
) -> Result<(), Box<dyn std::error::Error>> {
    println!("[atlas-builder:inspect] Analizando fuente: {:?}", source);

    if !source.exists() {
        return Err(format!("El archivo de origen no existe: {:?}", source).into());
    }

    let ext = source
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();

    if ext == "blend" {
        let blender =
            find_blender().map_err(|e| std::io::Error::new(std::io::ErrorKind::NotFound, e))?;
        println!("[atlas-builder:inspect] Usando Blender: {:?}", blender);

        let inspect_script = PathBuf::from("tools/blender/inspect_blend.py");
        if !inspect_script.exists() {
            return Err(format!("Script no encontrado: {:?}", inspect_script).into());
        }

        let mut cmd = Command::new(blender);
        cmd.arg("--background")
            .arg("--disable-autoexec")
            .arg(source)
            .arg("--python")
            .arg(&inspect_script)
            .arg("--")
            .arg("--out")
            .arg(out_path);

        if let Some(f) = fixture_path {
            cmd.arg("--fixture").arg(f);
        }

        println!("[atlas-builder:inspect] Ejecutando inspección headless en Blender...");
        let status = cmd.status()?;
        if !status.success() {
            return Err(format!(
                "Blender inspect falló con código de salida: {:?}",
                status.code()
            )
            .into());
        }

        if !out_path.exists() {
            return Err("El informe de inspección no fue generado por Blender.".into());
        }

        let data = std::fs::read_to_string(out_path)?;
        let val: serde_json::Value = serde_json::from_str(&data)?;
        let total = val
            .get("total_objects")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let fixture_count = val
            .get("fixture_inspected_count")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);
        let missing = val
            .get("fixture_missing_count")
            .and_then(|v| v.as_u64())
            .unwrap_or(0);

        println!(
            "[atlas-builder:inspect] Inspección exitosa: {} objetos totales, {} estructuras evaluadas, {} ausentes.",
            total, fixture_count, missing
        );
    } else {
        return Err(format!(
            "Formato de archivo no soportado para inspección directa: {:?}",
            ext
        )
        .into());
    }

    Ok(())
}
