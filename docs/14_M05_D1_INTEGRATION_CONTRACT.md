# anatom.ia — M05 D1: Contrato de integración y componentes v1.0

**Estado:** D0 visual aprobado por el propietario. D1 especificado. M05-A es la primera corrida de implementación, condicionada a la reparación y test de F01–F03 de M04-H. No hay React existente todavía en el repositorio.
**Rama local observada:** feature/m04-runtime-streaming, HEAD be654ca; modificaciones previas extensas sin commit. NO reset, clean, stash destructivo, checkout que sobrescriba archivos, push, merge ni publicación.
**Referencias normativas:** docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md; docs/13_M05_WIREFRAME_REVIEW.md; docs/m05-wireframes/index.html y gallery.html; docs/M04_RUNTIME_BRIDGE_CONTRACT.md; crates/atlas-web/src/lib.rs; crates/atlas-core/src/types.rs; apps/probe-web/asset-stream-manager.js; docs/AUDITORIA_IMPLEMENTACION_04H.md.

## 1. Decisión de ejecución

M05 se divide en tres corridas auditables y NO se implementa monolíticamente:
- **M05-A — Bases + gate M04-H.1:** reparar F01/F02/F03, establecer contratos TypeScript, crear nuevo shell React + sistema visual aprobado, responsive accesible, pruebas de UI y fixture seguro. No integrar todavía toda la anatomía real.
- **M05-B — Integración anatómica:** una vez auditado M05-A, conectar el manifest y catalog con SHA, Rust/WASM WebGPU/WebGL2, cámara, picking, visibilidad, eventos, offline y manejo de errores reales.
- **M05-C — Certificación de UX multiplataforma:** gestures, a11y, teclado, dynamic viewport, safe area, PWA, Safari iPhone/iPad/macOS, Android, Windows touch, performance móvil y matríz de excepciones.

No iniciar M05-B ni declarar el contrato congelado si F01/F02/F03 persisten.

## 2. Propiedad de estado — sin duplicación de 3D

| Área | Autoridad | Cliente React |
|---|---|---|
| Geometría, mallas, GPU, materiales, camera, picking, selección, visibilidad, sceneRevision | atlas-core en Rust vía atlas-web WASM | Comandos tipados, snapshots puntuales |
| Generación de escenas y planes canónicos | AtlasEngine instance_generation y ManifestSnapshot Rust | Adaptador serializa operaciones y descarta requests obsoletos |
| Network, CacheStorage, abort, concurrency y retries | AssetStreamManager en JavaScript; NO "Rust scheduler" | Un solo RuntimeClient lo instancia, no otro fetch de React |
| Nombres ES/EN/LA, TA2, lado, regiones y variantes | catalog.json verificado contra SHA/tamaño de manifest.json | Buscador, árbol, encabezado, inspector |
| Paneles, navegación, sheet, tema, búsqueda, foco, idioma | React UI store | Render y preferencias |
| Canvas, DPR, surface, failover WebGPU→WebGL2 y render-on-demand | Rust + host del canvas | Sólo resize, gestos y eventos |

**Catálogo real:** schemaVersion=0, structures[] con id, labels["es-MX"], labels.en, labels.la, side, ta2Id, licenseStatus. Ejemplo real para id ta2:1071: es-MX="Hueso sacro", en="Sacrum", la="Os sacrum". No copiar "Sacro" del wireframe como si fuera la fuente, ni inventar sistemas y relaciones médicas.
**Manifest actual:** atlasVersion="0.3.0"; regions=["pelvis"]; variants=["male-adult"]; core packages pelvis-base-lod0 (38,605 tris) y pelvis-lod1 (33,758 tris); paquete meshopt experimental no compatible; NO inventar female-adult ni otras regiones. Assets fuente pendiente por licencia individual: no publicarlos ni exponerlos en repositorio público.
**Stable keys:** AnatomyId TA2 exacto, nunca índice glTF, índice de array o label visual.

## 3. App y árbol de componentes (M05-A)

Crear apps/viewer NUEVO (React + TypeScript estricto + Vite como opción por defecto tras verificar stack). Mantener apps/probe-web intacto salvo defectos de transporte comprobados.

Responsabilidades:
- app/AppShell + WorkspaceLayout: geometría responsive y ownership de paneles.
- layout/TopBar, NavigationRail, ExplorerPanel, InspectorPanel, ViewerStage, AnatomySheet, OverlayHost.
- anatomy/AnatomyTree, AnatomySearch, RegionSelector, StructureRow, StructureIdentity.
- controls/CameraToolbar, VisibilityActions, ThemeToggle, QualitySelector. No mostrar controles de motor no soportados.
- status/LoadingOverlay, ErrorPanel, OfflineIndicator, BackendStatus (evitar indicadores falsamente "online" o "3D ready").
- runtime/AtlasRuntimeClient, AtlasRuntimeStore, wasm-loader, bridge-types, catalog-types, RenderScheduler, CanvasLifecycle, GestureController.
- styles/tokens.css, reset.css, themes.css, responsive.css, app.css. Prefijo atlas-; sin framework CSS pesado ni estilos globales que contaminen probe.
- test/ de componentes/contratos/visual/accessibility.

M05-A utiliza placeholders originales con texto explícito "Vista conceptual" o cubo sintético permitido, sin importar GLB anatómico no licenciado ni usar SVG como modelo médico. No iframe HTML del wireframe como aplicación final; reimplementar componentes React semánticos.

## 4. D0 visual congelado (aprobado)

**Clinical Precision / Obsidian Navy (Modern Sky Blue Accent):** bg #05080D, canvas #03060B, panel #0B111C, border #202D40, text #F0F5FA, accent #58B9FF, accent-hover #7AC8FF, accent-strong #2E9CFF, nav-accent #7FB8FF; light #F5F8FA / #FFFFFF / #162736, accent #087A7A. Colores de materiales anatómicos INALTERADOS por tema. Sistema de spacing múltiplos 4, radios 8/12/16, sombras mínimas, blur apagado en móvil; sin glow ni gradientes de marketing.
**Breakpoints por CSS viewport + altura, nunca UA:** compact 320–599, compact-wide 600–839, tablet 840–1119, workstation 1120–1535, pro-wide >=1536. Guardas: canvas >=720 y altura >=650 para pro-wide; >=640 workstation, >=540 tablet; degradación si no cabe.
**Wireframes base:** 1536×960 rail64 + explorador296 + stage832 + inspector344; 1280×800 rail56 + explorer296 + stage928 + inspector drawer; iPad834×1194 stage full + overlay único; iPhone390×844 stage390 + sheet colapsado (~110px), medio 52%, expandido 86%.
**Responsive:** header 60/56/52/48 según viewport/altura, 100dvh con fallback, safe-area env, VisualViewport para teclado virtual, input search >=16px, Touch targets >=44x44 CSS px, CSS grid minmax(0,1fr), min-width:0, foco visible, Escape, reduced-motion. No horizontal overflow, no zoom prohibido, no hover-only.
**Canvas:** NO reinicializar dispositivo por tema, panel, zoom, teclado o orientación; ResizeObserver batch + DPR acotado; no CSS transform scale. Overlay de sheet/explorer mutuamente exclusivo.

## 5. Store y puente Rust/WASM: contrato de eventos real

UI store: layoutMode, activeOverlay (none/explorer/inspector), sheetSnap (collapsed/mid/expanded), sheetTab, theme, searchQuery, categoryFilter, locale, qualityPreference, currentRoute, focusReturnTarget, alert visible.

Runtime store (solo derivado del motor): status (idle/initializing/loading/firstFramePending/ready/recovering/error/disposed), capabilities, SceneSnapshot, manifest/cat version, requestId, sceneGeneration, sceneRevision, backend, selectedId, visibleIds, memoryEstimate, error.

**Importante: API real del código no coincide completamente con ejemplos conceptuales.**
- Rust SceneSnapshot serializa snake_case: selected_id, scene_revision, visible_ids, region, variant, quality, backend; EngineCapabilities también snake_case (adapter_name, max_texture_dimension_2d).
- wasm-bindgen exporta métodos en camelCase (initialize, loadManifest, createLoadPlan, nextGeneration, applyPackageBytes, getSceneSnapshot, setEventCallback, renderFrame, selectAt, selectStructure, ...). Usar paquetes realmente generados para WebGPU y WebGL2 y comprobar firmas.
- setEventCallback entrega un evento desde Rust DENTRO de préstamo mutable RefCell; callback de JS **no invocará engine.* de forma síncrona**. Encolar a microtask/event queue antes de leer snapshots o enviar comandos, evitando reentrancia.
- ApplyPackageBytes confirma staging, NO primer frame. AssetStreamManager.loadRegion actual llama callbacks.onSuccess tras applyPackageBytes: "submitted", NO UI ready. Sólo evento region.ready tras renderFrame exitoso, con requestId + sceneGeneration coincidentes, puede cerrar loading.
- Para evento structure.selected/scene.changed, hacer snapshot selectivo/agrupado por revisión, no copy de matrices ni rerender React por frame.
- Eventos region.failed/engine.error pueden no llevar metadata completa; normalizarlos sin inventar requestId; los errores recuperables no borran escena anterior.
- Un sólo engine por canvas; StrictMode mount/unmount dev: disposal idempotente, tokens de instancias, abort y cleanup listeners; evitar dos GPU contexts activos.
- El Scheduler de React nunca controla el reloj de GPU con setState 60fps; requestAnimationFrame sólo cuando motor pide render, transiciones o interacción; descanso real en idle.

## 6. Gate M04-H.1 (bloqueante para M05-B, incorporado a M05-A)

**F01 P0 — coalescing cancellation:** asset-stream-manager.js inFlightRequests reutiliza promesa creada con signal del PRIMER caller; si aborta el primero, segundo falla. Reparar con una entrada por cacheKey y suscriptores/AbortSignals independientes; la operación subyacente sólo se aborta cuando no hay interesados; evitar leaks de listeners y aborto después del commit. Prueba de Chrome real usando tools/audit_m04h_scheduler.py y tests adicionales A+B, abort A, B sigue con 1 fetch; abort ambos produce cancel, sin promesas zombies.

**F02 P1 — 404 sin reintentos:** fetchWithRetry captura su propio error terminal y lo trata como transitorio, y puede duplicar incrementos del contador retries. Rechazar 400/401/403/404/410 y digest mismatch inmediatamente; reintentar 408/429/5xx y errores de transporte transitorios según política limitada, backoff abortable y timeout adecuado. Tests adversariales: 404 exactamente 1 fetch; 503 2–3 fetch según maxRetries; abort durante backoff detiene todos; no doble incremento.

**F03 P1 — prueba de memoria browser válida:** gate E de tools/test_m04h_hardening.py llama setQualityProfile("invalid_profile_name"), que no demuestra MEMORY_LIMIT. Crear test real del preflight GPU/CPU a través de WASM/buffer con presupuesto forzado sólo en build de diagnóstico o test API; invalid profile debe ir en su test propio. Verificar que memoria insuficiente devuelve MEMORY_LIMIT, no destruye geometría GPU previa, no genera falso region.ready y restaura visibilidad/selección. Si no se puede inducir sin afectar producción, marcar gate BLOCKED, nunca PASS por atajo.

**No adjudicar:** benchmark 120 llamadas JS a FPS, pérdida controlada de GPU a driver-loss físico; F04–F07 de auditoría deben quedar declarados NOT_RUN o riesgos aceptados, no desaparecer del informe.

## 7. Alcance operativo por subfase

| Función | M05-A | M05-B | M05-C |
|---|---|---|---|
| Shell React, layout, temas, responsive, paneles, estados | Real, testado | Mantener | Certificar |
| Nomenclatura catálogo SHA, variantes publicadas | Contratos y fixtures | Carga/consulta real | Verificación |
| Bridge typed, WebGPU/WebGL2 WASM | Adaptador + smoke sintético | Integración 3D real | Stress |
| selectAt, selection, isolate, visibility, focus, presets | Controles UI demo sin fingir funcionamiento | Motor real | Tests |
| Streaming real/cache/offline | Reparar F01–F03 y tests | Cargar assets locales verificados | Mobile |
| Gestos touch, keyboard, stage DPR, PWA | Diseño contract/test scaffolding | Implementar | Prueba real física |
| Clipping, disección, medidas, cuerpo entero, variante femenina | OUT | OUT | OUT |

## 8. Gate de calidad M05-A

- React/TS estricto con tests unitarios de componentes, no all-any TypeScript; lint/build PASS.
- Capturas 1536×960,1280×800,834×1194,390×844,320×568,360×800,844×390,1024×768,1920×1080 y dark/light + empty/selected/loading/error; no overflow, sin tablas de marketing en canvas, sin doble overlay.
- 44×44 touch targets, 16px inputs en móvil, safe areas, reduced-motion, zoom 200%, teclado, Escape, foco restaurado; no CSS frameworks ocultando estilos de proyecto.
- Canvas placeholder original NO se hace pasar por anatomía clínica, no copiar mallas, no subir .glb o .blend a GitHub público.
- F01/F02/F03 PASS independiente y verificado; Rust 38+ tests sin borrar pruebas, cargo fmt/clippy/wasm PASS, M04 probe sigue 9/9 PASS; la suite visual wireframes 12/12 + interacciones 9/9 no debe romperse.
- Si no pasa gate transporte/memory: detener antes de integrar motor 3D final; declarar PARTIAL y pendientes exactos.
- No iniciar M05-B, hacer push/commit/merge o deploy sin solicitud ulterior.
