# ANATOM.IA — PROMPT 05 PARA ANTIGRAVITY
## M05-A: FOUNDATION ENTERPRISE REACT + CIERRE DE GATES M04-H.1

**Rol:** Principal Frontend Architect (React, TypeScript estricto, CSS responsive) + Senior Rust/WASM/WebGPU Reliability Engineer + QA Lead de accesibilidad y navegadores.
**Ruta:** C:\Users\datam\Documents\anatom.ia
**Rama observada:** feature/m04-runtime-streaming; HEAD be654ca.
**Repo existente PÚBLICO:** https://github.com/anuaralejandro/anatom.ia
**Objetivo único:** implementar un frontend React de calidad enterprise fiel a los wireframes APROBADOS, más reparar y comprobar tres defectos del runtime de M04-H. No integrar todavía atlas clínico definitivo (reservado para M05-B). No publicar ni hacer push.

## I. PRE-FLIGHT Y DOCUMENTACIÓN DE LECTURA OBLIGATORIA

Lee ÍNTEGRAMENTE, antes de proponer o editar:
1. docs/14_M05_D1_INTEGRATION_CONTRACT.md — contrato D1 principal; respétalo como norma.
2. docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md — reglas de estilo y responsive por anchura y altura.
3. docs/13_M05_WIREFRAME_REVIEW.md — D0 aprobado por propietario.
4. docs/m05-wireframes/gallery.html + index.html + styles.css + mock.js.
5. docs/m05-wireframes/review/design-review-results.json + interactions-results.json.
6. docs/AUDITORIA_IMPLEMENTACION_04H.md — defectos F01-F07 y veredicto independiente.
7. reports/audit/m04h-independent-scheduler.json + tools/audit_m04h_scheduler.py.
8. docs/M04_RUNTIME_BRIDGE_CONTRACT.md; crates/atlas-web/src/lib.rs y crates/atlas-core/src/types.rs, memory.rs, renderer.rs.
9. apps/probe-web/asset-stream-manager.js, app.js, service-worker.js.
10. docs/11_M05_PLAN_UX_ARQUITECTURA_V0.md, docs/M04_HARDENING_RESULT.md, package.json, contratos de calidad/bridge existentes.

**Regla de integridad:** hay CAMBIOS LOCALES M04-H/auditorías importantes aún SIN COMMIT. NO git reset --hard, clean -fd, stash destructivo, checkout/rebase que sobrescriba archivos, force-push, merge, commit ni push. NO tocar ni incorporar al Git público los archivos GLB/BLEND o capturas de Z-Anatomy sin derechos claros. No modificar sources/z-anatomy-upstream.

Ejecutar y registrar:
- git status --short --branch
- git log -3 --oneline
- git diff --stat, git diff --check
- git -C sources/z-anatomy-upstream status --porcelain
- cargo fmt --all -- --check
- cargo clippy --workspace --all-targets -- -D warnings
- cargo test --workspace (38/38 en auditoría previa, comprobar ahora)
- cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder
- python tools/test_m04h_hardening.py
- python tools/test_m04_streaming.py
- python docs/m05-wireframes/review_wireframes.py
- python docs/m05-wireframes/review_interactions.py

No interpretar tests SKIPPED/NOT_RUN como PASS. No inventar outputs. Si existe un blocker, documentar.

## II. A0 — ARREGLAR DEFECTOS BLOQUEANTES ANTES DE CONECTAR REACT A LA CARGA REAL

### A0.1 F01 (P0): cancelación correcta de solicitudes coalescidas
AssetStreamManager actual comparte una misma Promise dependiente del AbortSignal del primer consumidor. Test previo: dos solicitudes del mismo hash con 1 fetch, se aborta A, y ambas son rechazadas.

Implementar entrada por clave SHA+versión+package con controlador de transporte propio, lista/mapa de suscriptores independientes y promises independientes. Abortar A sólo rechaza A y no interrumpe B. Abort subyacente SOLO cuando no queda ningún consumidor activo. Limpieza de event listeners y Map al completar/abortar/fallar; sin unhandled rejection. No coalescer distintos SHA/versiones.

Prueba adversarial navegador Chrome REAL:
- A+B mismos bytes, un fetch. Abort A => A AbortError, B SUCCESS; sólo 1 fetch.
- Abort B => B AbortError, A SUCCESS.
- A+B abortados => abort network y limpieza de Map.
- C se une tarde a B => 1 fetch total y ambos supervivientes resuelven.
- Cache hit, queued cancellation y cambio de versión nunca reusan datos erróneos.
Volver a ejecutar tools/audit_m04h_scheduler.py y demostrar diferencia con reporte anterior.

### A0.2 F02 (P1): retry sólo cuando corresponde
fetchWithRetry lanza el error HTTP 404 dentro de try y catch vuelve a reintentarlo como error de red; antes se midieron 4 fetches con maxRetries 2.

Separar explícitamente resultado HTTP terminal (400,401,403,404,410), transitorio (408,429,500,502,503,504), abort y error de red/timeout. 404 debe causar exactamente 1 intento y ningún backoff. 503 con maxRetries=2 => 3 intentos máximo. Abort durante backoff cancela. SHA/size corruptos => fallo terminal sin reintentos de transporte. Actualizar retriesCount una vez por retry real, no doble incrementos. Evitar timers y señales huérfanas; usar tests HTTP interceptados con conteos EXACTOS.

### A0.3 F03 (P1): memory preflight browser real
Gate E de tools/test_m04h_hardening.py sólo pasaba perfil inválido, NO MEMORY_LIMIT. Separar test enum inválido de un caso real de preflight WASM/Rust con presupuesto intencionalmente inferior al pico; permitir hook de diagnóstico/test exclusivamente, o fixture sintético de alta carga controlada. Assert: ErrorCode.MEMORY_LIMIT, selección/escena/buffers previos conservados, no region.ready falso, explicación del presupuesto/peak. Test Rust CPU/GPU y al menos 1 prueba en browser WASM. No manipular reporte para simular PASS. Si queda técnicamente bloqueado, status BLOCKED y no conectar atlas real.

**A0 Gate:** todos los checks F01/F02/F03 PASS demostrados, luego proceder con A1-A3. Si alguno falla, construir como mucho shell UI conceptual y reportar PARTIAL; NO integrar carga real, NO declarar M05-A completo.

**Riesgos F04-F07:** no declarar FPS por 0.08ms de llamadas JS, no confundir GPU loss simulada con pérdida física, no declarar cero memory leaks por contador analítico y no declarar Safari/iOS probado por Playwright Chrome.

## III. A1 — CREAR NUEVO FRONTEND REACT DE FUNDACIONES

Crear apps/viewer/ independiente del probe existente. Elegir React + TypeScript strict + Vite con versiones reproducibles y una estrategia coherente de package-lock; verificar dependencias/seguridad/licencias. Actualizar comandos root aditivamente sin cambiar el build WASM vigente. Sin backend, API, auth, Stripe, IA, CMS, PWA pública ni deployment.

Crear componentes pequeños y tipados siguiendo la matriz de docs/14_M05_D1_INTEGRATION_CONTRACT.md:
- AppShell, TopBar, NavigationRail, ExplorerPanel, ViewerStage, InspectorPanel, AnatomySheet, OverlayHost.
- AnatomyTree, AnatomySearch, RegionSelector, StructureRow, StructureIdentity.
- CameraToolbar, VisibilityActions, ThemeToggle, QualitySelector.
- LoadingOverlay, ErrorPanel, OfflineIndicator, BackendStatus.
- AtlasRuntimeClient/Store, wasm-loader, bridge-types/catalog-types, CanvasLifecycle/RenderScheduler/GestureController (pueden comenzar como contratos testeables de implementación diferida cuando la etapa aún no requiere el motor).
- CSS tokens, reset, responsive, themes, app; prefijo atlas-.

No reusar prototipo D0 como iframe ni copiar mock.js entero dentro de React. Inspirarse visualmente en las capturas y recrear con componentes semánticos, props explícitas, eventos y estilos estructurados. No meter toda la app en un solo App.tsx de 1000 líneas. No usar Tailwind/Bootstrap/Material como estilo impuesto que cambie jerarquía aprobada; si se usa una librería para comportamiento accesible, justificarla.

**UI-M05-A es un preview de diseño:** si no está conectada al motor, indicar "Vista conceptual" claramente. Acciones anatómicas disabled/aria-disabled y tooltip explicativo, o demo marcada; NUNCA fingir que se aplicó un focus/isolate real. Puede usar cubo sintético del motor exclusivamente para un smoke de bridge, NO generar screenshots de anatomía fuente sin licencias.

## IV. A2 — ADHERENCIA VISUAL ESTRICTA AL D0 APROBADO

Diseño aprobado Clinical Precision / Midnight:
- dark oficial OBSIDIAN NAVY / MODERN SKY BLUE: bg-app #05080D, bg-canvas #03060B, bg-panel #0B111C, bg-raised #121C2B, bg-hover #19273A, border #202D40, text-primary #F0F5FA, text-secondary #A3B2C5, accent #58B9FF, accent-hover #7AC8FF, accent-strong #2E9CFF, accent-soft rgba(88,185,255,.14), nav-accent #7FB8FF. El azul cielo sustituye definitivamente el turquesa anterior. Usar los tokens reales del wireframe aprobado, sin restaurar paletas históricas.
- light se mantiene INALTERADO: bg #F5F8FA, panel #FFFFFF, foreground #162736, border #DCE5EC, accent #087A7A. No aplicar la familia azul cielo al tema claro sin petición posterior.
- spacing múltiplos de 4, radii 8/12/16, shadows discretas, tipografía system UI o Inter legal, sin video/parallax/glassmorphism/marketing cards.
- El canvas central siempre es protagonista. No reestructurar a dashboard con gráficas.

Breakpoints exactos por viewport CSS, no por marca o UA:
- compact 320–599; compact-wide 600–839; tablet 840–1119; workstation 1120–1535; pro-wide >=1536.
- Pro-wide sólo si stage >=720px y altura útil >=650; workstation stage >=640; tablet stage >=540; degradar por espacio. Desktop 1536x960: rail64+explorer296+stage832+inspector344. MacBook1280x800: rail56+explorer296+stage928+inspector drawer. iPad834x1194: stage full + overlays alternos. iPhone390x844: stage full+bottom sheet collapsed/52%/86%.
- Header 60/56/52/48px según altura/ancho. CSS grid minmax(0,1fr) y min-width/min-height:0; 100dvh fallback, safe-area env(top/right/bottom/left), VisualViewport para teclado.
- Buttons touch >=44x44 CSSpx; search input >=16px en iOS. Selección accesible por teclado, ARIA, Escape, focus return, bottom sheet con scroll separado de drag, no overlays simultáneos.
- reduced-motion, dark/light sin afectar materiales de los órganos, sin horizontal overflow, compatibilidad zoom 200%. Ningún control crítico sólo en hover.
- No reinicializar Rust canvas al abrir/cerrar panel o alternar tema. Canvas no se escala con CSS transform. DPR topes por perfil cuando se integre, no render 4K por capricho.

Revisar las capturas ORIGINALES de docs/m05-wireframes/review/ en Chrome/Playwright: 1536x960, 1280x800, 834x1194, 390x844. Generar capturas equivalentes React y comparación lado a lado; documentar cualquier desviación (no modificar referencia para que coincida).

**OUT:** inventar zonas clínicas nuevas, contenidos médicos sin fuente, función femenina aún no publicada, cortador, mediciones 3D, exploded view, tutor IA, login, API tradicional o catálogo completo sin assets reales.

## V. A3 — BRIDGE TYPES Y PROPIEDAD DE ESTADO

No duplicar escena/cámara en React.
Rust controla geometría, cámara, selección, visibilidad, GPU. AssetStreamManager controla descarga/caché. React controla layout/paneles/idioma/tema/search/UI state.

IMPORTANTE: el bridge wasm-bindgen exporta métodos camelCase pero SceneSnapshot de Rust serializa selected_id, scene_revision y visible_ids en snake_case; EngineCapabilities tiene adapter_name, backend_type. Verificar contra .d.ts REAL compilado, crear adaptador normalizador único a TS camelCase. No usar any masivo ni tipos inventados.

setEventCallback llama JavaScript durante RefCell mutable Rust: callback JS DEBE únicamente encolar evento (microtask), sin llamar engine.getSceneSnapshot ni engine.selectStructure de forma síncrona; evitar reentrancia. Registro de listeners único y cleanup al dispose. Generaciones/IDs de requests siempre verificadas.

La resolución de AssetStreamManager.loadRegion sucede tras applyPackageBytes, NO después de presentarse un frame: en M05-B la UI sólo marcará Ready al recibir region.ready del motor con requestId+sceneGeneration concordantes. Por ahora escribir pruebas/adaptador sin conectar GLB real.

Quality profile, WebGPU/WebGL2, SVG/Canvas host y switches deben contemplar StrictMode mount-unmount, dispose idempotente y aislamiento de contextos. No hacer React setState en cada frame; usar store con subscripciones puntuales o useSyncExternalStore.

## VI. GATES M05-A QUE DEBES PROBAR

- Tests nuevos de scheduler: cancelación independiente y 404 terminal, 503 transitorio, abort backoff, ningún unhandled Promise rejection; exponer requests/aborts reales medidos.
- Test real browser WASM memory rejection con código MEMORY_LIMIT, no perfil inválido.
- React build, TypeScript strict, eslint/lint y unit tests PASS.
- Suite nueva Playwright de apps/viewer en 320x568,360x640,375x667,390x844,430x932,600x800,768x1024,834x1194,844x390,1024x768,1194x834,1280x800,1366x768,1440x900,1536x960,1920x1080; variaciones light/dark, selected/empty/loading/error, inspector abierto, sheet expandido.
- Assertions automáticas: scrollWidth <= clientWidth+1, stage visible y con medidas útiles, no paneles fijos cuando se desborda, targets touch >=44px, 16px search, no dos overlays, Escape close y foco recuperado, reduced motion, zoom 200%.
- 20 ciclos resize/theme/panels NO acumulan listeners o render contexts; solo placeholder para M05-A, sin afirmar carga de pelvis.
- Compatibilidad M00-M04: cargo fmt, cargo clippy, cargo test >=38, wasm check, suite M04H 8/8, M04 streaming 9/9, auditoría catálogo tamper, upstream clean.
- Chrome Windows + emulación de viewport NO equivalen a pruebas de iPhone Safari, iPadOS, Mac Safari ni Android. Registrar estos como NOT_RUN, no PASS físico.
- No incluir ningún .blend/.glb de Z-Anatomy ni capturas derivadas de fuente protegida en changeset público.

Si falta hardware/dependencia indicar BLOCKED con evidencia; nunca declarar 100% sobre pruebas que no se corrieron.

## VII. RESULTADOS QUE DEBES DEJAR

Crear:
- apps/viewer/ con React, componentes y tests.
- apps/viewer/README.md con comandos Windows.
- docs/M05A_IMPLEMENTATION_RESULT.md con arquitectura, capturas, decisiones y riesgos.
- docs/ADR_007_REACT_WASM_OWNERSHIP.md y docs/M05A_RUNTIME_COMPONENT_MATRIX.md.
- reports/implementation/M05A/gate-results.json.
- reports/implementation/M05A/visual-audit.json.
- reports/implementation/M05A/scheduler-adversarial.json.
- reports/implementation/M05A/memory-preflight-browser.json.
- scripts tests reproducibles y reportes de regresión.
- Actualizar README raíz e índice; no sobrescribir documentos D0/D1 aprobados para maquillar divergencias.

**Entrega final en español:** estructura real creada, screenshots de React vs D0, tests exactos + códigos de salida, diferencias, qué está simulado, pendientes para M05-B, y git status sin commit/push.

**NO IMPLEMENTAR M05-B, NO PUBLICAR, NO COMMIT, NO PUSH.** Antigravity debe implementar M05-A, no entregar una propuesta. El siguiente gate es AUDITORÍA INDEPENDIENTE ANTES de M05-B.
