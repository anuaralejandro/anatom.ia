# ANATOM.IA — PROMPT 07 / ANTIGRAVITY
## M05-B — ATLAS 3D REAL EN REACT, GIZMO VINCULADO Y STUDIO GRAPHITE

ROL: Principal Rust/WASM/wgpu 30.0.1 Graphics Engineer, React/TypeScript Architect, QA Lead.
WORKSPACE: C:\Users\datam\Documents\anatom.ia
RAMA: feature/m04-runtime-streaming; working tree PREEXISTENTE con decenas de cambios sin commit.
PRIORIDAD ABSOLUTA: El propietario ya está cansado de ver una silueta 2D. Sustituirla por la pelvis 3D GLB REAL funcionando dentro de apps/viewer en WebGPU y WebGL2. NO entregar más wireframes, Canvas 2D como anatomía, simulaciones de cámara ni supuestos PASS.
OBJETIVOS SECUNDARIOS: conectar de verdad el gizmo de Blender a la cámara Rust y rediseñar el tema alternativo blanco hacia Blender Studio Graphite.
NO crear M05-C, M06, backend, login, IA, otros órganos, ni publicar assets.

0. PRE-FLIGHT OBLIGATORIO

Leer completos:
- docs/AUDITORIA_IMPLEMENTACION_05A1_INDEPENDIENTE.md — nueva auditoría.
- docs/15_M05B_INTEGRATION_PLAN.md, docs/14_M05_D1_INTEGRATION_CONTRACT.md.
- docs/M05A_QA_CLOSEOUT_RESULT.md, docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md, docs/13_M05_WIREFRAME_REVIEW.md.
- docs/M04_RUNTIME_BRIDGE_CONTRACT.md, docs/ADR_005_GPU_SWAP_AND_RECOVERY.md, docs/ADR_006_MEMORY_AND_SCHEDULER.md, docs/ADR_007_REACT_WASM_OWNERSHIP.md.
- crates/atlas-web/src/lib.rs y crates/atlas-core/src/{camera,renderer,scene,manifest,memory,types}.rs.
- apps/viewer/src/components/layout/{ViewerStage,AppShell,TopBar,ExplorerPanel,InspectorPanel,AnatomySheet}.tsx.
- apps/viewer/src/components/controls/{AxisNavigationGizmo,CameraToolbar,ThemeToggle,QualitySelector}.tsx.
- apps/viewer/src/runtime/{AtlasRuntimeClient,bridge-types,normalizer}.ts; apps/viewer/src/store/useUIStore.ts.
- apps/viewer/src/styles/{tokens,themes,app,responsive}.css; vite.config.ts y package.json.
- apps/probe-web/{app.js,asset-stream-manager.js,manifest.json,catalog.json,service-worker.js}; apps/probe-web/pkg-webgpu y pkg-webgl2, tools/serve_probe.py.
- tests previos M04H/M05A; scripts de recompilación WASM y docs/BUILD_RUNTIME.md.

Guardar estado Git previo: git status --short --branch; git diff --stat; git diff --check; git log -3 --oneline y git -C sources/z-anatomy-upstream status --porcelain.
Reproducir baseline: npm test y npm run build en apps/viewer; cargo fmt/clippy/test y wasm32 check; python tools/test_m05a_react_suite.py y python tools/test_m04_streaming.py.
Sin git reset, clean, stash destructivo, rebase, commit, push, merge, deploy o borrado de cambios locales. Sin alterar GLB, .blend ni fuentes originales. No introducir Three.js ni Babylon ni recrear el motor en JS.

1. B1 — PRIMER FRAME GPU REAL EN APPS/VIEWER [GATE DE PARADA]

ANTES de cualquier refinamiento del modo claro, conseguir que http://127.0.0.1:3000 muestre una pelvis masculina anatómica REAL con 26 estructuras TA2 y materiales/iluminación PBR core, no la línea azul sintética.

- ViewerStage.tsx hoy usa canvas.getContext('2d') para dibujar una silueta. ELIMINAR esta ruta del viewer funcional. La prueba negativa debe detectar cualquier regreso a render 2D presentado como anatomía.
- CanvasHost nuevo con un ÚNICO canvas GPU estable por instancia, sin contextos 2D+wgpu sobre el mismo canvas. StrictMode cleanup, abort, dispose idempotente, ResizeObserver, DPR efectivo por perfil, dimensiones CSS vs framebuffer y pointer mapping correctos.
- Cargar dinámicamente los dos bundles WASM reales M04H: WebGPU preferido, WebGL2 fallback. Comprobar initialize y getCapabilities reales, no defaults falsos ni selección de backend por simple query param. Verificar firmas wasm-bindgen y objetos serde snake_case. Recompilar bundles tras cambiar Rust; NO reutilizar wasm desfasado.
- AssetStreamManager compartido: verificar manifest/catalog tamaño+SHA-256; Rust createLoadPlan canónico, nextGeneration y applyPackageBytes; no fetch duplicados en React. GLB local pelvis-base-lod0.glb de 681500 bytes SHA 1510ed9a93b54c8067543b4a13e92ee713f1d75adc2687324ad29a72b76244ae y pelvis-lod1.glb de 593928 bytes SHA 4c1054b116b972be97ed367cb4d0a7242098c92d31e094d2127b621168346391. Recalcular hashes y rechazar mismatch. NUNCA seleccionar meshopt experimental no soportado.
- Assets GLB sujetos a revisión de licencia individual. Sirve los datos SOLO mediante proveedor local PRIVADO de desarrollo, con lista blanca de rutas/archivos y controles contra path traversal. NO copiar GLB a public/ ni hacerlos versionables/deployables, CDN, GitHub público o capturas públicas. Asegurar gitignore real de la carpeta de test/screenshot protegida. No inferir que permiso de usar localmente implica derecho de distribución.
- Ajustar fit-to-bounds y vista anterior anatómica del modelo REAL; garantizar visibilidad, orientación, iluminación, proporciones, no recortes y no negro sobre negro. No pintar una falsa pelvis con svg/canvas sobre el GLB.
- Loading real por etapas, region.ready sólo tras primer frame presentado y requestId+sceneGeneration correctos; el resultado de applyPackageBytes NO es ready. Falla real GPU/asset muestra mensaje recuperable y fallback WebGL2, NUNCA la silueta 2D.
- Crear screenshot E2E de Chrome WebGPU Y de Chrome WebGL2 ejecutándose de verdad dentro de React; inspeccionar píxeles y estadísticas glTF: 26 IDs TA2; triángulos indexados LOD0=38605 o LOD1=33758, según versión/cifras verificadas de GLB; HTTP 200 de GLB; SHA válido; backend efectivo coincide con getCapabilities. No aprobar por mera carga de HTML/React o token WEBGPU.
- FIRST REAL 3D GATE: si no se ve la pelvis real con ambos backends, DETENER LAS DEMÁS ETAPAS y entregar root cause, logs, errores y estado BLOCKED/PARTIAL. NO volver a refinar dibujo 2D.

2. B2 — ACCIONES ANATÓMICAS REALES

Sólo cuando B1 pasó:
- Eliminar defaults ficticios de AtlasRuntimeClient (backend webgpu, Mock/Synthetic Engine, fake caps). No realizar actualizaciones optimistas del selectedId/visibleIds ni sceneRevision que Rust no confirmó. Fuente de verdad: eventos y snapshot Rust. React sólo controla tema, paneles y UI.
- Árbol TA2 ES-MX/EN/LA de catálogo SHA real. Selección por click en modelo (selectAt) o fila (selectStructure) sincronizada con inspector, highlight y lista. 26 IDs estables incluso con bilateralidad.
- Aislar, ocultar, mostrar, restablecer, enfocar, orbitar, pan, zoom, reset, quality profile y LOD0/LOD1 deben afectar geometría real; quitar marca (Demo) sólo de botones que ya ejecuten acciones. Al cambiar LOD conservar cámara, selección y visibilidad, y aplicar swaps GPU transaccionales M04H.
- Mouse, touch/pinch dos dedos, tablet/stylus, keyboard equivalentes y canvas touch-action limitado; no interceptar scroll del sheet ni gestos del navegador en los demás paneles.
- Validar que selección/ocultamiento no son meros cambios en el store de React; verificar píxeles, sceneRevision y getStats del motor en E2E.

3. B3 — GIZMO REAL ESTILO BLENDER

Actualmente AxisNavigationGizmo.tsx usa estados propios de yaw/pitch; onSelectAxis sólo console.info. Esto no es navegación del atlas.
- Exponer camera state de Rust de forma mínima y tipada (p. ej. getCameraState con yaw, pitch, distance, view orientation o matriz) y hacerlo fuente ÚNICA del gizmo. No duplicar una cámara React. Debe actualizarse al orbitar, al reset, al enfocar y al accionar cualquier eje.
- Los presets Rust existentes 0,1,2 NO permiten seis caras ortogonales. Implementar setCameraAxis/snapToAxis seguro para +X,-X,+Y,-Y,+Z,-Z, con orientación estable en polos ±Y y mismo target/distancia. Rust tests + WASM tests reales.
- CORREGIR LATERALIDAD del gizmo: manifest.coordinateSystem.patientLeft = +X. Por tanto +X=lado IZQUIERDO del paciente, -X=DERECHO, +Y=superior, -Y=inferior, +Z=anterior, -Z=posterior. No invertir modelo ni dar nombres clínicos de derecha/izquierda de observador.
- Desktop gizmo 64–76 px elegante y minimalista; en touch móvil, los seis hit targets NO caben con 44×44 sin superposición. Usar gizmo compacto que abre popover accesible con seis controles >=44×44, labels, foco y Escape. SVG circle r16 actual tiene sólo 32 px y no cumple seis targets separados.
- Cada eje clicado mueve la CÁMARA REAL y el modelo; no sólo las esferas del icono. Animación breve opcional, sin movimiento con prefers-reduced-motion. Screenshot real antes/después de seis orientaciones y comprobación de cámara numérica.

4. B4 — REEMPLAZAR MODO CLARO POR STUDIO GRAPHITE

El propietario rechazó el modo claro actual (paneles blancos/canvas azul pálido y acento verdoso); quiere algo en la familia del oscuro o de Blender.
- NO CAMBIAR tema oscuro Obsidian Navy aprobado, acento Modern Sky Blue #58B9FF.
- Sustituir visualmente el antiguo light por una variante nombrada STUDIO GRAPHITE: interface neutral gris grafito/media, claramente distinta de Obsidian pero sin blanco clínico ni azul gris pastel; viewport 3D SIEMPRE casi negro incluso en tema alternativo.
- Tokens sugeridos para contrastar y ajustar mediante screenshots: bg-app #242A33; bg-panel #303946; bg-raised #3C4858; bg-hover #465569; border #4E5B6D; bg-canvas #080E16; text-primary #EFF4FA; text-secondary #BAC6D4; accent #58B9FF; accent-hover #7AC8FF; accent-strong #2E9CFF; accent-soft rgba(88,185,255,.14). Puedes modificar sólo estos tokens orientativos si la estética Blender mejora y contrastes WCAG 2.2 AA se cumplen. NO verde petróleo #087A7A ni turquesa.
- Si la bandera interna data-theme=light debe mantenerse por compatibilidad, la UI etiqueta el toggle como Studio/Obsidian, no blanco/oscuro. Misma geometría de paneles y controles, sin glow ni glassmorphism.
- Cambiar tema NO reinicializa device, no recarga GLB, no cambia identidad TA2/cámara y no recolorea arbitrariamente materiales científicos del atlas.
- Generar comparativas REAL 3D lado a lado dark vs Studio en 1536x960,1280x800,834x1194,390x844; probar AA contraste y navegación.

5. B5 — RESILIENCIA Y RESPONSIVE

- Mantener invariantes M04H (integridad hash, abort subscriber independiente, 404 terminal, cache corruption, CPU/GPU budgets). Manejo device loss y WebGPU->WebGL2 fallback con error visible. Nunca prometer pérdida física de driver verificada.
- Offline en viewer con Service Worker scope propio, sin mezclar service worker del probe, y sólo si material de assets tiene permiso y está aislado localmente; no proclamar offline real si no se probó reload con context.setOffline(true) y atlas SHA verificado. Delimitar PARTIAL si esto requiere fase M05-C.
- Mantener 16 viewports responsive: 320x568,390x844,844x390,834x1194,1280x800,1536x960,1920x1080 como matriz mínima de E2E real GPU; teclado/safe areas/Stage Manager y paneles. No asumir Safari iPhone por Playwright Windows.
- Rendimiento en reposo con rAF on demand, resize/gesture sin recrear GPU, M04 memory estimates sin anunciar VRAM física, pruebas de 50+ swaps sin fuga injustificada.

6. QA Y ENTREGABLES, SIN PASS FICTICIO

Reejecutar npm test/build, cargo fmt/clippy/test/wasm check, M04 streaming+hardening+scheduler, M05-A QA, nuevas pruebas E2E React con WebGPU/WebGL2; negar PASS si escena sólo usa Canvas 2D. Guardar captura GPU REAL por backend y las dos variantes de tema en un directorio local EXCLUIDO de Git; comprobar que .gitignore lo excluye. No publicar binarios, capturas de Z-Anatomy ni archivos originales.
Nuevo test negativo: no hay GLB / hash inválido => FAIL honesto, no fallback a silueta dibujada.
Archivos requeridos:
- docs/M05B_IMPLEMENTATION_RESULT.md
- docs/ADR_008_VIEWER_CANVAS_AND_ASSET_PROVIDER.md
- docs/ADR_009_CAMERA_GIZMO_CONTRACT.md
- docs/M05B_STUDIO_GRAPHITE_PALETTE.md
- reports/implementation/M05B/gate-results.json (gates B1–B5 PASS/FAIL/PARTIAL/BLOCKED/NOT_RUN)
- reports/implementation/M05B/visual-audit.json
- Tests E2E reproducibles en tools/test_m05b_*.py y Rust/React.
- README viewer con comando exacto para iniciar el viewer REAL en puerto 3000 y forzar cada backend para validar.
- Tabla en español: primera imagen 3D en ambos backends, selección real, gizmo real, light Studio, tests exactos, código de salida, riesgo de licencias y git status.

Veredicto PASS_M05B_LOCAL_ONLY sólo cuando B1 3D real, B2 acciones reales, B3 gizmo real y B4 Studio Graphite estén verificados. Si existe 3D pero parte pendiente, PARTIAL. Si continúa la silueta 2D, FAIL. No despliegue ni commit/push/merge sin autorización.

EJECUTA LOS CAMBIOS REALMENTE. PRIORIDAD ABSOLUTA: SUSTITUIR LA SILUETA 2D POR PELVIS ANATÓMICA 3D REAL EN REACT, CON CAPTURAS DE WEBGPU Y WEBGL2, ANTES DE TODO LO DEMÁS.