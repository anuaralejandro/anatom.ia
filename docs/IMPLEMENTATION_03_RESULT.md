# ANATOM.IA — REPORTE DE IMPLEMENTACIÓN 03 (HITO M04)
## ASSET STREAMING, CACHE PERSISTENTE, GESTIÓN DE MEMORIA Y RECUPERACIÓN GPU

**Fecha de Ejecución:** 2026-11-09 / 2026-11-10  
**Rol:** Principal Rust WebGPU/WASM Reliability Engineer & Senior Browser Storage/Performance Engineer  
**Workspace:** `C:\Users\datam\Documents\anatom.ia`  
**Rama Git:** `feature/m04-runtime-streaming`  
**Estado General de M04:** **COMPLETADO / APROBADO (PASS)**  

---

## 1. RESUMEN EJECUTIVO

En este hito se transformó el visor anatómico base (M00–M02) y el builder de assets optimizados (M03) en un **runtime de streaming de activos robusto, escalable y tolerante a fallos**. 

Se resolvieron con rigor técnico todos los objetivos obligatorios de M04:
1. **Resolución segura de manifiestos y paquetes (M04-A):** Capa canónica agnóstica al DOM (`crates/atlas-core/src/manifest.rs`) que valida el esquema v1, aplica reglas estrictas contra URLs maliciosas/traversal, rechaza extensiones incompatibles (`EXT_meshopt_compression`) mediante error tipado (`ErrorCode::AssetUnsupportedExtension`) sin caídas del motor, y verifica digest criptográfico SHA-256 y tamaño en bytes antes de transferir a GPU.
2. **Asincronía, cancelación y tokens generacionales (M04-B):** Se eliminó el `static SCENE_GENERATION` global a favor de tokens generacionales por instancia (`instance_generation` y `MemoryTracker`). Cada intención de carga incrementa la generación e invalida peticiones obsoletas en vuelo mediante `AbortController`. En pruebas de ráfaga (A → B → A), las respuestas tardías son descartadas inmediatamente sin mutar la escena ni corromper recursos de GPU.
3. **Caché persistente, integridad y modo sin conexión (M04-C):** Siguiendo la decisión de arquitectura documentada en [`docs/ADR_004_CACHE_STORAGE.md`](./ADR_004_CACHE_STORAGE.md), se adoptó la API estándar `CacheStorage` con claves virtuales inmutables (`https://atlas.local/assets/v0.3.0/${packageId}?sha=${expectedSha256}`). Las recargas en caliente (`warm cache hit`) operan con **0 peticiones de red**. Se comprobó la resiliencia en modo offline (sirviendo activos cacheados y emitiendo `NETWORK_ERROR` tipado y recuperable ante misses no cacheados) y la detección automática de corrupción con purga inmediata de entradas alteradas.
4. **Gestión de memoria y conmutación atómica de LOD (M04-D):** Se implementó `transfer_state_from` en `Scene`, permitiendo conmutar entre LOD0 (38,605 triángulos glTF) y LOD1 (33,758 triángulos glTF) de forma atómica en GPU. La conmutación retiene de forma idéntica la orientación, target y zoom de la cámara, la estructura seleccionada (`selected_id`) y el estado de visibilidad o aislamiento de los 26 identificadores TA2. Se añadió destrucción explícita de buffers (`Buffer::destroy`) en `Renderer`, comprobando tras **20 conmutaciones consecutivas** la ausencia total de fugas crecientes de memoria GPU (pico: 3.27 MB, final: 3.21 MB).
5. **Recuperación de GPU y eventos de ciclo de vida (M04-E):** Detección y recuperación ante `SurfaceLost` y `Outdated` en `renderFrame()`, y simulación de pérdida de dispositivo (`simulateDeviceLoss()`) con reconstrucción de pipelines y recarga verificada desde caché local (clasificado como `SIMULATED_PASS`).
6. **Conservación estricta de contratos e invariantes:** Se mantuvieron intactos los fixtures de pelvis, Core PBR, catálogos TA2 y licencias. La distribución comercial pública continúa clasificada como `BLOCKED_FOR_COMMERCIAL_DISTRIBUTION`.

---

## 2. COMPONENTES Y MÓDULOS IMPLEMENTADOS

### 2.1. Núcleo Rust (`crates/atlas-core`)
- **`src/manifest.rs`:**
  - Estructuras: `ManifestSnapshot`, `PackageDef`, `RegionDef`, `CoordinateSystem`, `CatalogRef`, `RegionLoadPlan`.
  - Funciones de seguridad: `is_safe_relative_url` (prohíbe prefijos `/`, `\`, traversal `..`, esquemas `:` y caracteres no permitidos).
  - Verificación criptográfica: `verify_sha256` utilizando `sha2 = "0.10"`, `verify_size`.
  - Negociador de paquetes: `select_package` descarta paquetes que requieran `EXT_meshopt_compression` con `ErrorCode::AssetUnsupportedExtension` y prioriza el LOD solicitado o el de mayor fidelidad compatible (`encoding: none`).
- **`src/memory.rs`:**
  - Perfiles de calidad: `QualityProfile` (`Low`, `Medium`, `High`) con presupuestos provisionales:
    - Low: 64 MiB GPU / 48 MiB CPU / 2 fetches concurrentes.
    - Medium: 128 MiB GPU / 96 MiB CPU / 3 fetches concurrentes.
    - High: 256 MiB GPU / 160 MiB CPU / 4 fetches concurrentes.
  - `MemoryTracker`: Seguimiento por instancia de `resident_gpu_bytes`, `decoded_cpu_bytes`, generación activa, request ID y revisiones.
  - Cálculo de memoria de geometría: `calculate_scene_cpu_bytes` y `calculate_gpu_resident_bytes`.
- **`src/scene.rs`:**
  - Método `transfer_state_from(&mut self, old_scene: &Scene)`: Transfiere atómicamente la estructura seleccionada y los estados de visibilidad de los nodos coincidentes por `AnatomyId`, incrementando la revisión de escena.
- **`src/renderer.rs`:**
  - Campo `resident_gpu_bytes: usize` en `Renderer`.
  - Método `destroy_gpu_resources(&mut self)`: Invoca `.destroy()` explícito en todos los vertex buffers, index buffers, object buffers y uniform buffers antes de liberar vectores.
  - Implementación de `Drop` para `Renderer` que asegura la destrucción inmediata de recursos de GPU.
- **Pruebas Unitarias Nuevas:**
  - `tests/manifest_test.rs`: 6 tests unitarios y adversariales (manifest real, URLs maliciosas, rechazo de meshopt sin decoder, verificación SHA-256).
  - `tests/memory_test.rs`: 3 tests unitarios (presupuestos de perfil, ciclo de vida de tracker, cálculo de memoria).
  - `tests/atomic_swap_test.rs`: 3 tests unitarios (preservación de selección y visibilidad, preservación de aislamiento, descarte seguro de IDs no coincidentes).

### 2.2. Adaptador Web / Bridge WASM (`crates/atlas-web`)
- **Eliminación de `static SCENE_GENERATION`:** El token generacional y el `MemoryTracker` son ahora miembros de la estructura `EngineInner` y gestionados por instancia de `AtlasEngine`.
- **Nuevos métodos exportados vía `#[wasm_bindgen]`:**
  - `loadManifest(manifest_json: &str) -> Result<JsValue, JsValue>`
  - `createLoadPlan(region_id: &str, variant_id: &str, preferred_lod: Option<u32>) -> Result<JsValue, JsValue>`
  - `nextGeneration(request_id: Option<u32>) -> u32`
  - `currentGeneration() -> u32`
  - `cancelLoad(request_id: Option<u32>) -> u32`
  - `applyPackageBytes(bytes: &[u8], plan_val: JsValue, request_id: u32, generation: u32) -> Result<JsValue, JsValue>`
  - `getMemoryStats() -> JsValue`
  - `setQualityProfile(profile_str: &str) -> Result<JsValue, JsValue>`
  - `simulateDeviceLoss() -> Result<(), JsValue>`
- **Eventos emitidos:** `engine.ready`, `engine.error`, `region.loading`, `region.ready`, `structure.selected`, `scene.changed`, `quality.changed`, `device.recovering`, `device.recovered`.

### 2.3. Capa Web de Transporte y Diagnóstico (`apps/probe-web`)
- **`app.js` — Clase `AssetStreamManager`:**
  - Gestión de caché local persistente con `CacheStorage` (`anatomia-atlas-v0.3.0`).
  - Cálculo de digest SHA-256 en cliente mediante `crypto.subtle.digest('SHA-256', buffer)`.
  - AbortController por solicitud para abortar descargas obsoletas en ráfagas.
  - Soporte de modo sin conexión simulado (`simulatedOffline`).
  - Purgado automático ante discrepancia de hash SHA-256 en caché.
  - Función de prueba automatizada de conmutación rápida 20x (`runRapidLodToggleTest`).
  - Función de prueba de recuperación de pérdida de GPU (`simulateDeviceLossAndRecover`).
- **`index.html`:**
  - Controles diagnósticos: Selector de LOD (`LOD 0`, `LOD 1`), Selector de Perfil de Calidad (`Low`, `Medium`, `High`), Botón `🌐 Online / 🔌 Offline`, Botón `⚡ 20x LOD`, Botón `💥 GPU Loss`.
  - Panel inferior de métricas en tiempo real: Estado de Caché (`HIT (Disk)` / `MISS (Fetch)`), Bytes descargados, Generación activa, Memoria GPU estimada, Memoria CPU decodificada.

---

## 3. EVIDENCIAS DE EJECUCIÓN Y PRUEBAS

### 3.1. Pruebas de Compilación y Linters (PowerShell)
```powershell
# 1. Verificación de formato
cargo fmt --all -- --check
# Resultado: EXIT CODE 0 (Sin discrepancias de estilo)

# 2. Linter Clippy
cargo clippy --workspace --all-targets -- -D warnings
# Resultado: EXIT CODE 0 (0 warnings, 0 errores)

# 3. Compilación WASM
cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder
# Resultado: EXIT CODE 0 (atlas-core y atlas-web compilan limpiamente para wasm32)

# 4. Suite completa de tests unitarios de Rust (35 tests)
cargo test --workspace
# Resultado: 35 PASSED, 0 FAILED (atlas-core: 30 tests, atlas-builder: 5 tests)
```

### 3.2. Compilación Dual de Bundles WebAssembly
```powershell
npm run build
# -> wasm-pack build crates/atlas-web --target web --out-dir ../../apps/probe-web/pkg-webgpu --no-default-features --features webgpu (23.66s)
# -> wasm-pack build crates/atlas-web --target web --out-dir ../../apps/probe-web/pkg-webgl2 --no-default-features --features webgl (1m 20s)
# Resultado: EXIT CODE 0 (Ambos paquetes generados y optimizados con wasm-opt)
```

### 3.3. Suite E2E Automatizada de Streaming M04 (`tools/test_m04_streaming.py`)
Ejecutada en Google Chrome headless (1280x800) contra el servidor HTTP local:

| Caso de Prueba | Backend | Métrica Observada | Veredicto |
|---|---|---|---|
| 1. Descarga en Frío (`Cold Fetch`) | WebGPU | 1 petición de red GLB, 38,605 triángulos, 26 TA2 | **PASS** |
| 2. Reutilización de Caché (`Warm Hit`) | WebGPU | **0 peticiones de red**, digest SHA-256 verificado en disco, 38,605 triángulos | **PASS** |
| 3. Modo Offline (`Offline Mode`) | WebGPU | Carga offline desde caché exitosa; activo no cacheado rechazado con `NETWORK_ERROR` sin crash | **PASS** |
| 4. Integridad y Detección de Corrupción | WebGPU | Digest modificado deliberadamente detectado en disco, purgado y re-descargado limpiamente | **PASS** |
| 5. Conmutación Rápida 20x LOD | WebGPU | 20 swaps consecutivos: 26/26 IDs intactos, selección preservada, aislamiento preservado. Pico GPU: 3.27 MB, Final GPU: 3.21 MB (Sin fuga acumulativa) | **PASS** |
| 6. Cancelación de Peticiones en Ráfaga | WebGPU | Ráfaga A → B → A: Peticiones 1 y 2 canceladas por generación; petición 3 gana (38,605 triángulos) | **PASS** |
| 7. Simulación de Pérdida de GPU | WebGPU | Contexto reconstruido, pipelines reinicializados, escena recuperada desde caché local (26/26 nodos) | **SIMULATED_PASS** |
| 8. Inactividad Render-on-Demand | WebGPU | En estado estático `renderFrame()` retorna `false`; cero consumo innecesario de ciclos de render | **PASS** |
| 9. Streaming en WebGL2 (LOD1) | WebGL2 | Backend WEBGL2 activo, 33,758 triángulos glTF, 26/26 nodos renderizados | **PASS** |

**Veredicto de la Suite M04:** **PASS (9/9 pruebas aprobadas)**  
**Reporte JSON generado:** [`reports/implementation/M04/m04-streaming-suite-result.json`](../reports/implementation/M04/m04-streaming-suite-result.json)  
**Captura auténtica generada:** [`reports/implementation/M04/m04-probe-rendered.png`](../reports/implementation/M04/m04-probe-rendered.png)

### 3.4. Regresión de Pruebas de Línea Base M00–M03
- `python tools/verify_pelvis_baseline.py` → **PASS** (26/26 estructuras TA2 presentes en fixture GLB).
- `python tools/verify_pbr_core_fixture.py` → **PASS** (Geometría idéntica, Core PBR sin extensiones propietarias).
- `python tools/validate_stage6_contracts.py` → **PASS_DESIGN_ONLY**.
- `python tools/validate_stage7_blueprint.py` → **PASS_DESIGN_ONLY (21/21 checks)**.
- `python tools/audit_lod_silhouettes.py` → **PASS_MEASURED (MAX_P95: 0.0 px)**.
- `python tools/audit_m03_browser_dual.py` → **PASS (4/4 casos WebGL2 y WebGPU para LOD0 y LOD1)**.

---

## 4. INVENTARIO DE ENTREGABLES DEL HITO M04

1. `crates/atlas-core/src/manifest.rs` — Resolver de manifiesto, URLs seguras y validación de hash SHA-256.
2. `crates/atlas-core/src/memory.rs` — Perfiles de calidad, tracking de memoria GPU/CPU y tokens generacionales.
3. `crates/atlas-core/src/scene.rs` — Conmutación atómica de escena (`transfer_state_from`).
4. `crates/atlas-core/src/renderer.rs` — Destrucción explícita de buffers GPU y tracking de VRAM residente.
5. `crates/atlas-core/tests/atomic_swap_test.rs` — Pruebas de conmutación atómica y preservación de selección/aislamiento.
6. `crates/atlas-core/tests/manifest_test.rs` — Pruebas unitarias y adversariales de manifiesto y hash.
7. `crates/atlas-core/tests/memory_test.rs` — Pruebas de presupuestos de memoria y lifecycle de trackers.
8. `crates/atlas-web/src/lib.rs` — Bridge WASM ampliado para M04 con tokens de instancia y eventos.
9. `apps/probe-web/app.js` — Controlador web con `AssetStreamManager` (`CacheStorage` + Web Crypto + AbortController).
10. `apps/probe-web/index.html` — Shell de diagnóstico con controles de streaming, LOD, perfiles y métricas en vivo.
11. `apps/probe-web/manifest.json` y `apps/probe-web/catalog.json` — Manifiesto y catálogo servidos localmente.
12. `docs/ADR_004_CACHE_STORAGE.md` — Registro de decisión arquitectónica para la adopción de `CacheStorage`.
13. `docs/BUILD_RUNTIME.md` — Guía de compilación, verificación y ejecución del runtime.
14. `tools/test_m04_streaming.py` — Arnés automatizado de pruebas E2E de streaming y caché en navegador.
15. `reports/implementation/M04/m04-streaming-suite-result.json` — Resultados estructurados de la suite M04.
16. `reports/implementation/M04/m04-probe-rendered.png` — Captura auténtica del visor operando con el streaming de M04.
17. `reports/implementation/implementation-03-status.json` — Estado formal auditado del hito M04.

---

## 5. LÍMITES Y TRABAJO EXCLUIDO

- **No implementado M05:** No se desarrolló interfaz React final, sistema de usuarios, autenticación, CMS ni tutor por IA.
- **No implementado M06:** No se desplegó en AWS S3/CloudFront ni servidores Docker.
- **Sin decodificador meshopt runtime:** `pelvis-meshopt-lod0.glb` permanece excluido del runtime y es detectado y rechazado de forma segura con `ErrorCode::AssetUnsupportedExtension`.
- **Estatus legal:** La distribución comercial de activos Z-Anatomy permanece bloqueada (`commercial_release_allowed: false`). El uso actual es estrictamente para investigación y validación local de ingeniería.
