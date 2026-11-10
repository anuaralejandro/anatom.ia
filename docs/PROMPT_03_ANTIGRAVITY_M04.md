# ANTIGRAVITY — ANATOM.IA / IMPLEMENTACIÓN 03: M04 ASSET STREAMING, CACHE, MEMORY Y DEVICE RECOVERY

**Rol:** Principal Rust WebGPU/WASM Reliability Engineer + Senior Browser Storage/Performance Engineer.
**Workspace único:** `C:\Users\datam\Documents\anatom.ia`
**Repo existente:** `https://github.com/anuaralejandro/anatom.ia` (PUBLIC, rama main).
**Alcance exclusivo:** M04; no M05 React, no M06 AWS/publicación, no procesamiento masivo de anatomía.
**Propósito:** convertir el visor M02 y builder M03 ya auditados en un **runtime de assets escalable, recuperable y eficiente**. Implementación REAL con código, tests e informes auditables.

## REGLA 0 — PRESERVAR EL ESTADO REAL, NO REHACERLO

ANTES DE MODIFICAR NADA, leer COMPLETOS:
- `README.md`
- `docs/AUDITORIA_IMPLEMENTACION_01.md`
- `docs/AUDITORIA_IMPLEMENTACION_02.md` (**OBLIGATORIO; prevalece sobre reportes originales de Antigravity**)
- `reports/audit/m03-independent-verdict.json`
- `reports/audit/m03-real-silhouettes.json`
- `reports/audit/m03-dual-backend-browser.json`
- `docs/09_BLUEPRINT_IMPLEMENTACION.md`, `docs/10_ADR_GATES.md`
- `docs/07_RENDERER_WGPU_SPEC.md`, `docs/08_LOD_PICKING_TEST_PLAN.md`
- `contracts/atlas-manifest.schema.json`
- `contracts/engine-bridge-v1.json`
- `contracts/quality-profiles-v1.json`, `contracts/render-profile-v1.json`
- `contracts/renderer-acceptance-v1.json`, `contracts/implementation-milestones-v1.json`
- `build/atlas/release/manifest.json` y `catalog.json`
- `crates/atlas-core/src/` completo, especialmente scene, renderer, glb, picking, camera, types
- `crates/atlas-web/src/lib.rs` completo
- `apps/probe-web/app.js`, `index.html`, `tools/serve_probe.py`
- `crates/atlas-builder/src/build.rs`, `report.rs` y `validate.rs`.

**NO CONFUNDAS DATOS:** LOD0 tiene **38,605 triángulos glTF** y LOD1 **33,758**. Los 29,210→25,542 previos eran conteos de polígonos Blender, no triángulos runtime. Se preservan 26 IDs TA2 y 27 primitivas. Calidad del piloto: diferencia de bordes de siluetas rasterizadas máxima 1 px en 5 vistas; NO implica aprobación clínica.

**ANTES:** ejecutar `git status --short`, `git remote -v` y los tests de baseline. Hay cambios locales de auditoría importantes SIN subir a GitHub: NO hacer reset/checkout forzado/stash destructivo, NO sobreescribir reportes corregidos. Si vas a trabajar en rama, crear una rama local separada preservando exactamente los cambios; no asumir que main remoto representa el estado auditado.

### VERIFICACIÓN BASELINE
Ejecutar y guardar comandos con resultados reales:
```powershell
cargo fmt --all -- --check
cargo clippy --workspace --all-targets -- -D warnings
cargo test --workspace
cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder
python tools/verify_pelvis_baseline.py
python tools/verify_pbr_core_fixture.py
python tools/validate_stage6_contracts.py
python tools/validate_stage7_blueprint.py
python tools/audit_m03_browser_dual.py
```
El último test requiere Chrome/Playwright; si falta una dependencia marca BLOCKED, no inventes resultados.

## 1. LÍMITES NO NEGOCIABLES

- Mantener **un único núcleo de escena Rust**, con `wgpu` v30 y dos backends WASM: WebGPU y WebGL2.
- No sustituir Rust renderer por Three.js/Babylon/ECS ni copiar escena completa en TypeScript.
- **No implementar M05:** sin React, UI final, sistema de usuarios, autenticación, tutor IA, backend ni CMS.
- **No implementar M06:** sin deploy AWS/S3/CloudFront, servicios públicos, Docker de servidor, CDN real, GitHub Release ni publicación de activos.
- **No implementar meshopt decoder** por defecto: `pelvis-meshopt-lod0.glb` es experimental incompatible con el parser actual. M04 DEBE detectarlo y excluirlo del runtime; cualquier intento de cargarlo tiene que fallar con error tipado sin crash.
- No modificar `sources/z-anatomy-upstream/`, `Startup.blend`, GLB de referencia ni geometría/TA2/catálogos salvo corrección mínima demostrada.
- Repositorio de GitHub **público**: no añadir ni subir `.blend`, `.glb`, fuentes de terceros ni capturas nuevas de modelos sin revisión de licencias. No hacer push ni merge automático; preparar changeset local para revisión posterior.
- No afirmar FPS, RAM GPU ni ahorro de red sin medición real.
- No forzar service worker/PWA todavía: el cache programático del navegador debe funcionar sin SW.

## 2. M04-A — MANIFEST RESOLVER Y NEGOCIACIÓN DE PAQUETES

Crea capa canónica para consumir `manifest.json` y `catalog.json` de M03:
- Resolver versión v1, `atlasVersion`, SHA-256, bytes, variants, regions, packages, LOD, encoding, extensiones y rutas relativas.
- No permitir URL absolutas externas, traversal, queries de origen arbitrario, symlink escapes en herramientas offline ni `data:` inyectado desde manifest.
- Verificar un SOLO par región/variante existente; `pelvis` + `male-adult`. Rechazar variantes femeninas no publicadas, sin inventar modelo femenino.
- Preferir paquetes `encoding: none` con `requiredExtensions: []`; comprobar exactamente restricciones del parser antes de descargar. Excluir meshopt/quantization no decodificable.
- No interpretar `lod: 0` como el modelo barato; LOD0 tiene mayor resolución que LOD1. En dispositivos limitados, paquete LOD1 primero si tiene soporte y métrica; en alto, LOD0 puede ser preferido.
- Resolver rutas de release INMUTABLES, versionadas o con hash; no permitir mezclas `manifest vA` + `asset vB`. Verificar SHA-256 de bytes antes del parser o antes de abrir desde cache.
- Compatibilidad con `manifest` histórico de tres paquetes (meshopt incluido pero omitido) y el nuevo build offline de dos paquetes.

Diseño Rust propuesto: `AssetDescriptor`, `ManifestSnapshot`, `PackageSelector`, `RegionLoadPlan`, errores tipados; núcleo agnóstico al DOM. La implementación de fetch/caché se realiza en la frontera web, mediante adaptadores de transporte. No duplicar deserialización/selección del manifest en Rust y JavaScript.

## 3. M04-B — ASINCRONÍA, CANCELACIÓN Y ESTADO DE CARGA

Implementar una máquina de estados auditable:
`NotRequested -> Queued -> Fetching -> Verifying -> Decoding -> Uploading -> Resident`; rutas `Cancelled`, `Failed`, `Evicted`.

- `loadRegion(regionId, variantId, requestId)` devuelve Promise/respuesta tipada con `sceneGeneration`.
- Cada intención de carga/cambio de LOD incrementa token de generación por instancia de engine (NO static global que mezcle instancias); los resultados anteriores no pueden mutar escena ni GPU.
- AbortController cancela fetch; aunque una operación Wasm no se pueda interrumpir, el resultado obsoleto se descarta y libera.
- Dos cambios rápidos (A→B→A), reintentos, abortos, timeout, desmontaje, cambio de backend y llamadas duplicadas no deben crear estado zombie ni prompts de permisos.
- Carga inicial visible: no declarar `region.ready` solo al terminar fetch; emitir después de tener la geometría renderizable y comprobable.
- Mantener la escena anterior hasta que nueva geometría sea válida (switch atómico cuando presupuesto permita); ante error preservar selección y contenido previamente válido.
- Controlar errores `NETWORK_ERROR`, `ASSET_CORRUPT`, `ASSET_UNSUPPORTED_EXTENSION`, `MEMORY_LIMIT`, `CANCELLED`, `GPU_DEVICE_LOST`, `REGION_UNAVAILABLE` con campos `recoverable`, `requestId`, `sceneGeneration`.
- Evitar colisiones entre `loadGlbBytes` diagnóstico M02 y `loadRegion` nuevo: mantener API previa y tests.
- No bloquear innecesariamente event loop; medir parse/decode de GLB de pelvis y decidir si realmente necesita worker. No introducir workers complejos sin números.

## 4. M04-C — CACHÉ INTEGRIDAD Y OFFLINE

Crear persistencia best-effort para binarios `manifest/catalog/assets`:
- Preferir `Cache Storage` o `IndexedDB` según análisis del entorno; describir elección con ADR breve. No introducir ambos por inercia.
- Claves de cache por `atlasVersion + packageId + SHA256`; nunca reusar archivo con digest inválido.
- Cache miss -> fetch -> verificar tamaño/digest -> parse -> almacenar solo si pasó integridad.
- Cache hit -> verificar consistencia mínima/digest y volver a usar sin red; si corrupto: borrar entrada y re-descargar si red; si offline: error recuperable, no render corrupto.
- Manejar ausencia de permisos, cuota excedida, eviction del navegador, modo privado y políticas de almacenamiento: seguir con navegación online sin bloqueo.
- Configurar concurrency inicial conservadora según `quality-profiles-v1.json` (low=2, medium=3, high=4; hipótesis, medir). Evitar descargas concurrentes duplicadas del mismo hash.
- Test explícito: primera visita en línea, recarga con red apagada desde caché persistente; perder caché y red = error recuperable, nunca un falso `ready`.
- No cachear assets no autorizados en infraestructura externa. La prueba local no concede licencias para publicar.

## 5. M04-D — GESTIÓN DE CPU/GPU Y CAMBIOS LOD

- Implementar memoria estimada a partir de bytes reales de buffers/upload/geom CPU, con estadísticas `resident bytes`, `decoded bytes`, `cache bytes`, `evictions`, `request generation`; NO presentar `performance.memory` como memoria VRAM real.
- Presupuestos iniciales provisionales: low GPU 64 MiB / CPU decoded 48 MiB, medium 128/96, high 256/160; caps efectivos nunca exceden límites adapter.
- LRU con protección de recurso visible/seleccionado y referencias GPU generacionales, sin use-after-free. No liberar mesh mientras está en draw/command submission; identificar fase segura.
- LOD1 reducido como degradación conservadora; LOD0 como detalle. Conmutación atómica preservando los 26 IDs, `selectedId`, visibilidad, aislamiento, matriz/cámara y `sceneRevision`. Comparación de geometría/intersección no debe devolver IDs cambiados.
- Para la pelvis, evalúa si conviene retener ambas mallas o descargar una al alternar; medir pico CPU/GPU, no suponer VRAM infinita. Preferir cache de bytes verificados a cache doble de GPU.
- `dispose()` idempotente: cancela jobs, suelta recursos y listeners del navegador.
- Adaptación de calidad solo con mediciones e histéresis; no bajar/subir LOD cada frame (thrashing).
- Render-on-demand continúa vigente; no crear loop infinito al estar inactivo.

## 6. M04-E — GPU LOSS, RECOVERY Y FALLBACK

- Diferenciar SurfaceLost/Outdated/Timeout/OutOfMemory de pérdida real del Device. Verificar comportamiento real de `wgpu 30` y browser WebGPU/WebGL2.
- Reconfigurar surface/descriptores correctos cuando es recuperable; si DeviceLost, reconstruir device/pipelines/buffers y volver a cargar desde bytes verificados, conservando estado anatómico si posible.
- Cambiar WebGPU→WebGL2 creando canvas nuevo cuando navegador impida reutilizar contexto, sin tocar shaders con features WebGL2 no permitidas.
- Máximo limitado de reintentos con backoff; prohibido retry loop infinito. Si ambos backends fallan: mostrar error explícito.
- Si un test solo SIMULA loss, reportar `SIMULATED_PASS`, no afirmar recuperación de driver real. Test físico cuando pueda ejecutarse.

## 7. BRIDGE RUST ↔ WEB Y PROBE MÍNIMO

- Mantener propiedad Rust de escena/cámara/selección/GPU.
- Extender bridge versión 1 existente con `loadManifest` o `configureAssets`, `loadRegion`, `setQualityProfile`, `cancelLoad`, `getMemoryStats` y eventos apropiados, siempre compatibilizando `engine-bridge-v1.json`.
- No duplicar cientos de transformaciones en React ni emitir eventos por frame. Añadir `load.progress` si aporta valor y con throttling.
- Actualizar temporal `apps/probe-web` solo para diagnosticar: backend, región, LOD, calidad, contador descargas, cache HIT/MISS, escena generation y uso estimado GPU/CPU; controles para simular red caída/reintento/cambio rápido.
- No hacer UI premium, responsive final ni PWA.
- Documentar API TypeScript y manejo de excepciones; si cambia contrato, ADR y tests de compatibilidad obligatorios.

## 8. GATE G-M04 / PRUEBAS BLOQUEANTES

Las pruebas deben realizarse en WebGPU y WebGL2 cuando haya soporte real. Mínimo:
1. `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace`.
2. Dos bundles WASM compilados y probados, shaders y M03 core glTF intactos.
3. `manifest` válido, catálogo SHA correcto, package SHA correcto, rechazo de URLs maliciosas, SHA falsificado, encoding meshopt sin decoder, manifest mezclado de versiones.
4. Cache cold y warm: fetch real de primera carga, segunda carga sin fetch, recarga offline desde cache, corrupción detectada/borrada, cuota/sin CacheStorage no bloquea.
5. Cancelación real: load A y luego B, B debe ganar; respuestas tardías no mutan scene; dispose durante fetch; error durante upload preserva escena anterior.
6. Alternar LOD0↔LOD1 20 veces: IDs 26/26, selección e isolate persistentes y GPU/memoria no crecen monotónicamente; medir picos.
7. Red inestable: HTTP 404/500, respuesta truncada, timeout, cache miss offline, reintento bajo política, sin loops.
8. GPU: reconfigure surface y recuperación simulada de device; fallback WebGPU→WebGL2 con evidencia de backend real. Si la pérdida física no se pudo provocar, `NOT_RUN` físico.
9. Render-on-demand: sin frames constantes con escena inactiva.
10. CPU RAM y VRAM asignada estimadas contra presupuesto provisional en escenario low con escena representativa; sin garantía 30/60 FPS si no hay hardware y muestras.
11. Browser E2E con Playwright: verificar que se muestra el asset correcto por URL/hash y que `region.ready` llega después de render; no basta contar filas.
12. Repetir QA de M03: `tools/audit_lod_silhouettes.py`, hash check, 26 IDs, p95/p99 o máximo real de contorno; nunca copiar cifra histórica de 0.01px.
13. Validar archivo original fuente Git sin cambios.
14. Simular manifiesto experimental 3 paquetes (meshopt incluido) y 2 paquetes sin meshopt; ambos deben elegir GLB core correctamente.

G-M04 PASS exige: 0 regresiones, fallback real, eventos y generaciones correctos, cache/integridad verificadas, eviction sin fuga creciente, LOD atómico, error tipado y logs. Si pruebas físicas iOS/Android faltan, marcar alcance Desktop Browser PASS y mobile PENDING, nunca afirmar cobertura móvil completa.

## 9. PERF, TEST HARNESS Y EVIDENCIA

Medir como mínimo:
- manifest fetch, download, digest verify, decode GLB, upload GPU, primer frame, tiempo reuso cache, número de requests, bytes transferidos, bytes CPU decoded, bytes GPU estimados, cache usage/evictions.
- p50/p95 frame time durante ≥120 frames de interacción REAL bajo escena y perfil indicados, sin medir FPS de render-on-demand como benchmark.
- 2 backends; cold/warm/offline; calidad low y high cuando sea viable. Guardar datos y hardware/browser.
- Screenshots/JSON automáticos realmente generados, sin reproducir asset protegido en GitHub público.
- Matriz PASS/FAIL/NOT_RUN/BLOCKED por plataforma.
- Crear pruebas adversariales que fallen si alguien rompe request generations, SHA or atomic swap; no tests pasivos que `return` y pasen sin comprobación.

Evidencia:
`docs/IMPLEMENTATION_03_RESULT.md` (M04 resultados; no confundir con M03),
`docs/BUILD_RUNTIME.md`,
`reports/implementation/M04/` (logs/JSON; binarios/screenshots locales bajo directorios ignorados),
`reports/implementation/implementation-03-status.json`.
Actualizar `README.md` y documentar cambios de API. Guardar comandos exactos y salida de test.

## 10. GitHub: POLÍTICA DEL REPOSITORIO YA EXISTENTE

El repo GitHub `anuaralejandro/anatom.ia` ya existe y es público; NO lo recrees ni cambies a otro remoto. Main remoto puede no incluir últimas correcciones locales de auditoría M03. Ejecuta `git status`, `git log`, `git diff`, identifica cambios preexistentes, y preserva todos.

Si usas branch local `feature/m04-runtime-streaming`, créala SIN eliminar cambios locales y documenta su punto de partida. No hagas `git reset --hard`, `git clean -fd`, force-push ni rebase destructivo.

No subir modelos Z-Anatomy, GLB/BLEND, capturas de anatomía ni archivos gigantes; respetar `.gitignore`, revisar `git ls-files` y hacer escaneo de secretos/artefactos antes de preparar commit. No realizar push ni abrir PR sin una autorización expresa posterior. Se podrá preparar el changeset revisable localmente.

## 11. PLAN DE EJECUCIÓN

1. Auditar estado y tests existentes. Catalogar riesgos precisos del código real.
2. Crear módulos mínimos `manifest`, `asset manager`, `cache transport` y `memory` sin duplicaciones.
3. Integrar Rust↔WASM, cache e integridad.
4. Integrar generación y cancelación de solicitudes.
5. Atomic LOD swap/selección y memory tracking.
6. Recuperación surface/device y fallback browser.
7. Probe temporal + test harness integrado.
8. Negativas, web dual backend, memoria/cache/offline, no regresión de M00–M03.
9. Corregir defects y documentar gate; NO implementar M05/M06 ni publicar nada.

**PROHIBIDO:** falsificar PASS, inventar capturas, declarar GPU-lost recuperado sin prueba, borrar auditoría, diseñar un backend que no hace falta, activar meshopt en runtime sin decoder, o tratar los assets como licencias comerciales ya aprobadas.

**ENTREGA ESPERADA:** M04 real, comprobable y conservador: stream/caché segura de assets, cambio LOD sin perder identidad, memoria acotada y recuperación/fallback. Todo lo demás queda fuera de alcance.
