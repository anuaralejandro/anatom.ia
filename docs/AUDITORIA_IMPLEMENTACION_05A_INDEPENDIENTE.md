# anatom.ia — Auditoría independiente de M05-A
Fecha de revisión: 2026-11-10. Rama local: feature/m04-runtime-streaming. HEAD observado: be654ca.
**Veredicto: PARTIAL_PASS — GO_M05A_QA_CLOSEOUT; NO-GO a implementación M05-B hasta cerrar los hallazgos P0/P1 y aprobar visualmente la app real.**
La revisión no modificó código de producción, no hizo commit, push ni despliegue.

## Reproducciones y evidencia
- npm test en apps/viewer: 13/13 PASS.
- npm run build: PASS, bundle CSS ~15.93 kB y JS ~174.31 kB sin comprimir (no constituye presupuesto final de runtime GPU).
- npm audit --omit=dev --audit-level=high: 0 vulnerabilidades del conjunto de producción evaluado (no confundir con todas las dependencias).
- cargo fmt, clippy y cargo test --workspace: PASS; compilación wasm32 PASS. Reporte Antigravity: 39 tests Rust.
- python tools/audit_m04h_scheduler.py y test_m04h_hardening.py ejecutados durante esta auditoría: PASS/previos, con limitaciones de DeviceLost físico.
- python tools/test_m05a_react_suite.py: 16/16 viewports sin overflow y con stage positivo, interacciones básicas PASS.
- Browser real Chrome headless + Vite dev local en http://127.0.0.1:3000/: HTTP 200. Script independiente tools/audit_m05a_independent.py; resultados reports/audit/m05a-independent-browser.json.
- Capturas inspeccionadas: desktop 1536x960, iPad 834x1194, iPhone 390x844; el diseño obscuro y acento azul cielo están aplicados.
- Fuente upstream Z-Anatomy sin modificaciones; no hay despliegue de assets.

## Defectos de evidencia y usabilidad

**F08 · P0 · falso PASS del agregador de pruebas.**
El reporte reports/implementation/M05A/gate-results.json contiene visual_audit.color_contract_pass=false pero verdict=PASS. tools/test_m05a_react_suite.py fija verdict=PASS y sólo lo cambia en viewport, no agrega resultados de interacciones ni color. El criterio actual fija banda oscura 75–90%, pero la captura mide 95.3%; el propietario aprobó estética más negra. Se debe determinar criterio cromático aprobado y hacer que fallo en CUALQUIER gate obligatorio haga retornar nonzero y FAIL/PARTIAL de forma honesta. No maquillar estadísticas.

**F09 · P1 · render permanente de demo incluso en reposo y reduced motion.**
ViewerStage.tsx crea requestAnimationFrame recursivo sin gate de visibilidad, actividad ni prefers-reduced-motion. Auditado en Chrome con prefers-reduced-motion:reduce: 110 callbacks de rAF en 750 ms, aún sin interacción. Infringe la regla de render-on-demand y consume batería innecesariamente en móvil. Para M05-A debe convertir figura conceptual a dibujo on-demand (theme/resize/selección) o CSS/SVG estático; si se decide animación, detenerla al entrar en hidden/idle y reduced motion, sin alterar el motor Rust.

**F10 · P1 · controles móviles fuera del objetivo táctil.**
En emulación 390x844 touch/coarse, botones de topbar midieron 44 × 36 CSSpx (objetivo 44×44). Hay overrides inline minHeight=36 y otros controles con 28/32/36 px. Inspeccionar todos en modo coarse y corregir hitbox real, NO sólo el icono. Chrome emulation no certifica iPhone físico.

**F11 · P1 · focus management de drawers incompleto.**
OverlayHost solo escucha Escape; no establece focus inicial, focus trap ni dialog/inert correcto. Tras 12 tabs el foco sale del drawer en test independiente. openOverlay a menudo no recibe returnTarget, por lo que closeOverlay no restaura foco. Implementar semántica correcta de drawer modal, keyboard, backdrop y teardown; probar Tab/Shift+Tab/Escape, focus restore y click fuera.

**F12 · P1 · estado GPU engañoso y botones sin efecto real.**
En un canvas.getContext('2d') no nulo y canvas.getContext('webgpu') no disponible, el header muestra badge LIVE "WEBGPU" aunque el viewer M05-A no inicializa wgpu. CameraToolbar tiene onResetCamera vacío, onPreset solo console.info y onFocus re-selecciona estructura; inspector Aislar/Ocultar cambia SOLO store UI aunque la figura 2D queda igual. Diferenciar modo DEMO/preview, deshabilitar comandos de motor pendientes (sin fake éxito), o hacer demo explícita que altere una representación de prueba consistente, no nomenclatura de estado real. El estado de UI no debe anunciar 3D operativo hasta M05-B.

**F13 · P2 · guardas responsive por altura no aplicadas.**
AppShell clasifica 844×390 como tablet sin degradación a compact-wide, aun cuando el contrato D0 de altura <500 exige composición de emergencia; ocupa rail de 56px y stage 788×342. Workstation tampoco comprueba stage mínimo 640 ante cambios contextuales. Aplicar una sola política responsive por viewport CSS real + altura y tests de landscape corto, Stage Manager y zoom.

**F14 · P1 · taxonomía anatómica heurística sin validación.**
tools/gen_catalog_ts.py infiere categorías mediante substrings españolas; p.ej. "Sínfisis púbica" se clasifica "organ" porque no contiene Hueso/Ligamento/Músculo. Categorías, sistemas y relaciones anatómicas NO proceden de campos certificados del catalog.json actual. Mantener nombres e IDs exactos TA2; evitar declarar curación clínica del sistema/categoría. Usar metadatos validados con fuente y revisión, o categoría "Sin clasificar" temporal; no incorporar inferencias heurísticas al inspector como hechos clínicos.

**F15 · P2 · instrumento de QA limitado.**
tools/test_m05a_react_suite.py solo comprueba stage >0, scroll horizontal, cambios de texto y Escape; no comprueba objetivos táctiles, screen reader, 200% zoom, modal trap, presupuesto de animación, uso de canvas o layout correcto por altura. Revisar tooling y la matriz de hardware físico NOT_RUN. No confundir 16/16 con cumplimiento universal Apple/Android.

## Resultado por área
| Área | Resultado |
|---|---|
| React estructura y build | PASS local |
| 13 unit tests React, 39 Rust reportados | PASS local |
| Tipos bridge preliminares y diseño CSS dark/blue | PASS parcial, integración no probada |
| 16 viewports sin overflow horizontal | PASS limitado |
| Drawer/modal accesible, objetivos touch | FAIL / parcial |
| Eficiencia preview idle y reduced-motion | FAIL |
| Indicadores de backend y acciones reales | FAIL / mock engañoso |
| Taxonomía clínica validada | NOT_VALIDATED |
| M05-B integración glTF/WebGPU | NOT_IMPLEMENTED (correcto por fase) |
| Safari iOS/iPadOS, Android físico, macOS Safari | NOT_RUN |
| Distribución assets comercial/clinical | BLOCKED |

## Decisión
El usuario puede abrir React ahora en http://127.0.0.1:3000/ y aprobar/rechazar distribución visual. Antes de crear prompt M05-B, hacer una corrida correctiva **M05-A QA Closeout**, preservar visual aprobado Obsidian Navy/Modern Sky Blue y no modificar motor 3D salvo tests estrictamente necesarios. Volver a auditar; si pasa, preparar e implementar M05-B en una nueva corrida separada.
