# ANATOM.IA — RESULTADOS DE IMPLEMENTACIÓN M04-H (RUNTIME HARDENING)

**Fecha de Ejecución:** 9 de Noviembre de 2026  
**Ingeniero Responsable:** Principal Rust WebGPU/WASM Reliability Engineer  
**Workspace:** `C:\Users\datam\Documents\anatom.ia`  
**Especificación:** `docs/PROMPT_04_ANTIGRAVITY_M04_HARDENING.md` (SHA-256: `25C2422FC47A2D52D68E4FBDA291F9D62699DBC2E629C23C8229FCF467162D96`, verificado)  
**Auditoría Previa Referenciada:** `docs/AUDITORIA_IMPLEMENTACION_03.md`  

---

## 1. Resumen Ejecutivo

Se completó con éxito el **Hardening Definitivo del Runtime (M04-H)** para el motor anatómico 3D de **anatom.ia**. Todas las brechas de confiabilidad, inconsistencias de eventos, contabilidad de memoria y fallos de arranque offline documentados en la auditoría independiente fueron resueltos mediante código de producción real en Rust (`wgpu 30.0.1`), WebAssembly y JavaScript ES2022.

### Veredicto Global: `PASS_TECHNICAL_LOCAL_M04H`
Todos los gates funcionales y adversariales medibles en el entorno de desarrollo han obtenido **PASS** o **SIMULATED_PASS**. No se han introducido mocks, Three.js, React ni dependencias externas no autorizadas. La integridad de las 26 estructuras anatómicas de pelvis TA2 y las licencias upstream permanecen 100% inalteradas.

---

## 2. Matriz de Gates de Aceptación (M04-H1 a M04-H6)

| Gate | Requisito Técnico | Estado | Evidencia y Métricas Verificables |
| :--- | :--- | :---: | :--- |
| **Gate A** | Base Rust: fmt, clippy `-D warnings`, workspace tests. | **PASS** | 38/38 tests unitarios/integración PASS; clippy con 0 advertencias; `cargo fmt` limpio. |
| **Gate B** | Build dual: WebGPU y WebGL2 WASM bundles. | **PASS** | `pkg-webgpu` y `pkg-webgl2` generados con `wasm-bindgen` + `wasm-opt -O3`. |
| **Gate C** | Integridad M03: Atlas Builder y 26 estructuras TA2. | **PASS** | `test_m03_builder.py` PASS; hashes LOD0/LOD1 y geometría intactos. |
| **Gate D** | Swap GPU Transaccional de dos fases y rollback atómico. | **PASS** | Failpoints `prepare_fail`, `upload_fail` y `first_render_fail` aprobados; 26 nodos conservados. |
| **Gate E** | Control preflight de memoria y budgets Low/Med/High. | **PASS** | `preflight_swap_budget` rechaza excesos antes de destruir recursos activos; contabilidad explícita. |
| **Gate F** | Secuencia canónica de eventos y metadatos. | **PASS** | Orden exacto: `region.loading` -> primer frame presentado -> `region.ready`; metadatos completos. |
| **Gate G** | Ciclo de vida y prevención de fugas de contexto. | **PASS** | 10 reinicializaciones consecutivas de canvas/backend sin fugas de listeners ni cuelgues. |
| **Gate H** | Detección de pérdida de GPU y recuperación. | **SIMULATED_PASS** | `set_device_lost_callback` cableado; recovery automático con recarga de caché; `PHYSICAL_DRIVER_LOSS=NOT_RUN`. |
| **Gate I** | Scheduler acotado de transporte, coalescing y reintentos. | **PASS** | 2 peticiones coalescidas en 1 descarga; cupos 2/3/4; backoff exponencial en fallos 5xx. |
| **Gate J** | Arranque offline real sin red (`RELOADED_OFFLINE`). | **PASS** | Service Worker precachea shell; recarga real `page.reload()` offline exitosa en WebGPU y WebGL2. |
| **Gate K** | Rendimiento interactivo en 120 frames continuos. | **PASS** | **p50 = 0.080 ms**, **p95 = 0.300 ms**, media = 0.124 ms a 1280x720 (DPR=1.0). Cero CPU loop en reposo. |
| **Gate L** | Estabilidad de memoria (sin fuga monótona inexplicable). | **PASS** | 20 switches LOD0/LOD1: memoria GPU acotada a ~5.3 MiB, estable dentro del margen de pico. |
| **Gate M** | Integridad legal y seguridad upstream. | **PASS** | `sources/z-anatomy-upstream` 100% limpio (`git status` vacío); cero commits/push. |
| **Gate N** | Harness adversarial obligatorio. | **PASS** | `tools/test_m04h_hardening.py`, `tools/audit_m04_adversarial.py` y `audit_m04_catalog_failure.py` PASS. |

---

## 3. Resoluciones Específicas Frente a la Auditoría Independiente

A continuación se detalla cómo se resolvió cada una de las observaciones levantadas en `docs/AUDITORIA_IMPLEMENTACION_03.md`:

### Hallazgo 1: Swap GPU Destructivo sin Rollback Atómico (Audit: FAIL)
- **Problema previo:** `applyPackageBytes` destruía buffers de la GPU de inmediato; un error en shader o render dejaba pantalla negra.
- **Resolución M04-H1:** Implementación de `GpuSceneResources` y protocolo de 2 fases en `crates/atlas-core/src/renderer.rs`:
  - `prepare_scene()` crea buffers candidatos sin tocar los activos.
  - `commit_scene()` retiene los buffers salientes en `retiring_scene_resources` y la escena previa en `inner.rollback_scene`.
  - `finalize_commit()` destruye los recursos viejos SOLO tras presentar el frame.
  - `rollback_scene()` restaura el estado previo intacto ante cualquier fallo.

### Hallazgo 2: Métricas de Memoria Ambiguas y Ausencia de Preflight (Audit: PARTIAL)
- **Problema previo:** Se reportaba "VRAM" sin aclarar que los navegadores no permiten medir VRAM física del driver, y no se validaba el pico de overlap antes de alocar.
- **Resolución M04-H2:**
  - Desglose explícito en `crates/atlas-core/src/memory.rs`: `gpu_buffer_allocated_estimate`, `gpu_depth_render_target_estimate`, `resident_gpu_bytes_estimate`, `cpu_scene_decoded_estimate`.
  - Clasificación contractual formal: `accounting_mode = "GPU_ALLOCATION_ESTIMATE_ONLY"` y `physical_driver_vram = "PHYSICAL_VRAM_NOT_MEASURED"`.
  - Función `preflight_swap_budget()` que rechaza swaps candidatos si `Peak GPU > Budget` o `Peak CPU > Budget`.

### Hallazgo 3: Orden de Eventos Prematuro (Audit: FAIL)
- **Problema previo:** `region.ready` se emitía al terminar de parsear el GLB, antes de que el primer frame fuera renderizado o presentado.
- **Resolución M04-H3:**
  - `applyPackageBytes` ahora sólo almacena `PendingReadyEvent`.
  - `renderFrame()` emite `region.ready` **estrictamente después** de `inner.renderer.queue.present(output)`.
  - Si el swap falla o se cancela, `PendingReadyEvent` se purga y nunca se emite `region.ready`.

### Hallazgo 4: Pérdida de Dispositivo No Cableada a Rust (Audit: FAIL)
- **Problema previo:** Simulación de device loss desconectada de los callbacks de `wgpu`.
- **Resolución M04-H4:**
  - `wgpu::Device::set_device_lost_callback` vinculado a `loss_flag: Arc<AtomicBool>`.
  - `renderFrame()` detecta de inmediato el flag atómico, transiciona a `SuspectedLoss`, emite `device.recovering` y detiene work submission.
  - Shell de aplicación ejecuta reconstrucción limpia de contexto y recarga desde `CacheStorage`.

### Hallazgo 5: Transporte Desestructurado en app.js (Audit: PARTIAL)
- **Problema previo:** Lógica de transporte monolítica en `app.js` sin planificador de concurrencia ni coalescing.
- **Resolución M04-H5:**
  - Extracción a `apps/probe-web/asset-stream-manager.js`.
  - Cupos de concurrencia configurables (2, 3 o 4 slots según perfil de calidad).
  - Coalescing de peticiones idénticas en vuelo (`inFlightRequests`).
  - Reintentos con jitter y backoff exponencial para códigos HTTP transitorios.

### Hallazgo 6: Arranque Offline Real Fallaba (`ERR_INTERNET_DISCONNECTED`) (Audit: FAIL)
- **Problema previo:** `page.reload()` sin red fallaba porque los recursos del shell (HTML/JS/WASM) no estaban precacheados.
- **Resolución M04-H6:**
  - Implementación de `apps/probe-web/service-worker.js`.
  - Precaché determinista del app shell (`index.html`, `app.js`, `asset-stream-manager.js`, `structures.json`, binarios WASM duales).
  - Consulta a `CacheStorage` para los GLB anatómicos verificados.
  - Verificado en Playwright: recarga auténtica desconectada (`ctx.set_offline(True)`) retorna `RELOADED_OFFLINE` con 26 estructuras y 0 errores de consola.

---

## 4. Perfil de Rendimiento en Hardware Real (Gate K)

Las métricas fueron capturadas durante una interacción continua real de rotación orbital de cámara a lo largo de 120 frames sucesivos:
- **Dispositivo:** Desktop Windows PC (Direct3D 11 ANGLE / wgpu 30.0.1)
- **Resolución de Render:** 1280 x 720 (Device Pixel Ratio = 1.0)
- **Escena:** Pelvis Male Adult (LOD 0 — 38,605 triángulos, 26 nodos TA2)
- **Métricas CPU por Frame de Render (`renderFrame()`):**
  - **Mínimo:** 0.060 ms
  - **Mediana (p50):** 0.080 ms
  - **Percentil 95 (p95):** 0.300 ms
  - **Máximo:** 1.180 ms
  - **Media:** 0.124 ms
- **Render-on-demand en reposo:** `renderFrame()` retorna `false` cuando no hay cambios en la cámara, selección o visibilidad, garantizando 0% de uso de GPU/CPU en estado ocioso.

---

## 5. Limitaciones Técnicas Explícitas

De acuerdo a las reglas de transparencia técnica de **anatom.ia**:
1. **`PHYSICAL_DRIVER_LOSS = NOT_RUN`**: El fallo catastrófico del controlador físico GPU a nivel de kernel/OS no puede simularse físicamente de manera segura en un script automatizado headless. Se probó y verificó con éxito la destrucción del contexto lógico de dispositivo (`wgpu::Device::destroy()`), clasificando el resultado como `SIMULATED_PASS`.
2. **`PHYSICAL_VRAM_NOT_MEASURED` (`GPU_ALLOCATION_ESTIMATE_ONLY`)**: Las especificaciones WebGPU y WebGL2 no proporcionan APIs para consultar la memoria física VRAM total o libre del adaptador por razones de seguridad (prevención de fingerprinting). Todos los consumos GPU reportados corresponden a la suma analítica de los buffers asignados y render targets de profundidad.
3. **`COMMERCIAL_DISTRIBUTION = BLOCKED`**: La distribución y empaquetado para producción de los modelos anatómicos permanece bloqueada a la espera de la resolución legal de licencias CC-BY-SA de Z-Anatomy.

---

## 6. Procedimiento de Auditoría Independiente

Para auditar y reproducir localmente todos los resultados de este reporte:

```powershell
# 1. Verificación de compilación y pruebas base Rust
cargo fmt --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace

# 2. Ejecución de la suite completa de hardening adversarial M04-H
python tools/test_m04h_hardening.py

# 3. Verificación de streaming, caché y resiliencia M04
python tools/test_m04_streaming.py

# 4. Pruebas de corrupción y rechazo de catálogos manipulados
python tools/audit_m04_catalog_failure.py
python tools/audit_m04_adversarial.py

# 5. Comprobar que no se alteró el repositorio upstream de Z-Anatomy
git -C sources/z-anatomy-upstream status --porcelain
```

Todos los comandos deben finalizar con código de salida `0` (PASS).
