# ANATOM.IA — Procedimiento de Construcción de Assets Anatómicos (M03: Atlas Builder)

Este documento describe el procedimiento determinista y reproducible para ejecutar el pipeline de **Atlas Builder (M03)** en Windows PowerShell, procesando fuentes anatómicas de Z-Anatomy (.blend) y emitiendo paquetes glTF/GLB optimizados, validados y versionados.

---

## 1. Requisitos Previos

| Herramienta | Versión Mínima Verificada | Ruta / Comando Predeterminado |
|---|---|---|
| **Windows OS** | Windows 10/11 x86_64 | `powershell.exe` |
| **Rust Toolchain** | `stable-x86_64-pc-windows-msvc` (1.80+) | `cargo --version` |
| **Blender** | Blender 4.4+ LTS | `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe` |
| **Python** | 3.10+ (o el integrado en Blender) | `python --version` |
| **Node.js / npx** | Node 18+ (para `gltfpack` experimental) | `npx --version` |

> [!NOTE]
> Si Blender está instalado en una ruta personalizada, exporta la variable de entorno `BLENDER_PATH`:
> ```powershell
> $env:BLENDER_PATH = "C:\Ruta\A\Tu\blender.exe"
> ```

---

## 2. Estructura de Salida y Contratos

El pipeline emite artefactos en `build/atlas/release/`:

```
build/atlas/release/
├── manifest.json              # Atlas Manifest v1 con hashes SHA-256 y metadatos
├── catalog.json               # Catálogo multilingüe con las 26 estructuras TA2 y lateralidad
├── pelvis-base-lod0.glb       # Paquete base LOD0 Core PBR compatible (sin compresión obligatoria)
├── pelvis-lod1.glb            # Paquete simplificado LOD1 (Sacrum y Vejiga decimados, 24 reusados)
├── pelvis-meshopt-lod0.glb    # Paquete experimental meshopt (requiere EXT_meshopt_compression)
├── build-report.json          # Reporte técnico de compilación y empaquetado
├── validation-report.json     # Reporte de validación estructural y referencial
├── license-report.json        # Reporte de licencias y bloqueo comercial
└── quality-report.json        # Métricas de error geométrico y desviación de silueta LOD
```

---

## 3. Pasos de Ejecución (Windows PowerShell)

### Paso 1: Compilar la CLI `atlas-builder`

Desde la raíz del repositorio (`C:\Users\datam\Documents\anatom.ia`):

```powershell
cargo build --package atlas-builder
```

El ejecutable quedará en `target\debug\atlas-builder.exe`.

### Paso 2: Inspeccionar la Fuente Blender (Opcional / Diagnóstico)

Inspecciona el proyecto `.blend` sin modificar el archivo original:

```powershell
target\debug\atlas-builder.exe inspect sources\z-anatomy-template\Z-Anatomy\Startup.blend `
  --out reports\experimental\blend-inspection.json `
  --fixture reports\pelvis-fixture-candidate.json
```

**Resultado esperado:**
- Identifica 7,184 objetos totales en el blend (4,569 MESH, 951 CURVE).
- Confirma la presencia y evaluación de las 26 estructuras anatómicas de la pelvis.

### Paso 3: Construir el Release del Atlas (LOD0, LOD1, Manifest y Catálogo)

Ejecuta el pipeline completo de normalización, generación de LODs y empaquetado:

```powershell
target\debug\atlas-builder.exe build reports\pelvis-fixture-candidate.json `
  --crosswalk reports\pelvis-ta2-crosswalk.json `
  --profile mobile `
  --out build\atlas\release
```

**Resultado esperado:**
- Genera `pelvis-base-lod0.glb` (681,500 bytes, Core PBR, 26 estructuras, 27 primitivas).
- Genera `pelvis-lod1.glb` (593,928 bytes, 12.56% reducción poligonal, p95 silueta <= 0.01px).
- Genera `pelvis-meshopt-lod0.glb` (169,924 bytes, 75.07% reducción, experimental).
- Genera `catalog.json` (26 estructuras TA2 con nombres en ES, EN, LA).
- Genera `manifest.json` (Atlas Manifest v1).

### Paso 4: Validar el Paquete Release

Ejecuta la batería de validación estricta de integridad:

```powershell
target\debug\atlas-builder.exe validate build\atlas\release
```

**Verificaciones automáticas ejecutadas:**
- Esquema de `manifest.json` (schemaVersion = 1, coordinateSystem +Y up / +Z anterior / +X patientLeft).
- Integridad de hashes SHA-256 de todos los paquetes contra el disco.
- Ausencia de rutas sospechosas o path traversal (`..`, `/`, `\`).
- Integridad referencial de regiones y variantes.
- Catálogo: exactamente 26 identificadores únicos, 18 estructuras bilaterales (9 pares simétricos), 8 impares.
- Modelos GLB base y LOD1: carga y decodificación real en `atlas_core::glb::parse_glb`.
- Verificación de AABBs finitas y presencia de las 26 `AnatomyId` en los nodos.

### Paso 5: Generar Reportes de Calidad, Licencias y Métricas

Genera los reportes oficiales en `reports\implementation\M03`:

```powershell
target\debug\atlas-builder.exe report build\atlas\release --out reports\implementation\M03
```

---

## 4. Pruebas Automatizadas

### Pruebas Unitarias e Integración de la CLI

```powershell
cargo test --package atlas-builder
```

Incluye pruebas adversarias para detección y rechazo de:
- Rutas con path traversal (`test_adversarial_path_traversal_rejected`).
- Hashes SHA-256 manipulados (`test_adversarial_bad_hash_rejected`).
- Paquetes duplicados (`test_adversarial_duplicate_package_id_rejected`).
- Paquetes no listados en regiones (`test_adversarial_unlisted_package_in_region_rejected`).

### Pruebas de Renderizado en Navegador Headless (Chrome / Edge)

Para validar que los modelos `pelvis-base-lod0.glb` y `pelvis-lod1.glb` renderizan en el motor WebGPU/WebGL2 real:

```powershell
python tools\test_m03_browser_headless.py
```

Capturas de pantalla generadas:
- `reports\implementation\M03\probe-pelvis-base-lod0.png`
- `reports\implementation\M03\probe-pelvis-lod1.png`

---

## 5. Códigos de Salida

| Código | Significado |
|---|---|
| `0` | Éxito total. Todas las operaciones y validaciones pasaron. |
| `1` | Error en argumentos de CLI o comando desconocido. |
| `2` | Fallo de validación, error de integridad o discrepancia de hash/archivo. |
