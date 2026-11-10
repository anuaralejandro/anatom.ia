# ANATOM.IA — PROMPT 04 PARA ANTIGRAVITY
## M04-H: CIERRE ARQUITECTÓNICO / HARDENING DEL RUNTIME (ANTES DE M05)

**Rol operativo:** Principal Engineer de Rust, wgpu 30.0.1, WebAssembly, WebGPU/WebGL2, confiabilidad gráfica, memoria, concurrencia y pruebas adversariales de navegador.

**Directorio autorizado:** C:\Users\datam\Documents\anatom.ia
**Repositorio existente (PÚBLICO):** https://github.com/anuaralejandro/anatom.ia
**Rama observada:** feature/m04-runtime-streaming
**Commit base observado:** be654ca21a6f26f54dc66b2115ff7aa2b3d18c2a
**Objetivo:** CORREGIR M04 REALMENTE, con pruebas y evidencias; NO diseñar ni construir el frontend React de M05.

### MANDATO PRINCIPAL
El motor ya FUNCIONA para la pelvis masculina (26 AnatomyIds TA2, LOD0 38,605 triángulos, LOD1 33,758). No lo sustituyas ni lo reescribas. El objetivo es convertir las rutas funcionales existentes en un runtime robusto ante fallos de GPU, OOM, pérdida de contexto, races de carga y desconexión, manteniendo un solo núcleo de escena Rust. No basta escribir clases o tests que ejercitan únicamente el camino feliz: demostrar cada invariante con fallos inyectados y navegadores reales.

## 0. PRE-FLIGHT: REGLAS NO NEGOCIABLES

Antes de editar, LEE COMPLETOS:
- README.md; docs/AUDITORIA_IMPLEMENTACION_01.md; docs/AUDITORIA_IMPLEMENTACION_02.md; docs/AUDITORIA_IMPLEMENTACION_03.md
- reports/audit/m04-independent-verdict.json; reports/audit/m04-pre-fix-adversarial.json; reports/audit/m04-catalog-tamper.json; reports/audit/m04-after-fix-suite.json
- docs/PROMPT_03_ANTIGRAVITY_M04.md; docs/IMPLEMENTATION_03_RESULT.md (histórico, NO es aceptación final)
- contracts/engine-bridge-v1.json; contracts/quality-profiles-v1.json; contracts/render-profile-v1.json; contracts/implementation-milestones-v1.json
- crates/atlas-core/src/renderer.rs, memory.rs, scene.rs, manifest.rs, types.rs, glb.rs
- crates/atlas-web/src/lib.rs (TODO el archivo, no fragmentos)
- apps/probe-web/app.js y index.html; tools/serve_probe.py; tools/test_m04_streaming.py; herramientas audit_m04_*.py
- docs/ADR_004_CACHE_STORAGE.md; scripts npm/Cargo para ambos backends.

Estado LOCAL observado antes de este prompt: la rama feature/m04-runtime-streaming contiene cambios SIN COMMIT procedentes de la auditoría independiente. En especial, NO destruir:
- crates/atlas-core/src/manifest.rs: validate_load_plan canónico.
- crates/atlas-core/tests/manifest_test.rs: rechazo de variante/hash/ruta falsificados.
- crates/atlas-web/src/lib.rs: generaciones reparadas para loadGlbBytes y loadSyntheticCube y validación de plan.
- apps/probe-web/app.js: verificación SHA del catálogo, fail-closed, limpieza de ResizeObserver y abort en cambio de backend.
- docs/AUDITORIA_IMPLEMENTACION_03.md y reports/audit/m04-independent-verdict.json.

Ejecuta PRIMERO:
1) git status --short --branch, git diff --stat, git diff --check, git log -3 --oneline; clasifica modificaciones PREEXISTENTES.
2) cargo fmt --all -- --check
3) cargo clippy --workspace --all-targets -- -D warnings
4) cargo test --workspace (baseline local auditado: **36 tests**, no 35, salvo que el árbol haya cambiado)
5) cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder
6) python tools/test_m04_streaming.py
7) git -C sources/z-anatomy-upstream status --porcelain

Si una prueba se bloquea, informa BLOCKED con motivo verificable; jamás inventes PASS. No realizar 'git reset --hard', 'git clean -fd', stash destructivo, cambios de remoto, force-push ni checkout que pierda ediciones. NO cometer ni subir cambios automáticamente; dejar diff local revisable. No modificar geometría, .blend, .glb, crosswalk TA2, catálogo anatómico de fuente, licencias o screenshots publicables. No instalar un nuevo motor gráfico, ECS, Three.js, Babylon ni backend de servidor. No M05 React, no M06 cloud deploy.

## 1. DIAGNÓSTICO CONCRETO QUE DEBES CORREGIR

A. En 'crates/atlas-core/src/renderer.rs', 'Renderer::upload_scene(&mut self, scene: &Scene)' comienza con 'self.destroy_gpu_resources()' y devuelve '()'. En consecuencia, no se puede garantizar rollback ante fallos de construcción, asignación, validación o memoria. 'create_synthetic_cube_scene' también llama este método: actualizar todos sus call sites sin regresión.

B. 'MemoryTracker::is_within_budget()' y 'record_eviction()' existen, pero no se usan para controlar realmente reservas o expulsiones; 'concurrent_fetches' es una propiedad informativa, no un limitador. El indicador 'resident_gpu_bytes' incluye estimaciones del canvas/depth y NO equivale a VRAM medida. Los perfiles reales son low 64/48 MiB, medium 128/96, high 256/160 (GPU/CPU), no las cifras erróneas del resumen de Antigravity.

C. 'atlas-web::applyPackageBytes' parsea GLB, transfiere estado, sube a GPU y emite 'region.ready' antes de que 'renderFrame()' haya presentado un frame. Además, el render retorna false ante error pero puede poner 'needs_render = false', dejando la UI falsamente lista o parada.

D. 'simulateDeviceLoss()' sólo destruye buffers, y el botón JS recrea la instancia/canvas; no existe demostración de detección real de DeviceLost ni de política integral de reintentos y fallback. Separar 'simulated', 'controlled loss' y 'physical/driver loss' en resultados.

E. En 'apps/probe-web/app.js', el transport hace fetch/CacheStorage/SHA y AbortController; carece de scheduler de concurrencia efectivo, backoff/timeout general y pruebas rigurosas de respuestas retrasadas. Ya hay comprobaciones de canonicidad del manifest/plan: NO ELIMINARLAS.

F. CacheStorage permite volver a cargar geometría sin red dentro de una página activa, pero una recarga REAL de HTML+JS+WASM offline falla (net::ERR_INTERNET_DISCONNECTED). Se necesita un shell mínimo offline para cerrar esta limitación en el probe, SIN construir la PWA premium de M05.

## 2. M04-H1 — SWAP DE GPU TRANSACCIONAL / DOS FASES (P0)

Refactor de mínimo alcance, sin cambiar el contrato anatómico:
- Introducir concepto equivalente a 'GpuSceneResources' (mallas GPU, nodos GPU, materiales GPU, asignaciones y bytes asociados) separado de la infraestructura estable del Renderer (Device, Queue, Pipeline, Camera Uniform, Surface, Depth).
- 'prepare_scene(scene, budget, ...)' prepara una escena candidata y devuelve Result<PreparedScene, EngineError>, con validación de índices/formatos/limites, presupuesto preflight y errores GPU capturados. NO modificar el 'active_scene_gpu' ni destruir recursos activos durante preparación.
- Usar la API REAL de wgpu 30.0.1: Device::push_error_scope(ErrorFilter::Validation y OutOfMemory según corresponda), ErrorScopeGuard::pop().await y/o on_uncaptured_error apropiadamente. Verificar firmas/semántica para wasm32, WebGPU y WebGL2; no asumir que create_buffer_init devuelve Result. Error scope y unwind deben dejar intacta la escena anterior. No usar catch_unwind como mecanismo principal de OOM en WASM.
- Definir 'commit' al límite seguro de frame, conservando escena Rust y GPU emparejadas. Evitar estados mixtos (escena nueva con buffers anteriores). Solo marcar nueva escena activa cuando geometría + recursos + validación hayan sido aceptados. Conservar un recurso anterior para rollback hasta que el render/submit del primer frame de la nueva escena resulte exitoso; diferenciar 'present/submit aceptado' de confirmación física del monitor.
- Si el primer render/submit del candidato falla y el Device sigue útil, volver a la escena, cámara, selección, visibilidad y buffers previos. Si el Device se perdió, entrar al flujo DeviceLost (no prometer rollback sobre un device muerto).
- Liberación de buffers antiguos segura con respect to in-flight GPU work: usar garantías de wgpu y/o queue completion; evitar Buffer::destroy prematuro, uso de handles después del destroy, doble liberación y retención indefinida. 'dispose()' idempotente.
- Error handling: MEMORY_LIMIT, ASSET_CORRUPT, GPU_DEVICE_LOST, GPU_UNAVAILABLE, validación GPU. Prohibido 'unwrap()' sobre datos/estado no confiables.
- Incluir un FAILPOINT controlado SOLO para tests: inyectar fallo de reserva antes de subir, en la mitad de la preparación y previo al commit. Comprobar por test que la escena previa se sigue renderizando: IDs, matriz de cámara, selectedId, aislamiento, LOD, sceneRevision y backend intactos. El failpoint no debe ser manipulable por usuarios finales fuera de builds de diagnóstico/test.
- Conservar compatibilidad de 'loadGlbBytes', 'loadSyntheticCube', 'applyPackageBytes' y picking. No duplicar escena en JavaScript.

**Gate H1:** 0 rotura de escena ante fallos inyectados; cambio LOD0 <-> LOD1 sigue mostrando 26 IDs, sin handles destruidos; ambos backends PASS.

## 3. M04-H2 — MEMORIA REALMENTE CONTROLADA, SIN INFLAR COMPLEJIDAD (P0)

No inventar un ECS ni una LRU global de cientos de regiones cuando solo existen pelvis+dos LOD:
- Separar claramente 'gpu_buffer_allocated_estimate', 'gpu_depth_render_target_estimate', 'cpu_scene_decoded_estimate', 'cpu_staging_bytes', 'verified_blob_bytes', 'cache_storage_estimate', 'peak_overlap_bytes', y 'memory_budget_bytes'. Las estadísticas deben llamarse ESTIMACIONES; jamás etiquetar como VRAM física.
- Preflight conservador: calcular tamaño de candidato y pico del swap (activo+pendiente+buffers temporales+depth, según vida útil real); verificar presupuestos del perfil antes de asignar recursos. Si no cabe, preferir LOD1 cuando esté disponible y cumpla seguridad; de otro modo rechazar con MEMORY_LIMIT recuperable y conservar escena visible.
- Adaptar al límite disponible del GPU adapter (máximo buffer/texture dimension/alignment) y limitar DPR/resolución efectiva. Mantener perfiles contractuales: low 64 MiB GPU + 48 CPU, medium 128 + 96, high 256 +160. No garantizar esas capacidades en hardware real: son metas provisionales sujetas al adapter.
- Implementar contabilidad de ciclo de vida: reserved/pending/active/retiring; actualizar bytes tras swap, rollback, resize, dispose y device loss. El contador de evictions sólo sube cuando se expulsó ALGO REAL; no simularlo con una llamada vacía.
- Con una sola región visible, una política 'single-resident-scene + bounded verified blob cache' puede ser más correcta que LRU de GPU; documentar decisión explícita. Si se implementa LRU, debe tener consumidores reales, política de protección selected/visible y pruebas de eviction sin estado zombie.
- CacheStorage tiene límites diferentes de GPU/CPU: implementar capacidad objetivo best-effort y manejo de cuota, con presión de almacenamiento controlada; no crear doble cache gigante en RAM. Probar cache deshabilitado, quota exceeded, corrupt cache.
- 'setQualityProfile' no puede limitarse a cambiar un badge: debe comprobar presupuesto al cambiar a Low y ejecutar una transición segura al LOD1 o devolver estado typed que indique que el cambio se difiere/rechaza.
- No hacer promesas de memory-leak-free por ver solamente 3.27→3.21 MB estimados. Ejecutar estrés 20, 100 y si hardware tolera 300 swaps; comparar objetos/contadores reales y registrar alcance de cada métrica.

**Gate H2:** no sobrepasar intencionalmente un presupuesto sin 'MEMORY_LIMIT' o downgrade seguro; test forzado con presupuesto bajo falla ANTES del swap conservando escena; contador GPU activo vuelve al baseline tras dispose/reloads.

## 4. M04-H3 — EVENTOS Y CICLO DE VIDA CORRECTOS (P1)

- Establecer contrato explícito de estados (Queued, Fetching, Verifying, Decoding, PreparingGpu, CommitPending, FirstFramePending, Ready, Failed, Cancelled, Recovering).
- 'region.loading' cuando comienza solicitud válida; 'region.ready' sólo después de que el primer frame del candidato haya sido enviado y presentado con éxito según la semántica real del backend. No afirmar que el monitor físico ya lo mostró.
- 'region.ready' debe incluir 'requestId', 'sceneGeneration', 'sceneRevision', 'region', 'variant', 'lod' y backend efectivo, con nombres estables. 'region.failed'/'engine.error' con código, recoverable, requestId y generación. No exponer arrays de vértices ni miles de estructuras en los eventos.
- En fallos no ocultar, vaciar o destruir escena anterior; el usuario debe seguir interactuando con la escena previamente válida. UI diagnóstica no debe marcar documento global 'error' si el error fue una petición secundaria recuperable mientras hay una escena lista.
- En 'renderFrame()', sólo limpiar 'needs_render' si render+submit/present resultaron exitosos. Errores SurfaceLost/Outdated/Occluded/Timeout/OutOfMemory deben conducir a acciones distintas: reconfiguración, pausa, retry acotado, degradación o recovery.
- Asegurar que 'currentGeneration' externo y 'memory_tracker.currentGeneration' permanezcan sincronizados incluso en rutas heredadas y 'dispose'; no tocar la escena nueva si una petición antigua completa tarde.
- Los métodos que actualizan GPU deben respetar single ownership/RefCell y no provocar reentrancia de callback durante un mutable borrow. Si es preciso, emitir eventos DESPUÉS de soltar RefCell borrow o canalizar eventos en cola; documentar y probar.
- El resultado de 'applyPackageBytes' no debe crear doble evento 'ready' por reintento o recovery.
- Exportar definiciones TypeScript precisas a partir del bridge WASM real, sin inventar shape camelCase si serde_wasm_bindgen produce snake_case.

**Gate H3:** tests de orden de eventos: loading -> commit -> primer frame válido -> ready; fallo -> failed sin ready; cancel -> cancelled sin ready; sin duplicados.

## 5. M04-H4 — PÉRDIDA GPU REAL Y FALLBACK AUTOMÁTICO (P1)

- Investigar APIs exactas de wgpu 30.0.1 y WebGPU: 'Device::set_device_lost_callback' (revisar semántica, restricciones Send y wasm), 'Device::push_error_scope', 'Device::on_uncaptured_error'. No implementar nombres de API inventados. En callbacks no capturar 'Rc<RefCell<...>>' que viole Send; adoptar flag atomizado/event queue apropiada y notificar al host sin reentrancia.
- La detección de DeviceLost debe funcionar fuera del bucle rAF de interacción; la escena puede estar quieta al perder GPU. No crear un render loop perpetuo para detectar el fallo: usar notificación/evento/observador ligero que no consuma GPU.
- 'DeviceLostReason::Destroyed' intencional debe distinguirse de 'Unknown'. Probar pérdida inducida/controlada en WebGPU y documentar que no equivale a un fallo físico del driver.
- Registrar una RecoveryStateMachine: Healthy -> SuspectedLoss -> Recovering -> Recovered | SwitchingBackend | TerminalFailed, con attempt limit, backoff y tokens para invalidar jobs obsoletos.
- WebGPU: reconstruir Device/Queue/Pipeline/Surface/Depth y GPU resources en un contexto/canvas nuevo si lo requiere navegador; restaurar bytes verificados desde cache/scene CPU, cámara, selectedId y visibility. Mantener fallback a WebGL2 si WebGPU falla en recovery; demostrar backend real por capabilities y pixels renderizados.
- WebGL2: manejar 'webglcontextlost' y 'webglcontextrestored' según contrato del navegador/wnative, sin impedir default en context loss erróneamente o hacer loops. Verificar que sólo un Canvas/WebGL context controlan el viewport y que observers/listeners viejos se eliminan.
- No confundir SurfaceLost/Outdated con DeviceLost real. Evitar declarar 'device.recovered' antes de recuperar recursos Y renderizar primer frame.
- Tras N intentos fallidos, emitir error terminal claro, conservar posibilidad de reintento manual sin loop infinito. No contaminar sesiones siguientes; dispose idempotente.
- Pruebas: (a) simulación existente, (b) Device.destroy() CONTROLLED_PASS si hay API accesible, (c) callback real disparado y captura de evento, (d) forzar fallo WebGPU y comprobar fallback WebGL2, (e) fallo de ambos, (f) ContextLost WebGL2 si la extensión aplicable lo permite. PHYSICAL_DRIVER_LOSS puede quedar NOT_RUN sin bloquear entrega local, pero NO puede etiquetarse PASS.

## 6. M04-H5 — TRANSPORTE: CONCURRENCIA, ABORT, RETRIES Y CACHÉ (P1)

- Extraer AssetStreamManager del inmenso 'apps/probe-web/app.js' a módulo autocontenido JS/TS compatible con probe; definir una interfaz portable para que M05 React pueda reutilizar sin copiar lógica.
- Conserva la autoridad de Rust para planes canónicos y SHA/size. El transport no debe permitir variantes falsas ni descargar URLs de manifes/paquetes alterados.
- Implementar scheduler con cupos reales según QualityProfile (Low=2, Medium=3, High=4). Los trabajos en cola deben poder cancelarse antes del fetch. Coalescing de requests concurrentes idénticos por versión+hash, con subscribers y abort correcto: cancelar un consumidor no debe abortar otros.
- Timeout explícito y reintentos ACOTADOS, con jitter/backoff para errores transitorios 408/429/5xx y network timeout; no reintentar 404, URLs maliciosas, fallos de digest permanentes, meshopt unsupported o MEMORY_LIMIT. Capturar Response.body truncado y tamaño antes de parsear. Asegurar que AbortController cancela fetch y timers.
- Todas las continuaciones async deben verificar token activo, instance ID del engine, AbortSignal y estado 'disposed' ANTES de tocar UI/CacheStorage o GPU; una petición superada no puede ocultar overlay ni mostrar error encima de la ganadora.
- Preserve atomic scene on errors; no setear 'state.currentLod' como definitivo al inicio. Poner 'desiredLod' en pending y 'currentLod' tras commit/ready. La lista de visibilidad se actualiza tras sceneRevision.
- Mantener integridad en cache HIT/MISS por hash Y tamaño. Probar bloqueo al cambiar catalog SHA y manifest version. CacheStorage puede fallar por política/quota; navegación online continúa sin falso ready.
- Medir requests reales con Playwright interception; NO aprobar una carrera A->B->A sólo porque el último número de triángulos sea 38,605: exigir que p1/p2 estén abortadas o explícitamente superseded, y que gen+request ID de p3 coincidan con frame presentado.

## 7. M04-H6 — ARRANQUE OFFLINE REAL SIN CONSTRUIR M05

El test real anterior 'page.reload()' con browser context offline falló 'ERR_INTERNET_DISCONNECTED'; la simulación 'simulatedOffline' NO representa arranque offline.

Implementar una solución mínima y LOCAL de app-shell offline para 'apps/probe-web', sin convertirlo en una aplicación React/PWA definitiva:
- Un service worker restringido al scope del probe puede precachear HTML, JS, CSS, ambos bundles WASM, manifest y catálogo versionados, manejando updates con activación coherente de release. Reutilizar los GLB verificados que ya guarda AssetStreamManager en CacheStorage; no duplicar megabytes por defecto sin justificación.
- La navegación offline sólo se considera disponible DESPUÉS de una visita online que haya instalado/activado el worker y precacheado los recursos del shell. Sin visita previa, error de navegador es esperado y NO se presenta como PASS.
- No interceptar otros orígenes, no publicar assets, no cachear contenido no autorizado remotamente, ni crear app manifest, instalación móvil, dashboard u otras funciones M05.
- Mantener integridad/versión del manifest/catalog, no crear una mezcla inadvertida entre shell vA y geometry vB. Si no hay una versión consistente local, fallar con mensaje recuperable y sin anatomía falsa.
- Prueba real con Playwright: visita online, esperar navigator.serviceWorker.ready y control efectivo, carga GLB en caché, browserContext.setOffline(true), page.reload, visor vuelve a cargar pelvis sin requests reales, WebGPU y WebGL2 donde estén disponibles. Probar fallo de cache miss offline y recuperación de red.

Si aparece un bloqueo técnico no resoluble dentro de un shell mínimo, reportar OFFLINE_BOOT=BLOCKED con evidencia y mantenerlo pendiente; no declarar M04 completado por simulación.

## 8. GATES DE ACEPTACIÓN: REPRODUCIBLES, ADVERSARIALES, SIN PASS FICTICIOS

A) Base Rust: fmt, clippy con -D warnings, tests workspace (>=36 sin tests eliminados), wasm check.
B) Build: 'npm run build' ambos bundles; no reutilizar wasm viejo durante E2E.
C) M03: builder validate, 26 AnatomyIds, hashes LOD0/LOD1 intactos; QA geométrica preexistente sin falsas métricas.
D) GPU swap: 20/100 cambios; test de fallo antes de allocation, fallo parcial y fallo de primer render; escena previa conservada salvo pérdida real del device.
E) Memory: forzar presupuesto por debajo del peak y comprobar MEMORY_LIMIT antes de destruir recurso activo; medir high-watermark activo+pending; no afirmar VRAM física.
F) Events: orden exacto region.loading, region.ready sólo después de primer frame presentado; cancel/fail no emite ready; requestId/generation precisos; cero eventos después de dispose.
G) Lifecycle: reinicializar backend 30 veces, no acumulación de ResizeObserver, pointer/wheel/touch handlers; backends reales en screenshots/test asserts; DOM sin escenas viejas.
H) Recovery: dispositivos controlados/simulados y fallback; 'PHYSICAL_DRIVER_LOSS=NOT_RUN' si no hay evidencia física. Sin bucle de reconexión infinito.
I) Transport: cache hit/cold/corrupt; network 404, 408, 429, 500, 503, timeout, truncated body, hash mismatch, cache quota, false manifest; abort during queued/fetch/verify/prepare; "last wins".
J) Offline: boot real con navegador sin red DESPUÉS de precache correcto y sin fake simulatedOffline; test en ambas variantes; sin online-first inicial => comportamiento explicitado.
K) Performance: p50/p95 CPU render frame para >=120 frames durante interacción REAL, con backend/hardware/resolución/version registrados; no utilizar FPS de render-on-demand en reposo para inferir rendimiento.
L) No fuga: 100 switches no incremento monotónico INEXPLICABLE en recursos contabilizados; puede haber caching intencional documentado. Si no se dispone de medición driver VRAM, declarar 'GPU_ALLOCATION_ESTIMATE_ONLY' y 'PHYSICAL_VRAM_NOT_MEASURED'.
M) Seguridad/legal: ningún cambio en sources/z-anatomy-upstream, no publicar GLB o screenshot de assets en repo público, no modificar assets/licencia; cero push.
N) Test harness adversarial obligatorio: nuevos tests deberían FALLAR contra código anterior (por invariantes reales), pasar tras patch. No usar 'return' silencioso si falta artefacto o navegador; registrar SKIPPED/BLOCKED con causa.

## 9. FORMATO DE ENTREGA OBLIGATORIO

Crear sin eliminar el historial:
- docs/M04_HARDENING_RESULT.md (antes/después, arquitectura elegida, decisiones y riesgos)
- docs/ADR_005_GPU_SWAP_AND_RECOVERY.md (propiedad de GPU resources, staging/commit/retire, error scopes, lifecycle y límites)
- docs/ADR_006_MEMORY_AND_SCHEDULER.md (perfiles, contabilidad, política residente y concurrencia)
- docs/M04_RUNTIME_BRIDGE_CONTRACT.md (API real WASM↔JS y cambios compatibles con M05; estados y semántica ready)
- reports/implementation/M04H/m04h-results.json (cada gate con PASS/FAIL/SIMULATED_PASS/NOT_RUN/BLOCKED, no booleano ambiguo)
- reports/implementation/M04H/test-matrix.json (backend, hardware, browser, pruebas, número de frames, métricas)
- scripts de pruebas reproducibles: tools/test_m04h_*.py y tests Rust en crates adecuados.

Actualizar README.md y reports/implementation/implementation-03-status.json con 'audit_override' y referencia al cierre M04H; nunca sobrescribir auditoría independiente original. No inventar capturas; conservar imágenes protegidas fuera de Git público. Registrar archivos modificados, parámetros de tests y SHA-256 de GLB. Adjuntar lista de limitaciones físicamente no verificadas. Si hay fallos, NO atribuir éxito a reportes previos.

### RESULTADO FINAL ESPERADO
- **PASS_TECHNICAL_LOCAL_M04H** sólo cuando todos los gates funcionales medibles en el dispositivo disponible están sustentados, salvo pruebas físicas móviles/driver explícitamente NOT_RUN y licencia comercial BLOCKED.
- **PARTIAL_PASS** si falla memoria, rollback, events, recovery o offline boot.
- **FAIL** ante regresión de M00-M03, identidad anatómica alterada, versiones mezcladas, bypass de SHA o reporte manipulado.

Al terminar informa en español un cuadro breve: 'Implementado / Verificado / Parcial / No probado', diferencias con la auditoría previa, test count, comandos ejecutados, reportes y árbol Git. **NO crear todavía M05, NO hacer push, NO declarar listo para producción**.

**EJECUTA LAS REPARACIONES REALMENTE. NO ENTREGUES SÓLO UN PLAN.**
