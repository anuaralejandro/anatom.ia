# GUÍA DE COMPILACIÓN Y EJECUCIÓN (BUILD.MD)
## ANATOM.IA — HITOS M00 A M02

Esta guía contiene las instrucciones exactas, reproducibles y verificadas en **Windows 11 (PowerShell)** para preparar el entorno, compilar los bundles WebAssembly (WebGPU y WebGL2), ejecutar la suite de pruebas y arrancar el visor de diagnóstico (`apps/probe-web`).

---

## 1. REQUISITOS PREVIOS DEL SISTEMA

Se requiere tener instalado en el sistema:
- **Rust Toolchain:** `1.97.1` (o superior compatible).
- **Target WebAssembly:** `wasm32-unknown-unknown`.
- **wasm-pack:** `v0.15.1` o superior.
- **Node.js:** `v22.x` y **npm:** `10.x`.
- **Python:** `3.10` a `3.13`.
- **Navegador web moderno:** Google Chrome o Microsoft Edge con soporte de WebGPU / WebGL2.

### Configuración inicial del entorno (ejecutar una sola vez en PowerShell):

```powershell
# 1. Configurar canal de Rust y target WASM
rustup default 1.97.1
rustup target add wasm32-unknown-unknown

# 2. Instalar componentes de formato y linter
rustup component add rustfmt clippy

# 3. Instalar wasm-pack si no se encuentra instalado
cargo install wasm-pack
```

---

## 2. ESTRUCTURA DEL PROYECTO

```
anatom.ia/
├── Cargo.toml                  # Workspace Rust (crates/atlas-core, crates/atlas-web)
├── rust-toolchain.toml         # Fijación de canal 1.97.1 y target wasm32
├── package.json                # Atajos npm para compilación y servidor
├── crates/
│   ├── atlas-core/             # Motor gráfico agnóstico (glTF, picking, cámara, renderer)
│   └── atlas-web/              # Adaptador WASM / wasm-bindgen (bridge WebGPU/WebGL2)
├── shaders/
│   └── anatomy_opaque.wgsl     # Shader WGSL estándar compatible con WebGPU y WebGL2
├── apps/
│   └── probe-web/              # Shell web de diagnóstico y verificación visual
│       ├── index.html          # Interfaz de diagnóstico con canvas casi full-screen
│       ├── app.js              # Controlador ES Module y manejo de eventos
│       ├── structures.json     # Catálogo con nombres en español de las 26 estructuras
│       ├── pelvis-pbr-core-compat.glb # Fixture anatómico real verificado
│       ├── pkg-webgpu/         # Binarios WASM optimizados para WebGPU
│       └── pkg-webgl2/         # Binarios WASM optimizados para WebGL2
├── reports/                    # Reportes de auditoría y capturas de evidencia
└── tools/                      # Scripts de validación y servidor local
```

---

## 3. COMPILACIÓN DE PRUEBAS Y LINTERS

Ejecutar las validaciones unitarias e integraciones de Rust:

```powershell
# Formato de código
cargo fmt --all -- --check

# Linter Clippy sin advertencias permitidas
cargo clippy --workspace --all-targets -- -D warnings

# Verificación de compilación para wasm32
cargo check --target wasm32-unknown-unknown --workspace

# Pruebas unitarias e integración de parsers, cámara, picking y shaders
cargo test --workspace
```

---

## 4. COMPILACIÓN DUAL DE LOS BUNDLES WEBASSEMBLY

El proyecto genera dos paquetes WASM diferenciados que comparten el mismo núcleo `atlas-core`:

### A. Bundle WebGPU (Ruta nativa moderna)
```powershell
wasm-pack build crates/atlas-web --target web --out-dir ../../apps/probe-web/pkg-webgpu --no-default-features --features webgpu
```

### B. Bundle WebGL2 (Ruta de compatibilidad downlevel)
```powershell
wasm-pack build crates/atlas-web --target web --out-dir ../../apps/probe-web/pkg-webgl2 --no-default-features --features webgl
```

### C. Compilación simultánea vía npm:
```powershell
npm run build
```

---

## 5. EJECUCIÓN DEL SERVIDOR LOCAL DE DIAGNÓSTICO

Para servir los archivos WebAssembly con los tipos MIME correctos (`application/wasm`) y cabeceras de aislamiento:

```powershell
# Iniciar servidor local en el puerto 8080:
python tools/serve_probe.py

# O utilizando npm:
npm run serve
```

---

## 6. APERTURA EN EL NAVEGADOR

Abre Google Chrome o Microsoft Edge y navega a una de las siguientes URLs:

- **Modo Detección Automática (WebGPU con fallback a WebGL2):**
  [http://localhost:8080/index.html?backend=auto](http://localhost:8080/index.html?backend=auto)

- **Forzar WebGPU nativo:**
  [http://localhost:8080/index.html?backend=webgpu](http://localhost:8080/index.html?backend=webgpu)

- **Forzar WebGL2 (ruta downlevel):**
  [http://localhost:8080/index.html?backend=webgl2](http://localhost:8080/index.html?backend=webgl2)

- **Probar Cubo Sintético M01:**
  [http://localhost:8080/index.html?backend=auto&scene=cube](http://localhost:8080/index.html?backend=auto&scene=cube)

- **Probar Pelvis Anatómica Real M02 (26 estructuras TA2):**
  [http://localhost:8080/index.html?backend=auto&scene=pelvis](http://localhost:8080/index.html?backend=auto&scene=pelvis)

---

## 7. PRUEBA HEADLESS AUTOMATIZADA

Para verificar la ejecución sin abrir manualmente el navegador:

```powershell
python tools/test_browser_headless.py
```
Este script levantará un servidor temporal, ejecutará Chrome/Edge en modo headless, renderizará la pelvis y el cubo sintético, y almacenará capturas y estados en `reports/implementation/M01/` y `reports/implementation/M02/`.
