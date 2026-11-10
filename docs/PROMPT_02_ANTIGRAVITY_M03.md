# ANTIGRAVITY — anatom.ia — IMPLEMENTACIÓN CONTROLADA 02: ATLAS BUILDER (M03)

**Rol:** Principal Engineer especializado en anatomía 3D, Blender Python API, glTF 2.0, meshoptimizer, Rust CLI, validación de datos científicos, reproducibilidad y QA de geometría.

**Workspace ÚNICO:** C:\Users\datam\Documents\anatom.ia

**Misión:** implementar el hito M03 del proyecto existente, NO iniciar un proyecto nuevo. Convertir el pipeline experimental que ya produjo la pelvis real de Z-Anatomy en una herramienta offline **repetible, segura, versionada y verificable** que pueda emitir paquetes de atlas, catálogos y manifiestos, incluyendo primeros LOD cuando de verdad superen controles anatómicos. Debe conservar la compatibilidad de todo M00–M02, tanto WebGPU como WebGL2.

TAREA REAL DE CÓDIGO: no entregar solo diseño, pseudocódigo, README ni prototipos no ejecutables.

## 0. PREVUELO, LECTURA Y AUDITORÍA

Antes de modificar nada:
1. Leer completamente:
   - README.md
   - docs/AUDITORIA_IMPLEMENTACION_01.md
   - docs/09_BLUEPRINT_IMPLEMENTACION.md
   - docs/10_ADR_GATES.md
   - docs/05_Z_ANATOMY_FUENTE_VERIFICADA.md
   - docs/06_VALIDACION_PELVIS_Y_GLB.md
   - docs/07_RENDERER_WGPU_SPEC.md
   - docs/08_LOD_PICKING_TEST_PLAN.md
   - contracts/atlas-manifest.schema.json
   - contracts/implementation-milestones-v1.json
   - contracts/engine-bridge-v1.json
   - contracts/render-profile-v1.json
   - contracts/quality-profiles-v1.json
   - contracts/renderer-acceptance-v1.json
   - reports/pelvis-fixture-candidate.json
   - reports/pelvis-ta2-crosswalk.json
   - reports/pelvis-catalog-candidate.json
   - reports/pelvis-spatial-curve-audit.json
   - reports/pelvis-lod-policy-proposal.json
   - reports/pelvis-pbr-compat-validation.json
   - reports/audit/browser-interactions.json
   - docs/IMPLEMENTATION_01_RESULT.md
   - tools/export_pelvis_baseline.py
   - tools/inspect_fixture_spatial.py
   - tools/audit_ta2.py
   - tools/verify_pelvis_baseline.py
   - tools/verify_pbr_core_fixture.py
   - crates/atlas-core/src/glb.rs
   - crates/atlas-core/src/scene.rs

2. Inspeccionar el estado REAL de la carpeta y todos los informes, no asumir que son correctos por su título.
3. Ejecutar baseline y guardar logs antes de cambiar código:
   - cargo fmt --all -- --check
   - cargo test --workspace
   - cargo clippy --workspace --all-targets -- -D warnings
   - cargo check --target wasm32-unknown-unknown --workspace
   - python tools/verify_pelvis_baseline.py
   - python tools/verify_pbr_core_fixture.py
   - python tools/validate_stage6_contracts.py
   - python tools/validate_stage7_blueprint.py
4. Confirmar que source Git Z-Anatomy está limpio; no modificar ni registrar como propio el código de terceros.

### Referencias verificadas que debes conservar

Repositorio oficial: https://github.com/Z-Anatomy/Models-of-human-anatomy
Commit local inmovilizado: 56016ea6da9de755ee4229f61fafc2b313db66ff
Blender origen: sources/z-anatomy-template/Z-Anatomy/Startup.blend (306,838,281 B).
Referencia inmutable: reports/experimental/pelvis-pbr-core-compat.glb (681,492 B).
SHA256 de referencia: 405da36949f511b197291f2b1274d5fcdd340bb2a31d9042ee2648f8782c5797.
Cuenta de referencia: **26 IDs TA2, 26 meshes, 27 primitives, 38,605 triángulos glTF**.
El origen total posee 4,569 objetos MESH, 951 CURVE, 1,660 FONT, 1,944 colecciones. NO procesar todos inicialmente.

Blender localizado en:
C:\Program Files\Blender Foundation\Blender 4.4\blender.exe

### GATE LEGAL
Z-Anatomy declara CC BY-SA 4.0 y referencias de otros autores, algunas con licencias NoCommercial. El uso LOCAL de fixtures de prueba no autoriza distribuir activos en producción. Preserva trazabilidad, registra incertidumbre y bloquea la publicación comercial hasta revisión por asset. NO asumir que toda la pelvis o todo Z-Anatomy tiene permiso comercial explícito uniforme.

## 1. ALCANCE: SOLO M03

**IMPLEMENTAR:**
- Un Atlas Builder offline y sus herramientas Blender.
- Inventario y normalización de objetos de un proyecto Blender sin alterar el .blend fuente.
- Mapa explícito source_object -> AnatomyId -> geometría/LOD/paquete/nodo.
- Catálogo multilingüe derivado de TA2.csv con revisión de ambigüedades y lateralidad.
- Perfiles de materiales de compatibilidad glTF core.
- LOD piloto de sacro/vejiga con QA, manteniendo todos los demás órganos y vasos intactos cuando corresponda.
- Empaquetamiento GLB, hashing SHA-256, manifest, verificación de integridad, reportes de trazabilidad/licencia.
- CLI y scripts de build/validate/report ejecutables, con tests.
- Integración mínima del paquete NO comprimido en probe existente para smoke test (sin reescribir viewer).

**NO IMPLEMENTAR:**
M04: streaming/caché persistente/gestión GPU LRU avanzada, workers de fondo; M05: UI React premium/PWA; M06: AWS, producción o publicación. Nada de base de datos, backend HTTP, Three.js, cambios masivos a shaders, IA, nuevos modelos femeninos ni procesamiento del cuerpo entero.

No refactorices módulos M00–M02 salvo para arreglar una incompatibilidad real surgida en M03, con tests y documentación de causa.

## 2. ARQUITECTURA Y CONTRATOS DE ARCHIVOS

Introduce `crates/atlas-builder` como Rust CLI del workspace SI la versión/toolchain y las necesidades reales lo justifican; los scripts de Blender Python deben permanecer bajo `tools/blender/` (o equivalente documentado). No dupliques la lógica de identidad en tres sitios.

Comandos objetivo (ajusta sintaxis de flags con docs claras):
- `atlas-builder inspect <source/project-or-blend> --out <report>`
- `atlas-builder normalize <fixture-config> --out <workdir>`
- `atlas-builder build <fixture-config> --profile mobile --out <release>`
- `atlas-builder validate <release>`
- `atlas-builder report <release>`

Si `inspect .blend` necesita Blender, la CLI lo invoca de manera CONTROLADA: ruta explícita, `--background --disable-autoexec`, subprocess con exit code, timeout configurable y log; nunca ejecutar scripts embebidos por default. Debe trabajar sin acceso a red cuando todos los insumos ya están en disco.

Distinguir claramente:
- `source assets`: originales inmutables fuera de outputs.
- `staging/intermediate`: resultados temporales versionados o descartables.
- `release`: manifest.json, catalog.json, asset GLB(s), reportes.
- `fixture config`: lista explícita de los 26 objetos, sus IDs, estados de licencia y reglas de LOD.

Artefactos derivados deben quedarse en `reports/experimental/` o `build/atlas/` y NO sobrescribir las referencias ya verificadas.

## 3. IDENTIDAD CIENTÍFICA — 0 PÉRDIDAS PERMITIDAS

Mantén invariantes para las 26 estructuras:
- El ID persistente se deriva de `TA2ID` y `:left`/`:right` cuando aplique; NO usar número de nodo GLB, nombre de material ni posición de lista.
- Un AnatomyId puede mapear a múltiples primitives, pero ninguna primitive seleccionable puede mezclar dos IDs distintos.
- Un mesh simplificado conserva `extras.atlas_id`, `extras.ta2_id`, `source_object`, lateralidad y procedencia. Valida después de **cada** paso de conversión, simplificación y compresión, no solo al inicio.
- Nombres duplicados, TA2 ambiguo, lateralidad incierta, estructura sin materialidad o pieza sin origen identificado deben terminar como ERROR o REVIEW_REQUIRED; nunca crear IDs falsos.
- No dar por validado clínicamente un órgano solo por coincidencia textual TA2. Catálogo: `en`, `es-MX`, `la` y campo de revisión.
- Los 18 objetos bilaterales de fixture deben conservar mapeo de izquierda/derecha en espacio anatómico estándar.
- GLB resultante: glTF en metros, +Y superior, +Z anterior, +X izquierda anatómica; comprobar transformación con bounding boxes/anchors. No duplicar rotación al aplicar `export_yup`.
- **Round trip de identidad:** source->export->LODx->asset->runtime parser; comprobar exactamente 26/26 IDs, no solo 26 nodos anonimizados.

Fallas a vigilar:
- gltfpack puede fusionar mallas/nodos y perder extras. Evaluar `-kn` y `-ke` y demostrar mediante validator que preservan las 26 identidades ANTES de usarlo.
- Jerarquías de Blender con colecciones semánticas no son IDs.
- Some MESH with 0 polygons are markers, not bones; FONT may be labels, not renderable meshes.

## 4. CONVERSIÓN DE CURVE→MESH, MATERIALES Y NORMALIZACIÓN

Para los ocho CURVE del fixture (arterias, venas y nervios):
- Crear copias evaluadas en memoria y convertir a MESH preservando radios/bevel, transformadas, colores/materiales, nombre anatómico, topología y `atlas_id`.
- No convertir a líneas sin grosor ni perder continuidad de ramificaciones.
- Inspeccionar normales, winding, bordes degenerados y AABB finitos.
- Evitar evaluar todo Z-Anatomy innecesariamente: el análisis anterior observó memoria alta y una advertencia de ciclo ajeno al fixture.
- Los modifiers SUBSURF y SOLIDIFY de mallas de origen solo se aplican a copias; no mutar el .blend.
- Excluir FONT de la geometría, conservar metadatos útiles de etiquetas.
- Ignorar/declarar por separado marcadores MESH vacíos.
- Los materiales de publicación M03 deben ser glTF PBR CORE: color anatómico preservado, metallic 0 y rugosidad determinista por tejido, doubleSided según evidencia; sin extensiones obligatorias no soportadas.
- La referencia M02 debe continuar cargándose exactamente igual.

## 5. LOD — PILOTO MÉDICAMENTE CONSERVADOR

No imponer automáticamente 3 niveles en todas las estructuras. Partir de `reports/pelvis-lod-policy-proposal.json`.

- Sacro: LOD0 referencia 11,676 triángulos; LOD1 candidato ratio ~0.65; LOD2 opcional ratio ~0.35.
- Vejiga: LOD0 referencia 3,036 triángulos; LOD1 candidato ratio ~0.75.
- Nervios femorales (4,032 triángulos cada uno), vasos y estructuras pequeñas: preservar geometría original durante el piloto.
- Los ratios son **propuestas**, NO targets obligatorios; si el error geométrico es excesivo, rechaza LOD y registra el motivo.
- Medir triángulos, bytes, tiempo de build y desviación geométrica/silueta en cámaras idénticas.
- Definir comparación de silueta como candidata p95 ≤ 2 píxeles a viewport de 720 px; documentar el método EXACTO y capturas reales. No afirmar que se cumplió si no se renderizó/comparó.
- Verificar que no desaparezcan zonas finas, superficies articulares, conexiones y referencias clínicas.
- Respetar topología, deformación máxima, normales, no invertir lateralidad ni eliminar órganos.
- No repetir archivos LOD completos cuando solo 1–2 estructuras cambian; medir primero el beneficio frente a caché/requests.

Cuando el método de simplificación tenga restricciones imposibles, elegir un LOD idéntico/omitido y documentar FAIL/NOT_APPLICABLE; no sacrificar anatomía por reducir el tamaño.

## 6. COMPRESIÓN Y COMPATIBILIDAD RUNTIME — CRÍTICO

El visor M02 **NO implementó decodificación de `EXT_meshopt_compression`**. Es INACEPTABLE emitir solo GLB comprimidos y llamarlos compatibles con el motor.

Se permiten:
- **Paquete base obligatorio:** GLB 2.0 sin extensiones requeridas, PBR core, consumible por el parser M02. Debe funcionar en WebGPU y WebGL2.
- **Paquete comprimido experimental opcional:** meshopt/quantization para comparación, con metadata de extensiones y perfil runtime, y pruebas de round-trip; si el motor no tiene decoder, marcar `runtimeCompatible=false` y nunca cargarlo en el probe.
- **No usar Draco/KTX2 por default**; agrega un decoder solo si está justificado y probado, fuera de este hito.

Preservar nodos y metadata con flags adecuados o post-procesamiento, pero NO falsificar extras faltantes. Si gltfpack vuelve inseparables nervio/vaso/órgano, descartar ese paquete.

Publicar `requiredExtensions` en manifest con validación cruzada real. No afirmar que `glTF 2.0 válido` implica que el parser actual lo soporta.

## 7. MANIFEST, CATÁLOGO, LICENCIAS Y TRAZABILIDAD

Usar como contrato de verdad `contracts/atlas-manifest.schema.json`; no crear otro manifest incompatible ni reescribirlo en silencio. Conservar:
`schemaVersion`, `atlasVersion`, `coordinateSystem`, `catalog`, `variants`, `regions`, `packages`, `bytes`, `sha256`, `encoding`, `requiredExtensions`.

Un validador externo debe comprobar:
- JSON Schema, claves requeridas y tipos.
- Integridad hash SHA-256 de cada archivo.
- URI relativas seguras y resolución dentro de carpeta de release.
- Unicidad de package IDs y referential integrity en regions->packages.
- Catálogo íntegro: 26 IDs sin pérdida, laterality consistente, nombres multilingües.
- Node extras preserved en GLB y binding de catálogo.
- Paquetes LOD ordenados/coherentes y forma de detectar perfiles incompatible.
- No metadata de versión o fecha no determinista en paquetes inmutables.

Reportes obligatorios:
- `build-report.json`: source -> object -> AnatomyId -> mesh/primitive -> lod -> package; conteos, tiempos, parámetros de build.
- `validation-report.json`: errores, warnings, esquema, hashes, IDs, geometría.
- `license-report.json`: fuente, licencia conocida, excepción de terceros, evidencia, atribución requerida y `commercial_release_allowed` como **UNKNOWN/FALSE** hasta auditoría real.
- `quality-report.json`: error silueta/geométrico, reducción por estructura, decisiones LOD PASS/REJECTED/NOT_RUN.
- `release-manifest.json` solo si es necesario como índice secundario, NO reemplaza `manifest.json`.

La fuente masculina no genera automáticamente `female-adult`; solo publicar variant `male-adult` disponible. Colecciones femeninas del .blend no contienen esas mallas.

## 8. TESTS Y GATE G-M03

Ejecuta tests unitarios, integración y seguridad:
1. Verificar scripts de baseline y nuevos tests sin regresiones, `cargo fmt/test/clippy/check` cuando corresponda.
2. Repetir dos builds WASM (WebGPU y WebGL2) SOLO si cambiaste código del motor/adaptador.
3. Fuente `.blend` y repositorio original intactos (git status limpio y hash de fuente si está disponible).
4. Exactamente 26 AnatomyIds en catálogo y en paquete base, 18 bilaterales correctos, 27 primitives en baseline de referencia.
5. Validar que al menos una estructura de dos primitives continúa seleccionable con mismo ID.
6. Efectuar tests negativos: manifest con path traversal, SHA erróneo, reference package faltante, duplicate ID, missing extras, malformed accessor, extension no soportada, LOD que perdió una estructura, material corrupto, nombres TA2 ambiguos.
7. Validar parser Rust de M02 con el nuevo paquete NO comprimido.
8. Abrir la pelvis recién compilada en probe existente en Chrome headless con `?backend=webgl2` y `?backend=webgpu`, comprobar primer frame, 26 estructuras y operaciones básicas.
9. Screenshots de LOD originales/candidatos cuando se hayan generado, con cámaras y formato idéntico para comparaciones; no inventar métricas.
10. Medir tiempo y memoria de Blender para el fixture, evitando procesar toda la biblioteca.
11. Comparar bytes/triángulos originales vs optimizados, no solo contar objetos.
12. Conservar la salida no comprimida como fallback cuando falten features.
13. Verificar que M04/M05 no se implementaron incidentalmente.

G-M03 = PASS SOLO SI: el build offline es reproducible, manifest/catalog/GLB validan, provenance y restricciones se registran, source->LOD conserva IDs, baseline no regresiona y nuevo paquete base renderiza en ambos backends.

Un LOD candidato REJECTED no implica fallar M03 si se hizo la comparación correctamente y el pipeline conserva la geometría de referencia. Una medición NOT_RUN no puede contarse como PASS. Si la auditoría visual de LOD no puede ejecutarse, deja ese subgate abierto.

## 9. EVIDENCIA, INFORME Y LIMITACIONES

Crear:
- `docs/IMPLEMENTATION_02_RESULT.md` (secciones A–J: qué se construyó, qué falló y qué no)
- `docs/BUILD_ASSETS.md` (build offline en Windows)
- `reports/implementation/M03/...` (logs, JSON, screenshots genuinas)
- `reports/implementation/implementation-02-status.json`

El informe incluirá:
A. Archivos nuevos/modificados y causa.
B. Toolchains/versions y comandos realmente ejecutados.
C. CLI inspect/normalize/build/validate/report: PASS/FAIL por comando.
D. Datos sobre la fuente Blender y 26 estructuras/8 curvas.
E. IDs TA2/mapeo por LOD y registro de errores.
F. Compresión, tamaño, extensiones y compatibilidad del parser.
G. Manifest, catálogo, SHA y matriz de procedencia/licencias.
H. Pruebas negativas, render smoke en ambos backends, cifras realmente medidas.
I. Gates abiertos, fallos y cambios mínimos necesarios antes de M04.
J. Confirmación de que M00–M02 sigue funcionando y Z-Anatomy no se modificó.

No alterar `reports/experimental/pelvis-pbr-core-compat.glb` ni sobrescribir el GLB de referencia. No modificar `reports/audit/` existentes para fingir capturas nuevas. Las nuevas evidencias van a `reports/implementation/M03/`.

## 10. PROTOCOLO DE EJECUCIÓN

1. Lee especificaciones y código actual COMPLETO, verifica baseline.
2. Haz microplan M03 con outputs concretos. No rediseñes arquitectura.
3. Implementa CLI + selección segura Blender + normalización/crosswalk.
4. Produce paquete base y reportes; valida con scripts externos.
5. Implementa LOD piloto de sacro/vejiga solo si el método preserva identidad y geometría.
6. Evalúa compresión opcional contra paquete base, sin romper compatibilidad.
7. Integra el paquete base en probe para smoke, sin tocar rendering core salvo necesidad demostrada.
8. Ejecuta tests negativos, build reproducible y pruebas de ambas GPUs.
9. Repite toda la suite M00–M02 afectada; no avances a M04.
10. Redacta informe CON EVIDENCIAS y tabla PASS/FAIL/NOT_RUN/BLOCKED.

**PRIORIDAD:** integridad anatómica e identidad > compatibilidad real con M02 > reproducibilidad > testabilidad > optimización > reducción de bytes. Un supuesto ahorro del 50% que pierde un nervio o TA2 es un FAIL absoluto.

**ENTREGA:** Atlas Builder offline ejecutable y validado para la pelvis del proyecto, con primer release experimental consistente, informes honestos y SIN iniciar M04–M06. No digas que está listo para producción.
