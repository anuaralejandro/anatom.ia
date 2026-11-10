# GUÍA DE COMPILACIÓN Y EJECUCIÓN DEL RUNTIME (BUILD_RUNTIME.MD)
## ANATOM.IA — HITO M04: ASSET STREAMING, CACHE, MEMORIA Y RECUPERACIÓN GPU

Esta guía detalla los pasos reproducibles en **Windows 11 (PowerShell)** para compilar, verificar y ejecutar el runtime de streaming de activos anatómicos de anatom.ia desarrollado en el hito M04.

---

## 1. REQUISITOS DEL SISTEMA

- **Rust Toolchain:** `1.97.1` o compatible (edición 2024).
- **Target WebAssembly:** `wasm32-unknown-unknown`.
- **wasm-pack:** `v0.13` o superior.
- **Node.js:** `v20.x` o `v22.x` con `npm`.
- **Python:** `3.10` a `3.13` (con `playwright` instalado para auditorías E2E).
- **Navegador:** Google Chrome o Microsoft Edge con WebGPU y WebGL2 habilitados.

---

## 2. COMPILACIÓN DE BUNDLES WEBASSEMBLY (DUAL BACKEND)

El motor compila dos paquetes WebAssembly independientes que comparten el núcleo de Rust `atlas-core`:

```powershell
# 1. Compilación del bundle WebGPU
npm run build:webgpu
# O directamente vía wasm-pack:
# wasm-pack build crates/atlas-web --target web --out-dir ../../apps/probe-web/pkg-webgpu --no-default-features --features webgpu

# 2. Compilación del bundle WebGL2
npm run build:webgl2
# O directamente vía wasm-pack:
# wasm-pack build crates/atlas-web --target web --out-dir ../../apps/probe-web/pkg-webgl2 --no-default-features --features webgl

# 3. Compilación dual simultánea
npm run build
```

---

## 3. SUITE DE PRUEBAS AUTOMATIZADAS

### A. Pruebas Unitarias y Linters de Rust
```powershell
# Formato de código
cargo fmt --all -- --check

# Linter Clippy sin advertencias permitidas
cargo clippy --workspace --all-targets -- -D warnings

# Verificación de compilación WebAssembly
cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder

# Suite completa de pruebas unitarias y de integración (36 tests después de la auditoría de seguridad del plan anatómico)
cargo test --workspace
```

### B. Pruebas de Línea Base y Contratos M00–M03
```powershell
python tools/verify_pelvis_baseline.py
python tools/verify_pbr_core_fixture.py
python tools/validate_stage6_contracts.py
python tools/validate_stage7_blueprint.py
python tools/audit_lod_silhouettes.py build/atlas/release/pelvis-base-lod0.glb build/atlas/release/pelvis-lod1.glb build/atlas/release/silhouette-audit.json
python tools/audit_m03_browser_dual.py
```

### C. Suite de Streaming, Caché y Conmutación M04
```powershell
python tools/test_m04_streaming.py
```
Esta prueba automatizada arranca un servidor HTTP local y ejecuta en Chrome headless:
1. Primera descarga en frío (`Cold fetch`) y verificación de renderizado en GPU.
2. Recarga en caliente con cero peticiones de red (`Warm Cache Hit` vía `CacheStorage`).
3. Resiliencia en modo sin conexión (`Offline mode`) y rechazo tipado de activos no cacheados (`NETWORK_ERROR`).
4. Detección de corrupción de digest SHA-256 en disco, purga automática y recuperación desde red.
5. Conmutación atómica rápida 20x entre LOD0 y LOD1, verificando retención de los 26 identificadores TA2, selección, aislamiento y ausencia de fuga acumulativa de buffers GPU.
6. Cancelación de peticiones superseded con tokens generacionales (`A -> B -> A`).
7. Simulación de pérdida de dispositivo GPU (`DeviceLoss`) y reconstrucción automática del contexto (`SIMULATED_PASS`).
8. Verificación de inactividad de bucle de render (`Render-on-Demand`).
9. Streaming dual bajo backend WebGL2 y WebGPU.

---

## 4. EJECUCIÓN MANUAL DEL SHELL DE DIAGNÓSTICO (`probe-web`)

Para interactuar con el visor desde el navegador de escritorio:

```powershell
# Iniciar servidor local
python tools/serve_probe.py
```

Abrir en el navegador:
- **URL Base:** `http://localhost:8080/index.html`
- **Auto (WebGPU preferido, fallback a WebGL2):** `http://localhost:8080/index.html?backend=auto`
- **WebGPU Forzado:** `http://localhost:8080/index.html?backend=webgpu`
- **WebGL2 Forzado:** `http://localhost:8080/index.html?backend=webgl2`
- **LOD 0 Directo (38,605 triángulos):** `http://localhost:8080/index.html?backend=auto&lod=0`
- **LOD 1 Directo (33,758 triángulos):** `http://localhost:8080/index.html?backend=auto&lod=1`

### Controles de Diagnóstico M04 en la Interfaz:
- **Selector de Perfil:** `Low` (64MB GPU), `Medium` (128MB GPU), `High` (256MB GPU).
- **Selector de LOD:** Cambia instantáneamente entre LOD0 y LOD1 de forma atómica en GPU.
- **Botón `🌐 Online / 🔌 Offline`:** Alterna la simulación de corte de conexión para comprobar la persistencia de caché.
- **Botón `⚡ 20x LOD`:** Ejecuta la ráfaga de 20 conmutaciones de nivel de detalle registrando el consumo de memoria.
- **Botón `💥 GPU Loss`:** Provoca la destrucción simulada del dispositivo y lanza la recuperación automática.
