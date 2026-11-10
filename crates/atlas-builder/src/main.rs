use std::path::{Path, PathBuf};
use std::process::ExitCode;

use atlas_builder::{build, inspect, normalize, report, validate};

fn print_usage() {
    eprintln!(
        r#"anatom.ia — Atlas Builder CLI (M03)

USO:
    atlas-builder <SUBCOMANDO> [OPCIONES]

SUBCOMANDOS:
    inspect <source-blend-or-json> --out <report.json> [--fixture <fixture.json>]
        Inspecciona el proyecto Blender o reporte sin modificar la fuente.

    normalize <fixture.json> [--crosswalk <crosswalk.json>] --out <staging-dir>
        Evalúa y extrae los 26 objetos anatómicos y normaliza a glTF Core PBR.

    build <fixture.json> [--crosswalk <crosswalk.json>] [--profile mobile] --out <release-dir>
        Construye el release del atlas (paquete base, LOD1, manifest.json, catalog.json).

    validate <release-dir>
        Valida integridad de manifest, hashes SHA-256, catálogo y modelos GLB.

    report <release-dir> [--out <reports-dir>]
        Genera los reportes oficiales de build, validación, licencias y calidad.
"#
    );
}

fn main() -> ExitCode {
    let args: Vec<String> = std::env::args().collect();
    if args.len() < 2 {
        print_usage();
        return ExitCode::FAILURE;
    }

    let subcmd = args[1].as_str();
    match subcmd {
        "inspect" => {
            if args.len() < 3 {
                eprintln!("Error: se requiere la ruta al archivo fuente (.blend).");
                print_usage();
                return ExitCode::FAILURE;
            }
            let source = PathBuf::from(&args[2]);
            let mut out = PathBuf::from("reports/experimental/blend-inspection.json");
            let mut fixture = None;

            let mut i = 3;
            while i < args.len() {
                if args[i] == "--out" && i + 1 < args.len() {
                    out = PathBuf::from(&args[i + 1]);
                    i += 2;
                } else if args[i] == "--fixture" && i + 1 < args.len() {
                    fixture = Some(PathBuf::from(&args[i + 1]));
                    i += 2;
                } else {
                    i += 1;
                }
            }

            match inspect::run_inspect(&source, &out, fixture.as_deref()) {
                Ok(_) => ExitCode::SUCCESS,
                Err(e) => {
                    eprintln!("[ERROR] inspect falló: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
        "normalize" => {
            if args.len() < 3 {
                eprintln!("Error: se requiere la ruta al archivo de fixture JSON.");
                print_usage();
                return ExitCode::FAILURE;
            }
            let fixture = PathBuf::from(&args[2]);
            let mut crosswalk = PathBuf::from("reports/pelvis-ta2-crosswalk.json");
            let mut out_dir = PathBuf::from("build/atlas/staging");

            let mut i = 3;
            while i < args.len() {
                if args[i] == "--crosswalk" && i + 1 < args.len() {
                    crosswalk = PathBuf::from(&args[i + 1]);
                    i += 2;
                } else if args[i] == "--out" && i + 1 < args.len() {
                    out_dir = PathBuf::from(&args[i + 1]);
                    i += 2;
                } else {
                    i += 1;
                }
            }

            match normalize::run_normalize(&fixture, &crosswalk, &out_dir) {
                Ok(_) => ExitCode::SUCCESS,
                Err(e) => {
                    eprintln!("[ERROR] normalize falló: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
        "build" => {
            if args.len() < 3 {
                eprintln!("Error: se requiere la ruta al archivo de fixture JSON.");
                print_usage();
                return ExitCode::FAILURE;
            }
            let fixture = PathBuf::from(&args[2]);
            let mut crosswalk = PathBuf::from("reports/pelvis-ta2-crosswalk.json");
            let mut profile = "mobile".to_string();
            let mut out_dir = PathBuf::from("build/atlas/release");

            let mut i = 3;
            while i < args.len() {
                if args[i] == "--crosswalk" && i + 1 < args.len() {
                    crosswalk = PathBuf::from(&args[i + 1]);
                    i += 2;
                } else if args[i] == "--profile" && i + 1 < args.len() {
                    profile = args[i + 1].clone();
                    i += 2;
                } else if args[i] == "--out" && i + 1 < args.len() {
                    out_dir = PathBuf::from(&args[i + 1]);
                    i += 2;
                } else {
                    i += 1;
                }
            }

            match build::run_build(&fixture, &crosswalk, &profile, &out_dir) {
                Ok(_) => ExitCode::SUCCESS,
                Err(e) => {
                    eprintln!("[ERROR] build falló: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
        "validate" => {
            if args.len() < 3 {
                eprintln!("Error: se requiere la ruta al directorio de release.");
                print_usage();
                return ExitCode::FAILURE;
            }
            let release_dir = Path::new(&args[2]);
            match validate::run_validate(release_dir) {
                Ok(summary) => {
                    if summary.passed {
                        ExitCode::SUCCESS
                    } else {
                        ExitCode::FAILURE
                    }
                }
                Err(e) => {
                    eprintln!("[ERROR] validate falló: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
        "report" => {
            if args.len() < 3 {
                eprintln!("Error: se requiere la ruta al directorio de release.");
                print_usage();
                return ExitCode::FAILURE;
            }
            let release_dir = PathBuf::from(&args[2]);
            let mut out_dir = release_dir.clone();

            let mut i = 3;
            while i < args.len() {
                if args[i] == "--out" && i + 1 < args.len() {
                    out_dir = PathBuf::from(&args[i + 1]);
                    i += 2;
                } else {
                    i += 1;
                }
            }

            match report::run_report(&release_dir, &out_dir) {
                Ok(_) => ExitCode::SUCCESS,
                Err(e) => {
                    eprintln!("[ERROR] report falló: {}", e);
                    ExitCode::FAILURE
                }
            }
        }
        "--help" | "-h" | "help" => {
            print_usage();
            ExitCode::SUCCESS
        }
        other => {
            eprintln!("Subcomando desconocido: {}", other);
            print_usage();
            ExitCode::FAILURE
        }
    }
}
