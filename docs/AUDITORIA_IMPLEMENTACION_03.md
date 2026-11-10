# anatom.ia — Auditoría independiente de implementación 03 (M04)

Fecha local: 2026-11-09. Rama: feature/m04-runtime-streaming. Commit base: be654ca21a6f26f54dc66b2115ff7aa2b3d18c2a.
Veredicto: PARTIAL_PASS_CORRECTED — desarrollo local del visor de pelvis operativo; M04 enterprise-grade NO cerrado.
Esta auditoría prevalece sobre el reporte histórico docs/IMPLEMENTATION_03_RESULT.md; no hubo commit ni push de correcciones.

## Verificaciones reproducidas
- cargo fmt --all -- --check: PASS.
- cargo clippy --workspace --all-targets -- -D warnings: PASS.
- cargo test --workspace: 35/35 PASS original; 36/36 PASS después de una prueba adversarial nueva.
- cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder: PASS.
- npm run build: los dos bundles WASM (WebGPU y WebGL2) reconstruidos satisfactoriamente.
- cargo run -p atlas-builder -- validate build/atlas/release: PASS (27 verificaciones).
- python tools/test_m04_streaming.py: 9 casos completados; 8 pruebas funcionales y 1 recuperación GPU SIMULADA, no física.
- Pruebas de navegador adicionales: informes reports/audit/m04-pre-fix-adversarial.json y reports/audit/m04-catalog-tamper.json.
- Z-Anatomy upstream: git status sin modificaciones; no deploy ni push.

## Defectos demostrados y reparados
1. Se aceptaba un RegionLoadPlan falsificado: un actor JS podía marcar la pelvis masculina como female-adult sin manifest válido. Se añadió validación canónica en Rust (ManifestSnapshot.validate_load_plan) y comprobación dentro de applyPackageBytes. La prueba de navegador pasó de ACCEPTED a REJECTED; las pruebas unitarias cubren hash, ruta y variante modificados.
2. loadGlbBytes y loadSyntheticCube incrementaban el token externo pero no el MemoryTracker por préstamo mutuo RefCell. Los dos contadores están ahora sincronizados; comprobado en el navegador real.
3. El probe M04 confiaba en el manifest pero no verificaba el catálogo referenciado. Ahora carga catalog.json, verifica longitud y SHA-256 contra manifest, comprueba IDs únicos y usa sus etiquetas como fuente autorizada de UI. Un catálogo manipulado bloqueó la carga en WebGPU y WebGL2, sin solicitar GLB.
4. Si fallaba la verificación inicial, el probe podía caer a carga directa no verificada; ahora falla cerrado para la anatomía. El nombre de CacheStorage y la clave de activo dependen de atlasVersion, no únicamente de una constante fija.
5. Al cambiar backend se abortan fetch anteriores y se desconecta el ResizeObserver previo; se captura la instancia del engine en el plan de carga y no se aplican cargas tardías sobre otra instancia.

## Hallazgos abiertos — BLOQUEANTES para declarar M04 finalizado
- MEMORY_BUDGET_ENFORCEMENT: MemoryTracker mide y publica presupuesto (64/128/256 MiB GPU y 48/96/160 MiB CPU) pero los métodos is_within_budget y record_eviction no se llaman desde el runtime. No hay política real de LRU, preflight de asignación ni degradación por presión de memoria. El reporte inicial que menciona Low=32, Medium=64, High=128 MB no corresponde a los valores del código.
- ATOMIC_GPU_SWAP: Renderer.upload_scene destruye los buffers GPU antiguos ANTES de subir los nuevos; un error de upload/OOM podría dejar la escena sin recursos. Las pruebas certifican transferencia de selección/visibilidad, no una transacción GPU con rollback.
- DEVICE_LOSS_REAL: la recuperación probada llama simulateDeviceLoss, destruye recursos y crea una nueva instancia/canvas desde JS. NO prueba DeviceLost real, pérdida de adapter, reconstrucción automática por evento ni fallos en reconfiguración de superficie.
- OFFLINE_BOOT: al desconectar físicamente la red y recargar la página, Chrome falló con ERR_INTERNET_DISCONNECTED, porque HTML, WASM, manifest y catálogo no se sirven offline sin service worker/app shell precacheado. Sí funcionan GLB cacheados desde una página ya abierta (simulación offline). El soporte PWA integral pertenece a M05 y requiere pruebas reales.
- EVENT_SEMANTICS: applyPackageBytes emite region.ready tras upload, ANTES del primer frame presentado; no cumple estrictamente el contrato de ready después de demostrar render y requiere revisar el bridge antes de conectar React definitivo.
- RETRIES/INFLIGHT_LIMITS: no se observó implementación de backoff ni límite efectivo de concurrent_fetches definido en QualityProfile. La prueba A-B-A ejerce una carrera sencilla, no retrasos arbitrarios HTTP/500, timeout de upload ni fallo en dos pestañas.
- MEMORY_LEAK_EVIDENCE: la prueba 20x observa bytes estimados de geometría y framebuffer calculados por el motor; NO es una medición independiente de VRAM ni acredita ausencia de leaks bajo estrés prolongado.
- MOBILE/CLINICAL/LEGAL: pruebas físicas Android/Safari, fidelidad científica y licencias individuales siguen NOT_RUN/BLOCKED.

## Matriz de aceptación auditada
| Componente | Veredicto |
|---|---|
| Manifest + GLB SHA / catálogo SHA | PASS_CORRECTED |
| CacheStorage cold/warm/corrupción | PASS para sesión web activa |
| Cancelación generacional y switch backend | PASS básico corregido; estrés avanzado PENDING |
| LOD0/LOD1 WebGPU y WebGL2 | PASS local |
| Integridad TA2 26/26 | PASS técnica |
| Render-on-demand | PASS básico |
| Límites CPU/GPU / LRU reales | NOT_IMPLEMENTED |
| Swap transaccional GPU ante error | NOT_IMPLEMENTED |
| DeviceLost real / fallback automático por evento | NOT_RUN / INCOMPLETE |
| Offline reload con shell web | FAIL, planificar en M05/PWA |
| Publicación comercial | BLOCKED |

## Decisión
El prototipo M04 puede utilizarse localmente y sirve de referencia para PLANEAR el diseño visual M05 en una conversación posterior. NO autorizar todavía el acoplamiento definitivo React/WASM ni la publicación: primero se necesita un cierre acotado de M04 para presupuestos/memoria, semántica ready, swap y recuperación; el offline full boot se puede implementar e integrar junto con M05 PWA.
No generar aún prompt de M05 ni modificar el frontend final en esta auditoría. Conservar cambios locales y revisar antes de cualquier push al repositorio público.
