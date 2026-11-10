# Auditoría independiente — Implementación 01 (M00–M02)

**Fecha:** 2026-11-09. **Origen:** inspección del código local y re-ejecución de pruebas en la PC con Desktop Commander. **Objetivo:** verificar afirmaciones de Antigravity, corregir defectos mínimos y definir si es seguro comenzar el M03 local.

## Resultado ejecutivo

**M00: PASS (local).** Workspace y toolchain en disco; fixture SHA-256 e invariantes anteriores correctos; upstream Git sin cambios.

**M01: PASS para prototipo web de escritorio, sin equivaler a compatibilidad móvil garantizada.** Ambos paquetes WASM están presentes. Prueba real del navegador Chrome headless en Windows confirmó `webgl2` y `webgpu` activos tras inicialización y primer frame; se inspeccionaron visualmente capturas de ambas rutas. No se validó WebGPU en navegador interactivo físico ni en Android/iOS.

**M02: PASS del vertical slice funcional, con limitaciones de cobertura.** Se cargó pelvis en ambas rutas, con 26 estructuras/27 primitives/38,605 triángulos. La auditoría de navegador comprobó selección por lista, aislamiento (1/26), restauración (26/26), acciones de focus y envío de eventos de orbit/zoom. La lógica de raycasting tiene pruebas unitarias reales. No se verificó exhaustivamente la selección táctil de los 26 IDs ni el gesto pinch real en teléfono.

## Hallazgos reales

1. **Desfase del informe:** Antigravity afirmó 7 tests, pero la suite actual contiene 17 antes de nuestras correcciones (9 adversariales GLB, 2 integración GLB, 5 picking y 1 shader). Se añadió un test: ahora **18/18**.
2. **Defecto de formato:** `cargo fmt --all -- --check` fallaba por un test de picking. Se aplicó `cargo fmt --all` y volvió a pasar.
3. **Defecto en AABB/raycast:** el slab test dividía por dirección cero y podía obtener NaN en caras/bordes. Se corrigió `crates/atlas-core/src/scene.rs` con tratamiento explícito de rayos paralelos y se añadió prueba `test_parallel_aabb_rays_on_faces_and_edges`.
4. **Defecto de ciclo de vida de UI:** `resetCanvas()` creaba listeners `window.mousemove/mouseup` adicionales cada vez que cambiaba de backend. Se agregó un `AbortController` por canvas en `apps/probe-web/app.js` y se abortan los listeners anteriores al reemplazar canvas.
5. **Ruido menor:** el navegador solicita `/favicon.ico` y recibe HTTP 404; no afecta el motor.
6. **Métricas FPS:** el contador del shell mide frames dibujados bajo render-on-demand y no es benchmark de 30/60 FPS. Las capturas tampoco acreditan FPS estables.
7. **Riesgos para M03:** parser M02 es un subconjunto deliberado de glTF (triángulos, posición, normal, índices, BIN embebido). No introducir extensiones meshopt/KTX2 en el paquete de uso por M02 sin decodificador y tests. El mapeo TA2 es léxico y la licencia por asset no está verificada.

## Evidencia re-ejecutada

- `python tools/verify_pelvis_baseline.py`: PASS.
- `python tools/verify_pbr_core_fixture.py`: PASS.
- `python tools/validate_stage6_contracts.py`: PASS_DESIGN_ONLY.
- `python tools/validate_stage7_blueprint.py`: PASS_DESIGN_ONLY.
- `cargo test --workspace`: **18 passed, 0 failed** tras parche.
- `cargo clippy --workspace --all-targets -- -D warnings`: PASS.
- `cargo fmt --all -- --check`: PASS tras ajuste.
- `node --check apps/probe-web/app.js`: PASS tras ajuste.
- `tools/audit_browser_interactions.py`: se re-ejecutó y confirmó rutas `webgl2` y `webgpu` y la pelvis en Chrome headless; captura/JSON en `reports/audit/`.
- Se conservaron capturas de WebGL2 y WebGPU en `reports/audit/pelvis-webgl2-ready.png` y `pelvis-webgpu-ready.png`. Ambas muestran geometría anatómica en canvas.
- No se modificaron contenidos bajo `sources/z-anatomy-upstream/`.
- `cargo check --target wasm32-unknown-unknown --workspace`: **PASS**, compilación comprobada después de los ajustes.

## Gate para siguiente fase

**GO para M03 en entorno de desarrollo local**, manteniendo M03 dentro del pipeline OFFLINE de assets. Condiciones para M03: preservar ID por estructura, no fusionar partes anatómicas, no introducir GLB comprimidos que el visor no pueda decodificar, construir LOD solo sobre sacro/vejiga si superan comparación visual y conservar baseline sin comprimir. La revisión de licencias no permite publicación comercial ni distribución del fixture.

**NO-GO para producción**: falta revisión legal por pieza, auditoría clínica, compatibilidad en móviles físicos, pruebas de streaming/memoria (M04) e interfaz final (M05).

No debe confundirse PASS local de M00–M02 con validación completa de toda la aplicación.
