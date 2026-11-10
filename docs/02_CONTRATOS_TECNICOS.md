# Contratos técnicos v1 — Atlas Engine

## A. Límites de responsabilidades
- **atlas-builder (offline):** inspección, normalización, identidad, LOD, compresión y validación; publica paquete GLB/manifest/catalog/licencias.
- **atlas-core (Rust):** anatomía runtime, scene graph, cámara, GPU renderer, picking, scheduler y recursos residentes.
- **atlas-web (adaptador WASM):** canvas, red, caché, eventos de entrada, transición web y puente asíncrono al núcleo.
- **atlas-viewer (React):** paneles, búsqueda y controles; no posee geometría ni renderiza frames.
- **Hosting:** S3 + CDN sin API dinámica en MVP.

## B. Convención espacial
- Unidades de salida metros; mano derecha; +Y superior, +Z anterior, +X izquierda anatómica.
- Se requiere registrar y validar orientación, escala y transformación del modelo origen. El modelo original no se modifica.
- Un ID anatómico es un concepto estable. El ID de nodo GLB y el runtime handle NO son persistentes.
- Múltiples partes pueden compartir `anatomy_id`; cada parte mantiene su identidad de componente si es necesario.
- El registro entre variantes es explícito, nunca mediante reuso ciego de transformaciones masculinas.

## C. Contratos de publicación
- `manifest.json`: datos de release, regiones, variantes, paquetes y huellas SHA256; esquema JSON en `../contracts/atlas-manifest.schema.json`.
- `catalog.json`: `anatomy_id` único, nombres, lateralidad, región, sistema, relaciones tipadas y `representations`.
- Cada paquete: GLB 2.0 autocontenido; hash calculado sobre bytes finales. Solo extensiones aprobadas por perfil.
- Reportes: `build-report.json`, `validation-report.json`, `license-report.json`.
- `current.json` mutable apunta a release inmutable; el cliente inmoviliza release durante una sesión.
- URLs relativas resueltas contra origen configurado; prohíbe `..` y referencias externas arbitrarias.

## D. Identidad
- `AnatomyId = string` estable, sin dependencia de índices glTF.
- `RepresentationId = variant/region/lod/version`.
- `RenderPartId = package/node/primitive` efímero y verificable.
- Toda primitive exportada mapea a exactamente una estructura seleccionable o a un objeto decorativo/no seleccionable explícito.
- El build falla con colisión de IDs, malla sin mapa o referencia de paquete rota.

## E. Contrato host ↔ motor
Comandos: `loadRegion(region,variant)`, `focus(id)`, `select(id)`, `setVisibility(id,bool)`, `setOpacity(id,0..1)`, `isolate(id)`, `resetVisibility()`, `resetCamera()`, `dispose()`.
Eventos: `ready`, `loadProgress`, `regionReady`, `structureSelected`, `sceneChanged`, `qualityChanged`, `error`.
- Todas las operaciones de carga tienen `request_id` y `scene_generation`.
- `loadRegion` devuelve estado aceptado/cancelado/error. `regionReady` solo se emite tras tener LOD base renderizable.
- Los mensajes de progreso pueden ser desconocidos (`progress=null`), no se inventan porcentajes.
- UI no recibe geometry buffers ni envía estado duplicado en cada frame.

## F. Máquina de estados del paquete
`NotRequested -> Queued -> Fetching -> Verifying -> Decoding -> Uploading -> Resident`.
Rutas terminales o reversibles: `Cancelled`, `Failed`, `Evicted`; reintentos con backoff acotado cuando la causa es recuperable.
- Cache hit se verifica contra hash/longitud si la fuente no es de confianza.
- Al cancelar, trabajos tardíos no mutan escena activa; pueden poblar caché si íntegros.
- LOD inferior se mantiene hasta reemplazo completo por LOD superior.
- Un bloque de CPU decodificado se libera cuando GPU deja de necesitarlo y no está reservado por política explícita.

## G. Gestión de GPU/memoria
- Un solo resource registry con handles generacionales y referencias de uso, no punteros GPU en la UI.
- Presupuestos separables: GPU residency estimada, CPU decoded geometry, inflight decompress y caché de disco.
- Preflight antes de asignaciones; límites a accessor counts, buffers, texturas y profundidad GLB.
- El frame render loop se suspende cuando escena está quieta.
- Subida GPU por presupuesto por fotograma; calidad y resolución dinámica controlada.
- En `DeviceLost`, reconstruir pipelines y activos necesarios; escena lógica persiste.
- El fallback WebGL2 es un perfil de capabilities, no la presunción de compatibilidad de cada shader.

## H. Selección
- Broad phase con AABB/índice espacial, narrow phase ray-triangle en CPU.
- Solo superficies visibles y seleccionables participan.
- Mapping hit→anatomy_id respetado en todos los LOD.
- Hit test con tolerancia de touch limitada y reglas de desempate documentadas.
- Ninguna lectura GPU síncrona obligatoria en el camino interactivo.

## I. Seguridad
- Archivos externos como datos no confiables: límites de tamaño, índices, offsets, NaN, extensiones, jerarquía, compresión y expansión.
- Validar esquema, hashes, MIME y contadores antes de subida GPU.
- Sin scripts ni recursos externos ejecutables embebidos.
- Catálogo y atribución científicos separados de parámetros de UI.

## J. Compatibilidad y control de cambios
- Schema version entero con evolución semántica y migraciones explícitas.
- Ruptura de contrato requiere cambio de versión y pruebas de consumidor.
- La versión de wgpu/Rust/WASM se fija en lockfile en fase de implementación; validación WebGL2 en CI y hardware.
- Los thresholds se fijarán después de benchmark, nunca se declaran cumplidos anticipadamente.

## K. Requisitos derivados del archivo real Z-Anatomy (auditado 2026-11-09)
- La fuente contiene 4,569 MESH, 951 CURVE y 1,660 FONT. El contrato de importación debe distinguir estos tres tipos.
- CURVE corresponde entre otros a nervios y vasos reales. Antes del GLB, convertir geometría a MESH manteniendo grosor, color, transformaciones y `anatomy_id`, con informes de errores de teselado.
- FONT comprende etiquetas de Blender; extraer texto/metadatos cuando aporte identidad, pero no convertir todos los FONT a triángulos.
- Algunos MESH son marcadores con cero polígonos; excluirlos del paso de render o convertirlos a puntos de referencia según corresponda, sin asignarlos erróneamente como órganos.
- Colecciones de Blender pueden representar etiquetas conceptuales sin geometría; una colección `Female genital system` no demuestra presencia de órganos femeninos.
- El crosswalk de `TA2.csv` (separador ;) y mallas requiere lateralidad, equivalencias de sinónimos y revisión manual cuando haya ambigüedad.
- El fixture candidato de 26 objetos incluye 8 CURVE que no deben omitirse durante exportación. Fuente y detalle: `docs/05_Z_ANATOMY_FUENTE_VERIFICADA.md`.
