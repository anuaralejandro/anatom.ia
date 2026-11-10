# anatom.ia — M05 · Revisión de wireframes D0

**Estado:** D0 WIREFRAMES APROBADOS POR EL PROPIETARIO; quedan D1 e implementación M05-A sujetas a gates F01–F03. No existe integración anatómica React M05-B todavía.
**Fecha:** 2026-11-09.
**Referencias:** \`11_M05_PLAN_UX_ARQUITECTURA_V0.md\`, \`12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md\`.
**Contenido:** prototipo standalone sin React, WASM, wgpu, red ni assets Z-Anatomy. La ilustración SVG es original, esquemática y NO clínicamente exacta.

## Revisar localmente
Abrir directamente:
- \`docs/m05-wireframes/gallery.html\`: galería comparativa de los estados renderizados.
- \`docs/m05-wireframes/index.html\`: prototipo de diseño responsive; cambiar tamaño de ventana.
- \`docs/m05-wireframes/review/design-review-results.json\`: medidas automatizadas y resultados.
- \`docs/m05-wireframes/README.md\`: parámetros de revisión.

No requiere npm install, servidor ni conexión. No es un replacement para el visor real.

## Cuatro composiciones principales, verificadas en Chromium

| Captura | Layout CSS | Geometría visible | Decisión |
|---|---|---|---|
| Desktop 1536×960 | pro-wide | Rail 64 + explorador 296 + canvas 832 + inspector 344; altura canvas 900 | Tres paneles permanentes |
| MacBook 1280×800 | workstation | Rail 56 + explorador 296 + canvas 928; altura 740 | Inspector temporal |
| iPad 834×1194 vertical | compact-wide | Canvas completo 834 × 1138; paneles overlay exclusivos | Sin barras laterales permanentes |
| iPhone 390×844 | compact | Canvas 390 × 792 detrás de sheet; topbar 52; sheet plegado | Canvas dominante + ficha inferior |

Las cifras son dimensiones verificadas en Chrome headless Windows con DPR=1. No describen tamaños físicos de iPhone/iPad ni pixeles retina. Los límites de iPad Stage Manager dependen de ventana real.

## Arquitectura visual (D0)

**Topbar:** anatom.ia mark, ubicación, búsqueda, theme/status; en compact se oculta ruido de navegación y se prioriza acceso a explorar.

**Rail:** una sola columna de navegación utilitaria, no sidebar decorativo. Sólo desktop.

**Explorador:** selector de región, búsqueda, árbol por sistemas/lateralidad y visibilidad. El mock muestra ocho entradas ilustrativas de un catálogo objetivo de 26. No implica validación médica de nombres o grupos.

**Stage 3D:** ocupa todo el espacio, fondo técnico y controles discretos. El SVG central NO es anatomía clínica. Las etiquetas flotantes son patrón de diseño; el motor real deberá calcular posición proyectada si algún día se habilitan labels sobre superficies.

**Inspector:** ficha de órgano seleccionable, nomenclatura ES/EN/LA, ID terminológico, acciones Enfocar/Aislar/Ocultar. Texto actual es prototipo; en producción se obtiene exclusivamente de un catálogo validado.

**Móvil:** un único sheet de contenido alternable, colapsado (~110 px), medio (~52% alto), expandido (~86%). No se montan dos overlays simultáneos. Teclado virtual y safe areas definitivas pendientes de validación física.

**Estados:** seleccionado, sin selección, loading, error GPU y modo claro. En estado de error el diseño presenta acción explicativa y nunca deja pantalla negra silenciosa.

## QA ejecutada

\`python docs/m05-wireframes/review_wireframes.py\`: **12/12 composiciones de viewport PASS**, layout esperado, no overflow horizontal, canvas no colapsado, paneles permanentes sólo cuando caben y sin errores de JavaScript. Se guardaron capturas para desktop, MacBook, iPad portrait/landscape, iPhone portrait/landscape y temas/estados. Son pruebas geométricas, no certificación de accesibilidad o performance en hardware físico.

El prototipo de diseño pasó además **9/9 pruebas interactivas** del script `docs/m05-wireframes/review_interactions.py`: selección del árbol, búsqueda con filtro, tema, apertura/cierre de inspector en laptop, `Escape`, explorador móvil, selección desde sheet y expansión. Evidencia en `docs/m05-wireframes/review/interactions-results.json`.

Se deben añadir pruebas de accesibilidad nativas y de integración real en M05: keyboard focus sistemático, VoiceOver, TalkBack, pinch/pan sobre motor, safe areas, teclado virtual, scroll de sheet y contrastes con superficie real.

## Decisiones que faltan para congelar el diseño

1. Aprobar visualmente composición general, densidad y paleta (Clinical Precision / Midnight).
2. Aprobar cantidad de controles siempre visibles y ubicación de navegación por cámara.
3. Aprobar comportamiento del inspector en laptop e iPad, y niveles del sheet móvil.
4. Elegir si el enfoque editorial de anatomía será sólo ficha terminológica o tendrá contenido anatómico clínico validado en una fase posterior (sin inventarlo en M05).
5. Resolver pendientes M04-H: cancelación de fetch coalesced, 404 sin reintentos, memoria real WASM; sin eso no congelar API React.

**No crear todavía PROMPT M05 de implementación**, hacer push, commit o modificar \`apps/probe-web/\`, Rust, shaders ni fuentes. El paso siguiente es revisión visual de estos wireframes y ajustes D0→D1.
