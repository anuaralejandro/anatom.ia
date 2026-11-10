# ANATOM.IA — PROMPT 06 PARA ANTIGRAVITY
## M05-A.1 QA CLOSEOUT: CORRECCIONES DEMOSTRADAS ANTES DE M05-B

Rol: Staff Frontend/Accessibility/Canvas Performance Engineer con conocimiento Rust WASM.
Workspace: C:\Users\datam\Documents\anatom.ia
Objetivo: resolver los defectos reproducibles F08–F15 de la auditoría independiente de M05-A, SIN conectar todavía el atlas Rust/GLB ni cambiar el diseño aprobado.

## 0. Preflight obligatorio
Leer completos:
- docs/AUDITORIA_IMPLEMENTACION_05A_INDEPENDIENTE.md (FUENTE PRINCIPAL DE HALLAZGOS)
- reports/audit/m05a-independent-browser.json y tools/audit_m05a_independent.py
- docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md
- docs/13_M05_WIREFRAME_REVIEW.md y docs/m05-wireframes/gallery.html
- docs/14_M05_D1_INTEGRATION_CONTRACT.md y docs/15_M05B_INTEGRATION_PLAN.md
- apps/viewer/src/components/layout/{ViewerStage,AppShell,TopBar,AnatomySheet,OverlayHost,InspectorPanel,ExplorerPanel}.tsx
- apps/viewer/src/components/controls/CameraToolbar.tsx
- apps/viewer/src/store/useUIStore.ts, runtime/AtlasRuntimeClient.ts, data/canonicalCatalog.ts
- apps/viewer/src/styles/*, tools/gen_catalog_ts.py, tools/test_m05a_react_suite.py
- reports/implementation/M05A/gate-results.json

Ejecútalos antes de editar: git status --short --branch, git diff --stat, git diff --check, npm test, npm run build, python tools/test_m05a_react_suite.py, cargo test --workspace, los tests de streaming M04. Hay modificaciones locales preexistentes M03–M05A sin commit: preservarlas. No reset, clean, stash destructivo, rebase, commit, push, merge o deploy. No tocar fuentes Z-Anatomy, GLB, shaders ni backend salvo tests de integración no invasivos.

## F08 P0 — VEREDICTO HONESTO DEL QA AGGREGATOR
El JSON real tiene color_contract_pass=false pero verdict=PASS. Corregir el runner para que cualquier test obligatorio que falla o no se ejecuta termine FAIL/PARTIAL, escriba razones y devuelva exit code !=0. Integrar assertions de interacciones/colores de verdad, no sólo viewport.
La antigua banda porcentual 75–90% de oscuro contradice el diseño más negro aprobado y la captura real 95.3%. Documentar una nueva regla coherente con D0: exigir dominancia oscura mínima, no un máximo arbitrario; validar de forma independiente que tokens son #05080D, #03060B, #0B111C y acento #58B9FF, no turquesa. Si el usuario no confirmó otra cota cromática, usar mínimo >=75%, sin máximo; justificarlo en ADR/reporte, NO manipular conteo de píxeles.
Escribir test negativo que haga fallar el runner cuando falta un control/overflow/contraste aunque los 16 viewports estén correctos. No usar PASS por default.

## F09 P1 — ELIMINAR LOOP INFINITO DEL PREVIEW 2D
En ViewerStage.tsx, requestAnimationFrame(render) se reprograma en cada frame sin límite, incluso en reposo. Prueba independiente: 110 callbacks en 750ms con prefers-reduced-motion:reduce.
Solución preferida: preview 2D estático/draw on demand mediante ResizeObserver, theme y selección, con requestAnimationFrame sólo para batch de repintado y cancel al desmontar. Si se conserva una microanimación opcional, no funcionar en reduced-motion, hidden/background ni idle y no producir un loop perpetuo. Mantener esquema conceptual y color Modern Sky Blue.
Tests instrumentados con contador rAF: tras estabilizar la página, <=3 callbacks de la preview en 750ms sin interacción en prefers-reduced-motion=reduce y en reposo; al resize o cambiar tema se repinta una vez o de forma acotada; cero callbacks tras unmount. No recrear canvas ni device por click en panel.
NO sustituir el placeholder por modelos médicos ni motor 3D todavía.

## F10 P1 — HITBOXES Y MOBILE HEADER
En 390x844 touch simulado, controles de TopBar miden 44x36 CSS px y algunos botones internos miden 28x28 / 32x32. Objetivo de producto: todos los targets críticos touch/coarse >=44x44, incluidos cerrar drawer, sheet, toolbar y chips. Evitar style inline que sobreescriba CSS; hitbox puede ser >=44 sin agrandar glifo.
Inspeccionar 320x568,360x640,390x844,430x932,844x390,834x1194 y landscape corto. El header móvil actualmente está demasiado denso; separar breadcrumbs, etiqueta de backend y controles, sin superposiciones ni clics tapados. Mantener formato Obsidian Navy + Modern Sky Blue y no reinventar composición.
Tests automatizados bounding boxes de elementos interactivos visiblemente relevantes, sin box intersecciones, contraste AA y scroll horizontal.

## F11 P1 — DRAWER SEMÁNTICO / FOCUS TRAP
OverlayHost.tsx sólo agrega listener Escape. Crear diálogo modal (o drawer accesible bajo patrón normativo) con foco inicial razonable, Tab/Shift+Tab dentro del drawer, backdrop, Escape y restauración del elemento iniciador; usar inert y aria-modal/role correctamente, sin bloquear teclado del propio drawer ni crear foco zombie.
Sin doble overlay en tablet, y en móvil el sheet con handle debe ser un botón accesible a teclado (no div onClick exclusivamente), sin robar gestos al canvas.
Prueba Playwright: abrir mediante teclado, focus dentro, 20 tabs o Shift+Tab no dejan el drawer; Escape cierra y devuelve foco al botón; repetir 10 veces sin listeners acumulados; overlay fondo no enfocable mientras modal. No interceptar clicks externos de forma que invaliden el focus restore.

## F12 P1 — VERACIDAD SOBRE CANVAS Y ACCIONES 3D
El viewer M05-A NO inicializa wgpu: canvas.getContext('2d') está activo, pero TopBar expone badge WEBGPU con estilo LIVE. No volver a mostrar WebGPU/WebGL2 como backend activo hasta recibir capabilities del AtlasEngine real. Mostrar estado honesto DEMO / VISTA CONCEPTUAL.
CameraToolbar botones reset/presets/focus actualmente no alteran cámara y Aislar/Ocultar solo cambia store, no geometría. En M05-A distinguir controles demo: deshabilitar acciones de motor no implementadas con texto visible/aria-disabled y explicación breve, o simular acciones en preview coherente y etiquetarlas DEMO. No dar feedback engañoso de operación 3D real.
Establecer contrato de transición al motor real M05-B sin clases duplicadas de canvas ni falsa readiness; tests para que no aparezca LIVE WebGPU en modo conceptual y que botones sin implementación estén disabled.

## F13 P2 — REGLAS RESPONSIVE POR ALTURA
AppShell determina layout por ancho e ignora altura corta en 844x390 (clasifica tablet y mantiene rail 56px). Contrato D0 exige degradar a compact-wide cuando altura <500 (excepto ancho <600, compact), con stage accesible y controles mínimos. Workstation requiere stage >=640 y pro-wide >=720 altura >=650. Sin user-agent.
Centralizar la política layout de anchura + altura, coherente CSS/JS, preservar tema y selección durante resize. Tests: 844x390,1024x480,1280x520,1536x620,320x568,834x1194 y StageManager 600x800.

## F14 P1 — TAXONOMÍA NO VALIDADA
tools/gen_catalog_ts.py clasifica por substrings de nombres en español; por eso "Sínfisis púbica" termina organ. No afirmar que sistema/categoría clínica está verificado solo por terminología TA2. Separar campos de fuente inmutable: AnatomyId, TA2, labels y side del catálogo, y metadata editorial curada/documentada. Hasta disponer de taxonomía validada, usar "Sin clasificar"/filtro seguro o crear mapping explícito revisable con evidencia por ID; prohibido inventar datos clínicos. No editar originales GLB/catalog fuente y no prometer órganos inexistentes. Tests 26/26 IDs contra catálogo y cero etiquetas clínicas incorrectamente inferidas. Revisar duplicados bilaterales por ID correcto, no por label.

## F15 P2 — EXTENDER QA Y DOCUMENTACIÓN
- React unit/browser tests, CSS assertions semánticas y visuales, focus trap, hit targets, 200% zoom, reduced-motion rAF, app-stage y consola.
- Reproducciones reales con Chrome Windows y especificar hardware. No afirmar iOS/iPad/Safari/Android físico PASS por emulación.
- npm test, npm run build, npm audit (distinguir prod/dev), cargo fmt/clippy/test/wasm check, streaming M04, 16 viewports, scheduler independent y memory preflight sin regresión.
- Compare screenshots desktop 1536x960, MacBook 1280x800, iPad 834x1194 e iPhone 390x844 contra D0 previamente aprobado; no modificar docs/m05-wireframes para ocultar diferencias.
- Mantener app en http://127.0.0.1:3000/ disponible para revisión visual; si servidor no está activo, indicar npm run dev desde apps/viewer y verificar HTTP 200.
- Cualquier hallazgo no resuelto => PARTIAL con causa, no declarar cierre total.

## Entregables
- Código de M05-A corregido, sin tocar M05-B Rust/GLB ni crear React runtime final aún.
- docs/M05A_QA_CLOSEOUT_RESULT.md y ADR si cambia la taxonomía/contrato.
- reports/implementation/M05A-QA/independent-regressions.json, touch-targets.json, focus-lifecycle.json, animation-idle.json, verified-color-gates.json y comparativa visual.
- Scripts reproducibles; actualizar docs/M05A_IMPLEMENTATION_RESULT.md con enlace a la auditoría y estado, sin reescribirla como si no hubiera fallos.
- Mantener docs/AUDITORIA_IMPLEMENTACION_05A_INDEPENDIENTE.md sin alterarla (evidencia histórica).
- Al terminar en español: PASS/FAIL/BLOCKED exactos por F08–F15, test counts, URLs locales y Git status, riesgos M05-B que permanecen.

**EJECUTA LOS ARREGLOS REALMENTE. NO IMPLEMENTAR M05-B NI HACER COMMIT/PUSH/MERGE/DEPLOY.**
