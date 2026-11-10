# Auditoría local — 2026-11-09

## Directorio de trabajo
- Ruta: `C:\Users\datam\Documents\anatom.ia`
- Estado inicial: carpeta vacía. Se creó estructura de documentación y validación.
- No se encontró material Z-Anatomy dentro del proyecto.

## Entorno observado
- Windows, sesión Desktop Commander dispositivo `lae`.
- Rust `1.97.1`, Cargo `1.97.1`.
- Node.js `v22.16.0`.
- Python `3.13.5`.
- Git accesible.
- GPUs: NVIDIA GeForce RTX 4070 Laptop e Intel UHD Graphics.
- Blender 4.4 localizado en `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe` (fuera de PATH). `gltfpack` y `wasm-pack` no detectados en PATH.
- No se hallaron nombres `z-anatomy` ni archivos `.blend` en la búsqueda inicial bajo Documentos; esa búsqueda no cubre todos los discos ni carpetas.

## GLB candidatos, NO verificados como fuente Z-Anatomy

1. `C:\Users\datam\Documents\first mesh.glb`
   - 129902956 bytes, GLB 2.0, Blender glTF I/O 4.4.56.
   - 1 mesh, 1 primitive, 2 nodes, 1 material, 0 texturas.
   - 1,998,230 triángulos nominales según accessor indexado.
   - Sin campo copyright en asset; procedencia no acreditada.

2. `C:\Users\datam\Documents\jace_0_improved_color.glb`
   - 9992344 bytes, GLB 2.0, Blender glTF I/O 4.4.56.
   - 1 mesh, 1 primitive, 2 nodes, sin materiales declarados.
   - 92,556 triángulos nominales.
   - Sin campo copyright en asset; procedencia no acreditada.

Un archivo con una sola primitive puede contener partes visuales distinguibles por colores, pero NO garantiza IDs de estructuras ni visibilidad independiente. Estos GLB no se utilizarán como prueba de integridad anatómica.

## Riesgos abiertos y acciones
- **R1 — Bloqueante:** localizar/recibir fuente original con estructuras separadas.
- **R2 — Bloqueante para distribución:** validar licencia por archivo, autor y restricciones de terceros.
- **R3 — Bloqueante para pipeline completo:** Blender localizado; falta inspeccionar la estructura real de la fuente original.
- **R4 — Técnico:** demostrar WebGL2 con el conjunto mínimo de features, compresión y shaders.
- **R5 — Rendimiento:** medir móviles físicos (las GPUs de este PC no sustituyen esa validación).

## Evidencia
- Metadatos recolectados con `tools/inspect_glb.py` en modo lectura.
- Resultado en `reports/local-candidate-glb.json`.
- No se decodificó la geometría ni se alteraron modelos originales.

## Actualización posterior: fuente Z-Anatomy localizada
El usuario identificó el repositorio https://github.com/Z-Anatomy/Models-of-human-anatomy. Fue clonado en `sources/z-anatomy-upstream` al commit `56016ea6`; se extrajo `Startup.blend` (306.8 MB) para inspección de solo lectura mediante Blender 4.4. Inventario real: 7,184 objetos, 4,569 MESH, 951 CURVE, 1,660 FONT, 1944 colecciones y 3,655,404 polígonos MESH nominales. La auditoría exhaustiva del origen está en `docs/05_Z_ANATOMY_FUENTE_VERIFICADA.md`.
Se identificó una propuesta de 26 objetos pélvicos en `reports/pelvis-fixture-candidate.json`. No se han creado paquetes GLB ni se han validado licencias individuales.
