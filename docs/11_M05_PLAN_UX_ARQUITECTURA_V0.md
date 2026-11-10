# anatom.ia — Fase M05: plan maestro de experiencia 3D / Diseño v0.1 (NO IMPLEMENTADO)

**Estado:** borrador de arquitectura producto y UX para revisión; ninguna implementación React autorizada todavía. Basado en contrato real Rust↔WASM v1.1 de M04-H, catálogo TA2 de 26 piezas de pelvis masculina y capacidad WebGPU/WebGL2. Referir `docs/AUDITORIA_IMPLEMENTACION_04H.md` para dependencias pendientes.

**Contrato responsive obligatorio:** `docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md` (v1.0, 271 líneas), fuente normativa para estilos, layouts adaptables, safe areas, accesibilidad y QA multiplataforma. Sus breakpoints prevalecen sobre los intervalos orientativos de este documento.

## 1. Tesis de producto

Atlas anatómico 3D clínico y educativo: *modelo en primer plano, datos clínico-anatómicos confiables y controles discretos*. Diseño enterprise-grade = consistencia, precisión anatómica, accesibilidad, fluidez, navegación y estados de error; NO llenarlo de efectos glass/blur, skeuomorphism, controles vistosos o dashboards de KPIs ajenos a un atlas.

**Tres experiencias**, sobre un solo motor:
1. **Explorar:** navegar estructura/órgano/sistema/región, capas visibles y anatomía circundante.
2. **Enfocar:** selección, centro de cámara, aislar/ocultar, inspección de metadatos multilingües y relación con piezas vecinas.
3. **Estudiar:** recorrido guiado *sólo con contenido anatómico auditado*. La fase 5 puede preparar el patrón de panel, pero no inventar texto clínico, exámenes, imágenes o explicaciones; su contenido editorial se integra después.

## 2. Arquitectura de información v1

- Navegación superior compacta: logotipo anatom.ia, breadcrumb `Atlas / Pelvis / Masculino`, región, variante **sólo si existe asset**, búsqueda global, ayuda y perfil visual.
- Explorador de anatomía (izquierda): buscador tolerante a acentos con alias TA2 catalogados, filtros por sistemas, lateralidad y visibilidad, árbol virtualizable cuando el atlas crezca.
- Canvas 3D principal: ocupa todo espacio disponible, sin tarjetas que lo constriñan, interacción mouse/touch; toolbar flotante mínima: reset camera, foco, anterior/posterior/lateral, aislamiento, layers, screenshot **solo si permitido por licencia**.
- Inspector contextual (derecha o bottom sheet): nombre anatómico ES + término EN/LA, ID TA2, laterality, acciones `Enfocar`, `Aislar`, `Ocultar`, `Mostrar todas`; contenido clínico adicional únicamente si validado.
- Estado persistente de UI: panel abierto, tema, idioma y preferencia de calidad; NO duplicar transforms/scene objects ni persistir sin versionar references de atlas.
- Vistas vacías: sin selección, loading, offline, asset corrupt, region unavailable, GPU fallback, memoria limitada, sin permisos; mensajes con acción útil y sin pantalla negra.

## 3. Sistema de layouts responsive (valores iniciales a validar)

| Viewport | Estructura |
|---|---|
| >=1440 desktop ancho | rail izquierdo 60-68px + explorador 284-320px + canvas flexible + inspector 328-380px; paneles retraíbles |
| 1024–1439 laptop | explorador 260-300px + canvas flexible; inspector en drawer no obstructivo |
| 768–1023 tablet | canvas dominante, rail de herramientas, explorador/inspector como overlays alternantes |
| <768 móvil | canvas continuo fullscreen; topbar compacta, herramientas de cámara accesibles, bottom sheet con alturas 20/55/85% de viewport, safe-area-insets |

- Animación de paneles CSS `transform/opacity` con duración moderada, desactivar con `prefers-reduced-motion`.
- La cámara no debe reorientarse arbitrariamente cuando aparece/desaparece panel: viewport resize estable, preservar focus/selection y ajustar canvas DPR adaptativamente.
- Targets táctiles diseñados >=44×44 CSS px, teclado completo, focus visible, contraste WCAG 2.2 AA y labels screen reader.
- No usar rAF React para GPU: Rust controla cámara/scene y render; React se actualiza sólo por eventos/snapshots con revisión.

## 4. Dirección visual preliminar: **Clinical Precision / Midnight**

Paleta conceptual:
- Background dark #070E17, dark elevated #101C2A, outline #273748, foreground #EAF3F7.
- Acento clínico azul cielo #58B9FF (hover #7AC8FF, strong #2E9CFF) para selección/control, azul navegación #7FB8FF, ámbar suave #F2AC67 para avisos no críticos.
- Light: fondo #F5F8FA, panel #FFFFFF, texto #162736, borde #DCE5EC.
- Colores reales de órganos separados de la UI; no recolorear mallas por tema.
- Tipografía de interfaz técnica legible (ej. Inter u otra libre y legalmente embebible), números tabulares, tamaños 12-16 para metadata, 18-24 para títulos locales.
- Material visual premium de bajo costo: superficies planas, borde de 1px, blur casi inexistente en móviles, sombras mínimas, espaciado 4/8px, esquinas 10-16px.
- Prohibido gamificar información clínica o introducir efectos que reduzcan silueta y contraste anatómico.

## 5. Contratos funcionales

**Actuales verificables:** load region/LOD, selectAt, focus, setVisibility, isolate, reset, 3 presets de cámara, scene snapshot, backend WebGPU/WebGL2, cambio quality profile, modo offline tras primer arranque, estado y memoria estimada.

**Necesitan diseño o implementación de motor posterior:** clipping plane/sección, transparencia por órgano, labels 3D fijados sobre superficies, exploded view, mediciones, animaciones de disección, relación clínica, variantes femeninas, cuerpo entero. No dibujar controles activos ni prometer estas funciones en M05 MVP.

**Estado único:** `AtlasEngine` Rust: mallas, camera, selection, visibility, lifecycle; `AssetStreamManager`: network/cache/generation; React: UI shell, overlays, search text, preferencias de tema. Contrato con tipos TypeScript generados de la API real, no typings ficticios. React no recibe arrays GPU ni mantiene 'Scene' duplicada.

**Entregables esperados:** React+TypeScript `apps/viewer`, design tokens, componentes accesibles de layout, filtros/búsqueda, inspector y toolbars, adaptadores bridge tipados, gestión errores, rutas estáticas, PWA con política offline versionada; NO backend dinámico ni funcionalidades no habilitadas.

## 6. Secuencia M05, todavía sin prompts

**D0 — Validación del diseño:** wireframes estáticos desktop/tablet/mobile de tres estados clave; flujo Figma-equivalente o CSS storybook; contraste, tipografía y densidad clínica.

**D1 — Contrato de integración:** resolver gaps M04-H P0 (coalesced abort, retry 404, verificación budget en browser), tipar API y eventos, lifecycle del canvas al desmontar y cambiar backend, control de errores.

**D2 — Shell React:** layout base, temas, responsive, accesibilidad, paneles y canvas; usar fixture sintético para evitar licencias en capturas públicas.

**D3 — Exploración anatómica:** catálogo TA2, búsqueda, filtros, selección cruzada canvas/lista, inspector, focus/isolate/visibility, presets cámara y estados vacíos.

**D4 — Calidad/offline:** PWA y Service Worker sin dos implementaciones contradictorias, rendimiento móvil real, tests de gestos, teclado, uso con una mano, render idle, safe areas.

**D5 — QA UX transversal:** visual regression de tamaños 360/390/768/1024/1440/1920, WebGPU/WebGL2, light/dark, teclado, accesibilidad, fallas GPU/Red/SHA/offline; primera carga/warm-load, no layout shift perceptible, selección y cámara persistentes en drawer.

## 7. Entregables antes de prompt de Antigravity
1. Design system v1: tokens, reglas de uso, estados, superficie/material y tipografía.
2. Wireframes concretos de las tres resoluciones, interactivos o estáticos, aprobados visualmente.
3. Mapa de componentes/UI state y tabla de eventos contractuales con Rust.
4. Historias de usuario y acceptance criteria por modo/caso.
5. Test plan de regresión y restricciones legales; no subir capturas de Z-Anatomy al repo público antes de resolver licencias.

**Decisión de esta etapa:** autorizar planificación y prototipos visuales NO conectados a motor si se necesitan. No iniciar React definitivo ni generar prompt M05 sin acuerdo de diseño + cierre o aceptación explícita de riesgos M04-H.
