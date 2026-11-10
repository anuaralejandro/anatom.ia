use std::collections::{HashMap, HashSet};
use std::path::Path;

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ValidationSummary {
    pub passed: bool,
    pub checks_count: usize,
    pub errors: Vec<String>,
    pub warnings: Vec<String>,
    pub files_verified: Vec<String>,
}

fn compute_file_sha256(bytes: &[u8]) -> String {
    let mut hasher = Sha256::new();
    hasher.update(bytes);
    format!("{:x}", hasher.finalize())
}

pub fn is_safe_relative_url(url: &str) -> bool {
    if url.starts_with('/') || url.contains('\\') || url.contains("..") || url.contains("://") {
        return false;
    }
    // Pattern: ^[A-Za-z0-9_./-]+$
    url.chars()
        .all(|c| c.is_ascii_alphanumeric() || c == '_' || c == '.' || c == '/' || c == '-')
}

pub fn run_validate(release_dir: &Path) -> Result<ValidationSummary, Box<dyn std::error::Error>> {
    println!(
        "[atlas-builder:validate] Validando release en: {:?}",
        release_dir
    );

    let mut errors = Vec::new();
    let mut warnings = Vec::new();
    let mut checks = 0;
    let mut files_verified = Vec::new();
    let mut catalog_ids = HashSet::new();
    let canonical_release = release_dir.canonicalize()?;

    // 1. Validar manifest.json
    let manifest_path = release_dir.join("manifest.json");
    checks += 1;
    if !manifest_path.exists() {
        errors.push("manifest.json no encontrado en el directorio de release.".into());
        return Ok(ValidationSummary {
            passed: false,
            checks_count: checks,
            errors,
            warnings,
            files_verified,
        });
    }

    let manifest_bytes = std::fs::read(&manifest_path)?;
    let manifest: serde_json::Value = match serde_json::from_slice(&manifest_bytes) {
        Ok(v) => v,
        Err(e) => {
            errors.push(format!("Error parseando manifest.json: {}", e));
            return Ok(ValidationSummary {
                passed: false,
                checks_count: checks,
                errors,
                warnings,
                files_verified,
            });
        }
    };

    checks += 1;
    if manifest.get("schemaVersion").and_then(|v| v.as_i64()) != Some(1) {
        errors.push("schemaVersion debe ser exactamente 1.".into());
    }

    checks += 1;
    let coord = manifest.get("coordinateSystem");
    if let Some(c) = coord {
        if c.get("unit").and_then(|v| v.as_str()) != Some("meter")
            || c.get("up").and_then(|v| v.as_str()) != Some("+Y")
            || c.get("anterior").and_then(|v| v.as_str()) != Some("+Z")
            || c.get("patientLeft").and_then(|v| v.as_str()) != Some("+X")
        {
            errors
                .push("coordinateSystem no cumple con la especificación de atlas-manifest.".into());
        }
    } else {
        errors.push("coordinateSystem ausente en manifest.".into());
    }

    // 2. Validar catalog.json referenciado
    checks += 1;
    let cat_ref = manifest.get("catalog");
    if let Some(cat) = cat_ref {
        let url = cat.get("url").and_then(|v| v.as_str()).unwrap_or("");
        let exp_sha = cat.get("sha256").and_then(|v| v.as_str()).unwrap_or("");
        let exp_bytes = cat.get("bytes").and_then(|v| v.as_u64()).unwrap_or(0);

        checks += 1;
        if !is_safe_relative_url(url) {
            errors.push(format!("URL de catálogo insegura o inválida: '{}'", url));
        }

        // Reject unsafe paths BEFORE filesystem access; never follow escaping symlinks.
        if !is_safe_relative_url(url) {
            return Ok(ValidationSummary {
                passed: false,
                checks_count: checks,
                errors,
                warnings,
                files_verified,
            });
        }
        let cat_file = release_dir.join(url);
        checks += 1;
        if !cat_file.exists() {
            errors.push(format!(
                "Archivo de catálogo no existe en disco: {:?}",
                cat_file
            ));
        } else {
            if !cat_file.canonicalize()?.starts_with(&canonical_release) {
                errors.push("Catálogo enlaza fuera del release".into());
                return Ok(ValidationSummary {
                    passed: false,
                    checks_count: checks,
                    errors,
                    warnings,
                    files_verified,
                });
            }
            let bytes = std::fs::read(&cat_file)?;
            checks += 1;
            if bytes.len() as u64 != exp_bytes {
                errors.push(format!(
                    "Tamaño de catálogo no coincide (esperado: {}, real: {})",
                    exp_bytes,
                    bytes.len()
                ));
            }
            checks += 1;
            let actual_sha = compute_file_sha256(&bytes);
            if actual_sha != exp_sha {
                errors.push(format!(
                    "SHA256 de catálogo no coincide (esperado: {}, real: {})",
                    exp_sha, actual_sha
                ));
            }
            files_verified.push(url.to_string());

            // Validar contenido del catálogo
            let cat_doc: Result<serde_json::Value, _> = serde_json::from_slice(&bytes);
            if let Ok(cd) = cat_doc {
                if let Some(structs) = cd.get("structures").and_then(|v| v.as_array()) {
                    checks += 1;
                    if structs.len() != 26 {
                        errors.push(format!(
                            "El catálogo debe contener 26 estructuras (tiene {})",
                            structs.len()
                        ));
                    }

                    let mut seen_ids = HashSet::new();
                    let mut bilateral_count = 0;

                    for s in structs {
                        if let Some(id) = s.get("id").and_then(|v| v.as_str()) {
                            catalog_ids.insert(id.to_string());
                            if !seen_ids.insert(id.to_string()) {
                                errors.push(format!(
                                    "ID de estructura duplicado en catálogo: {}",
                                    id
                                ));
                            }
                            if id.ends_with(":left") || id.ends_with(":right") {
                                bilateral_count += 1;
                            }
                        } else {
                            errors.push("Estructura sin 'id' válido en catálogo.".into());
                        }

                        // Verificar etiquetas multilingües
                        let labels = s.get("labels");
                        if let Some(lbl) = labels {
                            if lbl.get("es-MX").is_none()
                                || lbl.get("en").is_none()
                                || lbl.get("la").is_none()
                            {
                                warnings.push(format!(
                                    "Estructura {:?} carece de etiquetas multilingües completas.",
                                    s.get("id")
                                ));
                            }
                        }
                    }

                    checks += 1;
                    if bilateral_count != 18 {
                        errors.push(format!(
                            "Se esperaban 18 estructuras bilaterales en catálogo (encontradas: {})",
                            bilateral_count
                        ));
                    }
                } else {
                    errors.push("Catálogo inválido: falta arreglo structures".into());
                }
            } else {
                errors.push("Catálogo inválido: no es JSON bien formado".into());
            }
        }
    } else {
        errors.push("catalog ausente en manifest.".into());
    }

    // 3. Validar Packages
    let pkgs = manifest.get("packages").and_then(|v| v.as_array());
    let mut pkg_map = HashMap::new();

    if let Some(packages) = pkgs {
        for pkg in packages {
            checks += 1;
            let id = pkg.get("id").and_then(|v| v.as_str()).unwrap_or("");
            let url = pkg.get("url").and_then(|v| v.as_str()).unwrap_or("");
            let exp_bytes = pkg.get("bytes").and_then(|v| v.as_u64()).unwrap_or(0);
            let exp_sha = pkg.get("sha256").and_then(|v| v.as_str()).unwrap_or("");
            let encoding = pkg.get("encoding").and_then(|v| v.as_str()).unwrap_or("");

            if id.is_empty() {
                errors.push("Paquete con ID vacío en manifest.".into());
            } else if pkg_map.insert(id.to_string(), pkg.clone()).is_some() {
                errors.push(format!("ID de paquete duplicado: {}", id));
            }

            if !is_safe_relative_url(url) {
                errors.push(format!("URL de paquete insegura: '{}'", url));
                continue;
            }

            let pkg_file = release_dir.join(url);
            checks += 1;
            if !pkg_file.exists() {
                errors.push(format!("Archivo de paquete no encontrado: {:?}", pkg_file));
                continue;
            }
            if !pkg_file.canonicalize()?.starts_with(&canonical_release) {
                errors.push(format!("Paquete '{}' enlaza fuera del release", id));
                continue;
            }

            let bytes = std::fs::read(&pkg_file)?;
            checks += 1;
            if bytes.len() as u64 != exp_bytes {
                errors.push(format!(
                    "Tamaño de paquete '{}' no coincide (esperado: {}, real: {})",
                    id,
                    exp_bytes,
                    bytes.len()
                ));
            }

            checks += 1;
            let actual_sha = compute_file_sha256(&bytes);
            if actual_sha != exp_sha {
                errors.push(format!(
                    "SHA256 de paquete '{}' no coincide (esperado: {}, real: {})",
                    id, exp_sha, actual_sha
                ));
            }
            files_verified.push(url.to_string());

            // Validación de contenido GLB para paquetes no comprimidos
            if encoding == "none" {
                checks += 1;
                match atlas_core::glb::parse_glb(&bytes) {
                    Ok(scene) => {
                        let aids: HashSet<_> = scene
                            .nodes
                            .iter()
                            .filter_map(|n| n.anatomy_id.clone())
                            .collect();

                        let id_count = scene
                            .nodes
                            .iter()
                            .filter(|n| n.anatomy_id.is_some())
                            .count();
                        if aids.len() != 26 || id_count != 26 {
                            errors.push(format!(
                                "Paquete '{}' contiene {} AnatomyIds únicos, {} nodos etiquetados (deben ser 26/26)",
                                id, aids.len(), id_count
                            ));
                        }
                        if aids != catalog_ids {
                            errors.push(format!(
                                "Paquete '{}' no coincide exactamente con los IDs del catálogo",
                                id
                            ));
                        }

                        // Bounds finitos
                        if !scene.bounds.min.is_finite() || !scene.bounds.max.is_finite() {
                            errors.push(format!(
                                "Paquete '{}' posee AABB con coordenadas no finitas.",
                                id
                            ));
                        }
                    }
                    Err(e) => {
                        errors.push(format!(
                            "Paquete '{}' no pudo ser decodificado por atlas-core: {}",
                            id, e
                        ));
                    }
                }
            } else if encoding == "meshopt" {
                // Verificar que declare requiredExtensions
                let req_exts = pkg.get("requiredExtensions").and_then(|v| v.as_array());
                if req_exts.is_none() || req_exts.unwrap().is_empty() {
                    errors.push(format!(
                        "Paquete meshopt '{}' debe declarar requiredExtensions.",
                        id
                    ));
                }
            }
        }
    } else {
        errors.push("packages ausente o inválido en manifest.".into());
    }

    // 4. Validar Referential Integrity en Regions
    let regions = manifest.get("regions").and_then(|v| v.as_array());
    if let Some(regs) = regions {
        for reg in regs {
            if let Some(pkg_ids) = reg.get("packages").and_then(|v| v.as_array()) {
                for pid_val in pkg_ids {
                    if let Some(pid) = pid_val.as_str() {
                        checks += 1;
                        if !pkg_map.contains_key(pid) {
                            errors.push(format!(
                                "Región {:?} hace referencia a paquete inexistente: '{}'",
                                reg.get("id"),
                                pid
                            ));
                        }
                    }
                }
            }
        }
    }

    let passed = errors.is_empty();
    println!(
        "[atlas-builder:validate] Resultado: {} ({} verificaciones, {} errores, {} advertencias).",
        if passed { "PASS" } else { "FAIL" },
        checks,
        errors.len(),
        warnings.len()
    );

    Ok(ValidationSummary {
        passed,
        checks_count: checks,
        errors,
        warnings,
        files_verified,
    })
}
