# Etapa 5 — TA2, geometría espacial y primer GLB de pelvis

**Fecha:** 2026-11-09. **Estado:** auditoría/exportación experimental aprobada; renderizado Rust/LOD/meshopt/comercialización NO aprobados.

## Fuente y procedencia
- Repositorio: https://github.com/Z-Anatomy/Models-of-human-anatomy
- Commit: `56016ea6da9de755ee4229f61fafc2b313db66ff`.
- Archivo maestro: `sources/z-anatomy-template/Z-Anatomy/Startup.blend`.
- Se abrió en Blender 4.4.3 con `--background --disable-autoexec`. No se ejecutaron scripts embebidos, no se guardó ni modificó la fuente.
- Toda exportación se produjo a partir de copias temporales en memoria. El resultado es **para validación local**, sujeto a auditoría de licencias por objeto.

## A. Correspondencia TA2
- `tools/audit_ta2.py` corrigió la envoltura entre comillas de cada línea de `TA2.csv` y leyó 7,314 registros.
- Los 26 candidatos encontraron **un único TA2ID por nombre normalizado exacto** (inglés/latín).
- Se preservó la lateralidad `.l` / `.r` en identificadores `ta2:<id>:left` y `ta2:<id>:right`. Ningún fuzzy match se aceptó como definitivo.
- `reports/pelvis-ta2-crosswalk.json`: 26 correspondencias léxicas, todas `review_required=true`.
- `tools/build_catalog_candidate.py` generó `reports/pelvis-catalog-candidate.json`: traducciones español/inglés/latín, fuente, lateralidad, centro espacial, tipo y licencia pendiente.
- Comprobación de signo X en los 18 objetos bilaterales: **0 advertencias**.
- Es un crosswalk de etiquetas, no demuestra que la anatomía modelada esté clínicamente validada.

## B. Sistema de coordenadas
Archivo Blender original (observado):
- `scene.unit_settings.system = METRIC`, `scale_length = 1.0`, `length_unit = CENTIMETERS`; esto último controla el formato de visualización, no reescala las coordenadas internas.
- Las posiciones medidas son compatibles con unidades Blender representando metros: sacro cerca de z=0.923 y vejiga cerca de z=0.855.
- +Z superior; +X izquierda anatómica; -Y anterior, inferido de testículos y glande respecto al sacro/vejiga.
- La exportación glTF `export_yup=True` transforma hacia +Y superior, +Z anterior y mantiene +X izquierda anatómica.
- Los nodos GLB muestran ejes transformados coherentemente; validación anatómica final de escala/orientación sigue pendiente.

## C. Curvas y modificaciones
- En el fixture hay 18 MESH y 8 CURVE.
- Se evaluaron en Blender sin convertir el origen: **5,616 polígonos** provenientes de CURVE.
- Las 8 curvas tenían bevel depth 0.0005 unidades Blender en la evaluación.
- Las 18 mallas incluían subdivisión/solidify según objeto; Blender evaluó sus modificadores antes de crear copias temporales.
- Total MESH nominal del fixture sin modificadores: **17,221 polígonos**.
- Total de geometría evaluada exportada (MESH + CURVE, con modificadores): **25,717 polígonos**.
- Advertencia: la evaluación de toda la escena en Blender requirió memoria elevada y produjo una advertencia ajena al fixture sobre dependencia del esófago. Antes del builder productivo hay que aislar un escenario de trabajo mínimo para no evaluar los 7,184 objetos.

## D. Colecciones femeninas
- `Female genital system'`, `Female internal genitalia'`, `Female external genitalia'` y colecciones de uretra femenina contienen **0 objetos directos y 0 objetos descendientes** en este archivo.
- No se afirma que el modelo femenino esté presente. Se requiere integración de otras mallas con registro espacial y revisión de licencias.

## E. Exportación experimental
- Herramienta: `tools/export_pelvis_baseline.py`.
- Archivo: `reports/experimental/pelvis-baseline-uncompressed.glb`.
- Tamaño: **682,900 bytes** (aprox. 667 KiB).
- SHA-256: `8c9a107824bc11c64551cb3452c63395af35abf1fbbf9a9c058f074d2954ca47`.
- 26 nodos identificables; 26 meshes; 27 glTF primitives; 10 materiales; ninguna textura.
- Por cada nodo: extras `atlas_id`, `ta2_id`, `patient_side`, `source_object`, `source_kind` y `license_state`.
- Sin meshopt, sin Draco, sin LOD, sin cliente Rust ni prueba visual final. **No llamar optimizado** a este archivo base.
- Blender emitió `KHR_materials_specular` y `KHR_materials_ior` como `extensionsUsed`, ninguna en `extensionsRequired`. La implementación debe usar un perfil básico PBR o degradación validada antes de WebGL2.
- `reports/pelvis-baseline-export-report.json` guarda las métricas de exportación.

## F. Validación independiente
- `tools/verify_pelvis_baseline.py` lee cabecera y chunks de GLB, verifica 26 IDs, nombres fuente, meshes válidos y hashes.
- Resultado: **PASS**. 0 missing, 0 extra, 0 wrong source, 0 invalid meshes, 0 missing meshes.
- `reports/pelvis-baseline-validation.json` contiene evidencia reproducible.
- No significa validación de materialidad/correcta renderización, calidad clínica ni tasas FPS.

## G. Decisiones para la próxima implementación
1. Materiales: un perfil PBR reducido con colores anatómicos fiables y fallback WebGL2; extensiones avanzadas opcionales y explícitamente autorizadas.
2. Exportador: procesar únicamente objetos seleccionados, con conversión independiente de CURVE y aplicación de modificadores **en copias temporales**, siempre preservando ID.
3. Source graph: no aplanar categorías colecciones ni reemplazar IDs estables por índices glTF.
4. Introducir LOD después de medir error geométrico de huesos, vasos y nervios; no usar ratio único global.
5. glTF 2.0 sin comprimir es referencia de integridad; optimizar con meshoptimizer una vez haya round-trip y fallback validados.
6. Mantener todos los assets derivados en ámbito local experimental hasta resolver permisos/licencias.

## H. Gates
| Gate | Estado | Evidencia |
|---|---|---|
| G0: origen real | PASS | Commit + Startup.blend |
| G0.1: mapeo léxico TA2 | PASS léxico | 26/26, revisión anatómica pendiente |
| G0.2: lateralidad | PASS geométrico preliminar | 0 warnings por signo de X |
| G0.3: CURVE→MESH | PASS experimental | 8 curvas, 5,616 polígonos |
| G0.4: GLB y extras | PASS | 26 IDs, validador estructural |
| G0.5: materiales WebGL2 | PENDIENTE | extensiones opcionales presentes |
| G0.6: LOD/meshopt | PENDIENTE | baseline sin comprimir |
| G1: render Rust WebGPU/WebGL2 | NO INICIADO | motor no implementado |
| G2: integridad anatómica clínica | PENDIENTE | revisión humana requerida |
| G3: licencia comercial | BLOQUEADO | auditoría por asset |
| G6: rendimiento móvil | NO INICIADO | falta hardware/benchmark |

## Reproducción desde PowerShell
```powershell
$root = 'C:\Users\datam\Documents\anatom.ia'
$blender = 'C:\Program Files\Blender Foundation\Blender 4.4\blender.exe'
$source = "$root\sources\z-anatomy-template\Z-Anatomy\Startup.blend"
python "$root\tools\audit_ta2.py"
& $blender --background --disable-autoexec $source --python "$root\tools\inspect_fixture_spatial.py"
python "$root\tools\build_catalog_candidate.py"
& $blender --background --disable-autoexec $source --python "$root\tools\export_pelvis_baseline.py"
python "$root\tools\verify_pelvis_baseline.py"
```
Los comandos escriben únicamente en `reports/`, pero requieren memoria considerable para abrir la escena Blender completa. No se deben ejecutar en paralelo en una máquina con poca RAM.

**Resultado:** el pipeline básico de extracción/identidad es técnicamente viable. El siguiente hito es el prototipo mínimo Rust/WASM/WebGL2-WebGPU, junto a un perfil PBR de compatibilidad y LOD de prueba, no un backend tradicional ni una interfaz final.
