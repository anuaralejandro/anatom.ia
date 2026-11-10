# anatom.ia — Auditoría independiente M04-H (2026-11-09)

**Veredicto:** GO_M05_DESIGN_ONLY; M04-H no obtiene PASS integral de ingeniería. NO-GO a M05 implementación definitiva hasta cerrar P0/P1 de bridge/transport.

## Lo que se repitió y sí funciona
- `cargo fmt --all -- --check`: PASS (exit 0).
- `cargo test --workspace --quiet`: PASS, 38 tests (exit 0).
- `cargo clippy --workspace --all-targets -- -D warnings`: PASS (exit 0).
- `cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder`: PASS (exit 0).
- `python tools/test_m04h_hardening.py`: ejecución exit 0; los gates del script dieron PASS o SIMULATED_PASS.
- `python tools/test_m04_streaming.py`: ejecución exit 0; nueve casos reportados PASS.
- El SW sí permitió recarga offline tras visita online en Chrome headless Windows para WebGPU y WebGL2; no acredita comportamiento universal en Safari/iOS.
- `sources/z-anatomy-upstream`: limpio en la comprobación.
- La rama `feature/m04-runtime-streaming` tiene cambios locales pendientes de commit procedentes de la auditoría y Antigravity. No se realizó commit, push, merge ni cambios de motor durante esta auditoría.

## Defectos y pruebas débiles comprobados

**F01 (P0): coalescing y cancelación incorrecta.**
En `apps/probe-web/asset-stream-manager.js`, `inFlightRequests` reutiliza una única Promise que depende del AbortSignal del primer solicitante. Prueba adversarial reproducida en Chrome (herramienta `tools/audit_m04h_scheduler.py`) lanza dos cargas coalescidas con signals distintos y aborta solamente la primera. Resultado: **AMBAS rechazadas**, aunque la segunda continúa interesada. Evidencia `reports/audit/m04h-independent-scheduler.json`. Se requiere independencia de subscribers con referencia de cancelación y abort del fetch subyacente solo cuando no quedan consumidores.

**F02 (P1): HTTP 404 se reintenta indebidamente.**
`fetchWithRetry` lanza error ante 404, pero el `catch` general lo considera error de red transitorio y vuelve a intentar. En prueba independiente, **4 llamadas** con maxRetries=2, cuando el requisito era rechazo inmediato (1 llamada). Evitar doble contabilización y aplicar clasificación error retryable vs terminal. Evidencia en el mismo JSON.

**F03 (P1): gate de memoria navegador falsamente aprobado.**
En `tools/test_m04h_hardening.py`, sección Gate E, el caso `budget_test` llama `engine.setQualityProfile("invalid_profile_name")` y usa ese rechazo como evidencia de `preflight_swap_budget`. La evidencia JSON registra `errorCode = "Invalid quality profile..."` y `lowGpuBudget = null`. NO acredita un bloqueo de asignación por memoria en navegador. **Sí existe un test unitario Rust** (`test_preflight_swap_budget_enforcement`) que comprueba exceso GPU/CPU, y pasa. Pendiente prueba WASM→GPU que simule o fuerce peak over budget y verifique escena previa intacta.

**F04 (P1): benchmark frame-time atribuido incorrectamente.**
Gate K ejecuta 120 `engine.orbit(); engine.renderFrame()` **síncronos en el mismo callback de JavaScript** y mide el coste de esas llamadas con `performance.now()`; no mide presentación real a ritmo de rAF, latencia GPU, input-to-photon ni FPS sostenidos. Los 0.08–0.30 ms son tiempo de llamada CPU JS→WASM y submit, no "frame time" visual completo. El PASS no certifica rendimiento a 60 FPS. Usar rAF + PerformanceObserver/DevTools/indicadores del hardware para muestrear pacing real y registrar limitaciones.

**F05 (P1): cobertura de errores GPU limitada a failpoints.**
`Renderer::prepare_scene` crea buffers con `create_buffer_init`, devuelve Result por validación lógica/failpoints, pero el código revisado no encierra el camino de asignación en `push_error_scope`/`pop_error_scope` para comprobar errores reales de validación/OOM GPU. Los failpoints prueban reversión del estado bajo fallos inyectados, NO cobertura integral de errores reales de driver/API. `commit_scene` destruye la antigua escena retirándose si recibe una segunda confirmación antes de finalizar la primera; esto necesita un invariante de único commit pendiente o cola explícita.

**F06 (P1): recuperación DeviceLost no enteramente autónoma en idle.**
El flag es consultado por `renderFrame()`; con render-on-demand no se demostró respuesta inmediata a una pérdida del dispositivo mientras la escena permanece inactiva. Incluir notificación/callback hacia host o scheduler de recuperación sin render loop perpetuo, y pruebas de pérdida en reposo.

**F07 (P1): pruebas de lifecycle superficiales.**
El harness crea diez instancias nuevas y las destruye, pero no reata eventos/estado de la app a cada nueva instancia, ni mide listeners/observers por ciclo. No equivale a demostrar ausencia de fugas de UI.

## Qué NO se concluye de esta auditoría
- No se midió VRAM física ni performance móvil.
- No se revisaron licencias por asset ni exactitud clínica.
- No se afirma que el runtime entero falle; la pelvis puede utilizarse localmente y M05 puede DISEÑARSE.

## Gate de siguiente etapa
**Autorizado:** planificación de producto, UX, sistema de diseño, contratos de vistas, navegación, layouts, responsive y testing visual de M05.

**Condicionado:** inicio de implementación M05 sobre el bridge definitivo. Corregir primero F01-F03, y establecer evidencia/limitaciones explícitas F04-F07, o documentar decisión de aceptación de riesgo antes de congelar la API. Mantener código Rust y assets intactos hasta fase correctiva aprobada.

### Referencias locales
- `docs/M04_HARDENING_RESULT.md` y `reports/implementation/M04H/m04h-results.json` (reporte original; no reemplaza esta auditoría).
- `reports/audit/m04h-independent-scheduler.json` (prueba adversarial reproducible).
- `tools/audit_m04h_scheduler.py` (harness de auditoría).
