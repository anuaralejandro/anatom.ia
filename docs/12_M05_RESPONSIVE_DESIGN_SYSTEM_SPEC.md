# anatom.ia — M05 RESPONSIVE DESIGN SYSTEM CONTRACT v1.0
**Estado:** especificación normativa de diseño; NO es prompt de implementación. 2026-11-09.
**Ámbito:** navegador y PWA en iPhone iOS/Safari, iPadOS/iPad multitarea, macOS Safari/Chrome, Android Chrome/Samsung Internet/Firefox, Windows Chrome/Edge; pointer mouse/trackpad/touch/pen, teclado, tamaños de letra y zoom.
**Basado en:** `docs/11_M05_PLAN_UX_ARQUITECTURA_V0.md`, `docs/M04_RUNTIME_BRIDGE_CONTRACT.md`, `docs/AUDITORIA_IMPLEMENTACION_04H.md`.
**Prioridades:** anatomía > legibilidad > accesibilidad > fluidez > densidad informativa > efectos visuales.
**IMPORTANTE:** no crear React, ni UI, ni modificar Rust/GLB/WASM todavía. Especificación para aprobación previa al prompt de Antigravity.

## 0. DEFINICIÓN DE CALIDAD ACEPTABLE

Un layout es válido si y solo si:
1. Se ajusta al ancho y ALTO CSS disponibles, incluyendo split screen, zoom y teclado virtual; nunca usar User-Agent "iPhone/iPad/Mac/Android" para determinar la composición.
2. El canvas anatómico conserva máxima superficie útil, no desaparece al abrir paneles y mantiene el mismo Engine Rust durante redimensionamientos.
3. En cada breakpoint hay UNA sola estrategia definida para explorador e inspector (fijos, drawer o sheet); jamás dos paneles flotantes simultáneos tapando la anatomía en móvil.
4. Controles interactivos visibles, accesibles, con hit area >=44×44 CSS px en touch/coarse; >=36×36 escritorio por convención de producto (mínimo normativo WCAG 2.2 AA =24×24 o excepción de separación).
5. Todo modal, drawer y sheet se puede cerrar por control visible, Escape cuando existe teclado y comportamiento gestual cuando procede.
6. No hay desplazamiento horizontal de la aplicación, ni clipping de controles por notch/Dynamic Island/home indicator/curvas, ni superposición con teclado al buscar.
7. El modo dark/light y los estados offline/loading/error no cambian geometría anatómica, selección, cámara ni identidad TA2.
8. Prohibido maquillar funciones no disponibles (corte, transparencia avanzada, medidas, modelo femenino) como botones funcionales.

## 1. BREAKPOINTS NORMATIVOS — NO ENTRADAS DE MARCA

La regla primaria es el ancho del layout viewport/ventana en CSS px (NO screen.width ni resolución nativa). La altura, capacidades del puntero y los contenedores activan modificaciones adicionales.

| Rango de ancho | Nombre interno | Composición horizontal |
|---|---|---|
| 320–599 | compact | Canvas + header + toolbar flotante; panel de información como bottom sheet; explorador como vista dentro del mismo sheet/drawer |
| 600–839 | compact-wide | Canvas predominante; explorador/inspector como overlays MUTUAMENTE EXCLUSIVOS; footer simple |
| 840–1119 | tablet | canvas principal + rail de 56px opcional; explorador e inspector como drawers temporales, nunca fijos en pareja |
| 1120–1535 | workstation | rail 56px + explorador 280–304px fijo; inspector como drawer overlay o panel popover; canvas resto |
| >=1536 | pro-wide | rail 64px + explorador 288–304px + canvas minmax(0,1fr) + inspector 328–368px fijo |

**Restricción vertical y de canvas:** pro-wide sólo si el espacio resultante del canvas >=720px y altura útil >=650px; si no, degradar a workstation. workstation exige canvas >=640px; si no, degradar a tablet. tablet exige canvas >=540px; si no, compact-wide. Implementar una sola fuente de decisión, con CSS media queries + ResizeObserver del workspace; no dos fuentes de verdad CSS/JS peleando por el layout.

**Densidad de diseño:** en cualquiera de las composiciones, el canvas tiene min-width:0 y min-height:0; la cuadrícula se contrae, no desborda. Si una sidebar no cabe, se oculta como panel fijo y se expone por botón visible.

**Altura corta (<650 CSS px):** header base 48px, rail compacto, ocultar controles secundarios bajo overflow, sheets de altura máxima visual usable; cuando <500px canvas sin rail permanente y controles mínimos. Paisaje de teléfonos y iPad Stage Manager son casos prioritarios.

**Zoom 200 % y texto 200 %:** reorganizar en un rango más compacto cuando el viewport CSS se reduzca; nunca anular zoom, truncar texto importante o obligar a scroll horizontal de toda la app.

## 2. GEOMETRÍA DE INTERFAZ Y SISTEMA DE GRID

Workspace de alto completo, NO una card centrada:
- Header desktop: 60px base; tablet: 56px; móvil: 52px; móvil apaisado/altura corta: 48px. Insets del OS se agregan a la zona segura correspondiente; altura real puede exceder altura base.
- Rail vertical desktop: 64px pro-wide, 56px workstation; no usar rail fijo en compact.
- Explorador fijo: ideal 296px, permitidos 280–304px. Scroll independiente del canvas; buscador sticky dentro del panel, acciones de jerarquía no pegadas al borde.
- Inspector fijo: ideal 344px, permitidos 328–368px; nunca inferir información clínica inexistente.
- Separadores de panel: 1px; paneles flotantes: radius 12–16px, offset mínimo 12px de zona segura.
- Canvas: flexibilidad total; al reducir ancho, panel derecho pasa a drawer primero, luego el izquierdo; NO deformar el canvas con CSS transform:scale.
- Zona de cámara: controles agrupados (no botones dispersos por todas las esquinas); gap 8px, a >=16px del borde seguro; no superponer controles críticos con información anatómica seleccionada.
- Breadcrumb: desktop `Atlas / Pelvis / Masculino`; tablet acortar a `Pelvis`; compacto `Pelvis` + icono región; ellipsis con tooltip/título accesible; no truncar ID en inspector.
- En tamaños móviles, una sola capa modal: sheet inspector y drawer explorador son exclusivos; cuando se abre uno, el otro se cierra.
- No usar frameworks UI que añadan padding, scroll global o estilos no controlados. Bootstrap puede coexistir con prefijo `.atlas-` si se usa, pero el layout debe mantener tokens explícitos.

## 3. MÓVIL: BOTTOM SHEETS, ZONAS SEGURAS Y TECLADO

- Sheet colapsado: handle y resumen seleccionado, aproximadamente 88px de contenido + safe-area-inset-bottom; si no hay selección, mostrar acción `Explorar estructuras` sin dejar una barra vacía permanente.
- Sheet medio: altura objetivo ~52% del visual viewport.
- Sheet expandido: máximo min(86% del visual viewport, altura disponible hasta safe top+12px). Solo el cuerpo del sheet hace scroll; header/handle/close sticky.
- Sheet debe ofrecer posiciones discretas, drag con umbrales y decisión por velocidad; no saltos arbitrarios. El scroll de contenidos no debe activar drag cuando el usuario lee la nomenclatura.
- Botones/tabs del sheet >=44px altos; espaciado entre controles 8px; zonas clicables separadas por >=8px si hay riesgo de toque accidental.
- Interacción con teclado virtual (búsqueda): el buscador y resultados permanecen encima del teclado; usar VisualViewport `resize/scroll` para acotar sheets y overlays, sin desmontar canvas ni reabrir contexto GPU; reubicar foco al cerrar.
- Input search en iOS: font-size >=16px para prevenir autozoom indeseado, pero nunca suprimir zoom del usuario; cursor y botón clear accesibles.
- Safe area: `env(safe-area-inset-top/right/bottom/left,0px)`; viewport meta `width=device-width, initial-scale=1, viewport-fit=cover`. No forzar `user-scalable=no`, `maximum-scale=1`.
- iPhone Dynamic Island / notch: header background puede extenderse tras el área segura, pero texto/click targets comienzan DESPUÉS del safe inset.
- Home indicator: el fondo del sheet puede ocupar hasta abajo, pero el contenido operativo termina por encima de safe bottom+12px; controles flotantes inferiores respetan ese espacio.
- Android gesture bar y navegación de tres botones: mismas safe-area rules; comprobar con teclado Gboard abierto, URL bar colapsada/expandida y sistema de gestos.
- Dispositivos plegables/tablet multitarea: usar espacio CSS y, si hace falta, Viewport Segments como mejora progresiva, nunca derivar del modelo del teléfono.

## 4. INPUT MULTIMODAL POR CAPACIDAD, NO POR DISPOSITIVO

| Modalidad | Interacciones canvas | Interacciones UI |
|---|---|---|
| mouse | arrastrar=orbit; secondary drag o tecla+drag=pan; wheel con foco canvas=zoom; click=selección | hover/focus, tooltips no imprescindibles |
| trackpad Mac/Windows | drag=orbit; trackpad scroll según gesto=zoom; pan por modificador/botón; respetar browser gestures | herramientas operables por teclado; no capturar scroll externo |
| touch | un dedo orbit; dos dedos pinch zoom y pan; tap selección; doble tap foco si no interfiere con accesibilidad | bottom sheet y panel scroll nativo; no scroll de página arrastrando canvas |
| stylus/Apple Pencil | tap selección, arrastre orbit, botón secundario cuando exista | misma semántica que pointer; no depender de presión |
| keyboard | tab a canvas, shortcuts publicados reset/focus/orbit/zoom y controles equivalentes | búsqueda, árbol TA2, inspector, cerrar Escape, focus management |
| switch/screen reader | no exigir interacción exclusiva canvas; lista/árbol contiene acciones equivalentes | ARIA labels y anuncios de error/carga |

- `touch-action:none` SOLAMENTE en el canvas 3D de interacción; nunca en body, menús, sheets o contenedores de scroll.
- Preferir Pointer Events con `setPointerCapture` por puntero activo y limpieza de `pointercancel`; manejar múltiples IDs con geometría y estados previsibles.
- CSS `@media (hover:hover) and (pointer:fine)` para hover refinado; `@media (pointer:coarse)` para ampliar zonas táctiles. No bloquear simultaneidad de mouse+táctil en laptops 2-en-1: `any-pointer` complementa, no sustituye la modalidad por evento.
- Controles de cámara siempre disponibles por botón, incluso sin gestos; scroll/wheel no debe bloquear zoom general de página ni atajos de accesibilidad.
- No interferir con navegación del sistema desde bordes de pantalla, Safari browser back, selección de texto o VoiceOver/TalkBack.
- Gestos de sheet nunca se transmiten a picking/orbit 3D bajo overlay.

## 5. DESIGN TOKENS (REFERENCIA OBLIGATORIA)

**Tema oscuro Obsidian Navy (con Modern Sky Blue Accent)** (separado del color real de órganos):
`--bg-app:#05080D`, `--bg-canvas:#03060B`, `--bg-panel:#0B111C`, `--bg-raised:#121C2B`,
`--bg-hover:#19273A`, `--border:#202D40`, `--text-primary:#F0F5FA`, `--text-secondary:#A3B2C5`,
`--accent:#58B9FF`, `--accent-hover:#7AC8FF`, `--accent-strong:#2E9CFF`,
`--accent-soft:rgba(88, 185, 255, 0.14)`, `--nav-accent:#7FB8FF`,
`--warning:#F2AC67`, `--error:#FF7C85`, `--success:#5ED8B0`.

**Tema claro**:
`--bg-app:#F5F8FA`, `--bg-canvas:#E9F0F3`, `--bg-panel:#FFFFFF`, `--bg-raised:#EDF3F6`,
`--bg-hover:#E1E9EF`, `--border:#DCE5EC`, `--text-primary:#162736`, `--text-secondary:#455B6A`,
`--accent:#087A7A`, `--nav-accent:#3157C8`, `--warning:#915315`, `--error:#B42B40`.

Verificar contraste contra superficies REALES: texto normal >=4.5:1, grande >=3:1, controles/iconos relevantes >=3:1. No asumir que hexadecimal bonito = contraste conforme. Selección no se indica únicamente por turquesa: acompañar con contorno, estado, icono/texto. Conservación de color anatómico: cambiar tema altera superficies UI/iluminación de entorno solo si se autoriza; NO recalcular colores científicos de mallas.

**Espaciado:** escala base 4px: 4/8/12/16/20/24/32/40/48; prohibir ajustes individuales ad hoc (`margin-left: 17px` sin token).
**Radios:** 8px control, 12px panel, 16px overlay/sheet, 999px pill; evitar radius enormes tipo card de marketing.
**Tamaños:** icono 18–20px; control desktop min 36px, toolbar 40px, coarse/touch min 44px, primary mobile 48px.
**Tipografía:** system UI / Inter bajo licencia apropiada; preferir `-apple-system, BlinkMacSystemFont, "Segoe UI", Inter, sans-serif` con alineación numérica tabular. Body mobile 16px, desktop 14–16px, metadata secundaria >=13px cuando se requiera lectura, labels 13–14px, títulos `clamp(18px,1.3vw,24px)`. Line-height texto 1.45–1.6. No usar 10–11px en contenido de estudio.
**Sombra:** mínima para overlays; `backdrop-filter` por defecto OFF en móvil; como máximo blur leve en escritorio amplio si no impacta render. No glow excesivo, animaciones decorativas, fondos de video o parallax.
**Motion:** cambios de panel 140–220ms con opacity/transform; feedback selección <=120ms; `prefers-reduced-motion:reduce` desactiva transiciones no indispensables y cualquier cámara animada no solicitada.

## 6. SISTEMA DE CAPAS (NO Z-INDEX ALEATORIO)

Tokens: `--z-canvas:0`, `--z-canvas-labels:10`, `--z-floating-toolbar:20`, `--z-drawer:40`, `--z-sheet:50`, `--z-popover:60`, `--z-modal:80`, `--z-toast:90`.
- Canvas nunca por encima de un modal.
- Toast no tapa CTA principal ni teclado; avisos críticos usan panel con acciones; errores estructurados no sólo desaparecen al cabo de 3 segundos.
- Drawers y modales establecen focus trap/restauración; overlay inert/aria-hidden para región de fondo cuando aplica; body lock mientras un modal está abierto sin romper Safari scroll.
- No dependencias globales de `z-index:999999`.

## 7. CSS BASELINE — PATRONES CANÓNICOS (ILUSTRATIVOS, NO IMPLEMENTADOS)

```css
*, *::before, *::after { box-sizing: border-box; }
html, body, #root { min-width: 0; min-height: 0; margin: 0; }
html { -webkit-text-size-adjust: 100%; text-size-adjust: 100%; }
:root {
  --app-height: 100vh;
  --header-height: 60px;
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
}
@supports (height: 100dvh) { :root { --app-height: 100dvh; } }
.atlas-app {
  height: var(--app-height);
  min-height: 0;
  display: grid;
  grid-template-rows: calc(var(--header-height) + var(--safe-top)) minmax(0,1fr);
  overflow: clip;
  background: var(--bg-app);
}
.atlas-header {
  min-width: 0;
  padding-block-start: var(--safe-top);
  padding-inline: max(12px,var(--safe-left)) max(12px,var(--safe-right));
}
.atlas-workspace {
  min-height: 0; min-width: 0;
  display: grid;
  grid-template-columns: 64px 296px minmax(0,1fr) 344px;
}
.atlas-canvas-stage, .atlas-canvas-stage canvas {
  min-width: 0; min-height: 0; display: block; width: 100%; height: 100%;
}
.atlas-canvas-stage canvas { touch-action: none; }
.atlas-explorer, .atlas-inspector { min-height: 0; min-width: 0; overflow: auto; overscroll-behavior: contain; }
@media (width < 1536px) {
  .atlas-workspace { grid-template-columns: 56px 296px minmax(0,1fr); }
  .atlas-inspector { display: none; } /* accessible as on-demand drawer */
}
@media (width < 1120px) {
  .atlas-workspace { grid-template-columns: minmax(0,1fr); }
  .atlas-rail, .atlas-explorer, .atlas-inspector { display: none; } /* drawer/sheet versions */
}
@media (width < 840px) {
  :root { --header-height: 56px; }
}
@media (width < 600px) {
  :root { --header-height: 52px; }
}
@media (height < 650px) {
  :root { --header-height: 48px; }
}
@media (pointer: coarse) {
  .atlas-control { min-height: 44px; min-width: 44px; }
}
@media (prefers-reduced-motion: reduce) {
  .atlas-animated { animation: none !important; transition: none !important; }
}
.atlas-sheet {
  padding-bottom: calc(12px + var(--safe-bottom));
  max-height: calc(var(--app-height) - var(--safe-top) - 12px);
}
```

Advertencias: este extracto define el default y breakpoints por ancho; la estrategia vertical/guarda del mínimo canvas, variantes de panel mobile y sheet deben resolverla componentes de layout bajo una sola clase `data-layout` estable. `display:none` del panel permanente requiere un drawer alternativo realmente accesible; no dejar controles ocultos sin ruta. Fallback para CSS moderno y feature queries documentado. Un `@media` no debe seleccionar el backend WebGPU.

## 8. PIXEL DENSITY, DPR, CANVAS GPU Y RESIZE

Separar claramente **tamaño CSS** (layout) de **tamaño físico de render**:
- Observar `ResizeObserver` del stage; usar `clientWidth/clientHeight` CSS (o contentRect). `canvas.width = round(cssWidth*dprEffective)`; idem height. No multiplicar CSS `width/height` por DPR; no estirar canvas vía CSS scale.
- DPR efectivo inicial: `min(devicePixelRatio, dprCap)`, con caps low=1.25; medium=1.75; high=2.0. Además, presupuesto de píxeles ejemplo low=1.6MP, medium=3.7MP, high=8.3MP. Reducir dprEffective proporcionalmente si el buffer excede pixel cap; respetar límites reales `maxTextureDimension2D` y memory budgets del backend. Son objetivos iniciales sujetos a medición, NO garantías.
- iPhone con DPR nativo 3 no crea automáticamente un framebuffer 3× de cada dimensión; priorizar FPS/termal y antialiasing razonable.
- MacBook Pro Retina y monitor Windows 4K deben mantener UI nítida CSS; renderer puede reducir resolución GPU adaptativamente sin alterar UI. Nunca pedir canvas 8K sólo porque DPR es alto.
- `ResizeObserver` + una sola petición rAF para batch de resize; no reinicializar device/renderer en cada tick de resize, keyboard, Stage Manager o apertura de panel. Reconfigurar surface sólo si dimensiones físicas realmente cambian.
- Aspect ratio de cámara derivado de viewport render real; selección/picking utiliza coordenadas CSS corregidas por `getBoundingClientRect` y el scale efectivo, sin offsets globales hardcodeados.
- Al abrir inspector o sheet, cámara y selectedId se conservan. No hacer fit-to-bounds automático al resize; solo si el usuario pide `Enfocar`.
- Calidad adaptativa basada en pacing real de rAF y (cuando exista) timestamp GPU, con ventana temporal y histéresis; no alternar resolución/LOD cada frame.
- Estados visible/hidden/pagehide, batería/termal y background: detener frames o timers innecesarios, sin perder estado; no afirmar mediciones de energía sin instrumentos.

## 9. TECLADO, ACCESIBILIDAD Y ACCIONES EQUIVALENTES

- WCAG 2.2 AA como gate; mínimo SC 2.5.8 =24×24 CSS px o excepciones, objetivo de producto 44×44 para touch (similar al criterio AAA reforzado SC 2.5.5).
- Contraste, focus visible 2–3px, navegación de teclado, tab order consistente `topbar -> explorer -> canvas -> inspector`, Escape cierre overlay; aria-live `polite` para ready y `assertive` errores recuperables críticos.
- Árbol anatómico con roles correctos, selección aria-selected, botones aria-label para aislar/mostrar, focus roving y alternativa de lista al picking por canvas.
- Atajos tentativos `Ctrl/Cmd+K` búsqueda, `Esc` cerrar/deseleccionar, `F` enfocar, `R` reset cámara; sólo activarlos cuando no está escribiendo el usuario y mantener botón equivalente.
- Soporte VoiceOver Safari iOS/macOS y TalkBack Android; lector de pantalla debe acceder a TA2/ES/EN/LA sin necesitar 3D.
- Aumentos 200% fuente, zoom 200% y zoom 400% reflow cuando sea aplicable; `font-size` nunca fijada con `transform:scale`, evitar altura fija de filas con texto que envuelve.
- `forced-colors:active` y `prefers-contrast:more`: bordes e indicadores se hacen explícitos sin depender del color de fondo; focus intacto.
- Loading y failures muestran controles `Reintentar`, `Cambiar backend`, `Descargar para offline` SÓLO si esa acción existe. Nunca dejar spinner permanente sin explicación.

## 10. MATRIZ QA — DESKTOP, IOS, IPADOS, ANDROID Y WINDOWS

No usar única captura `1280×720` para aprobar responsive.

**Playwright snapshots por CSS viewport (mínimo):**
320×568; 360×640; 375×667; 390×844; 393×852; 412×915; 430×932;
600×800; 768×1024; 820×1180; 834×1194; 1024×768; 1024×1366;
1112×834; 1194×834; 1280×720; 1366×768; 1440×900;
1512×982; 1536×864; 1728×1117; 1920×1080; 2560×1440; 3440×1440.
Alternar dark/light, sin selección/con selección, drawer cerrado/abierto, loading/error/offline, texto grande. Se puede reducir combinatoria con pares representativos, pero cada breakpoint y caso de alto crítico debe tener captura.

**Prueba física o cloud DEVICE REAL antes de aceptar M05 final:**
- iPhone iOS Safari: pantalla compacta y grande, notch/home indicator, teclado/URL bar dinámica, vertical/horizontal; PWA instalada.
- iPadOS Safari: 11"/13" o equivalentes, portrait/landscape, Split View y Stage Manager/window resize, Apple Pencil, teclado/trackpad.
- macOS Safari y Chrome: Retina, browser zoom 125/200%, ventana estrecha, scroll/trackpad y teclado.
- Android Chrome + al menos un navegador adicional vigente: Gboard, sistema gestual, landscape, DPR variado, device low power; plegable si disponible.
- Windows Chrome/Edge: 100/125/150% display scale, pantalla táctil 2-en-1 si existe, mouse/wheel.
- WebGPU y WebGL2: al menos 2 casos por plataforma soportada. En browsers sin WebGPU comprobar fallback; Safari web feature support por versión, NO asumir universalidad.

**Assertions automatizables obligatorias:**
- `document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1` fuera de overlays intencionales.
- Cada control principal visible/activable sin intersección con safe inset ni barra del sistema.
- Stage de canvas visible y ancho disponible superior al mínimo para el modo activo (con excepciones explícitas bajo 320px).
- No overlays críticos bloqueados por teclado; foco visible después de mover el sheet.
- En 200% zoom todo texto importante refluye, botones accesibles, canvas aún operable.
- Cambiar orientación, resize y abrir/cerrar panel 20 veces no aumenta contadores de listeners ni recrea engine.
- Gestos pointer y touch no disparan eventos a paneles sobre el canvas ni a canvas bajo panel.
- `prefers-reduced-motion`, `forced-colors`, RTL como comportamiento futuro con propiedad CSS lógica aunque UI es-MX.
- JS del frontend no modifica object normals, camera state, asset geometry ni LOD fuera de acciones bridge autorizadas.
- No atribuir PASS para Safari iOS real sólo porque Playwright WebKit o emulación de dispositivo pasó en Windows.

## 11. CRITERIOS DE RECHAZO DE DISEÑO / ANTIGRAVITY

**REJECT inmediato si**:
1. Un breakpoint se decide con `navigator.userAgent`/marca en vez de ancho y capacidades.
2. Se usan paneles fijos múltiples en iPad 1024px que dejen el viewport 3D diminuto.
3. No hay safe-area-insets, altura 100dvh/fallback, control de teclado/sheets o modo landscape.
4. Se usa `100vw` indiscriminadamente causando scrollbars/horizontal overflow; elementos grid sin `min-width:0`.
5. La UI móvil depende de hover o controles <=32px y sin alternativa.
6. React reinicializa Rust/WASM/WebGPU al abrir panel, cambiar tema o ajustar el tamaño.
7. Los colores de los órganos cambian arbitrariamente con el tema.
8. Se usan animaciones constantes, blur potente, sombras pesadas o canvas detrás de cards decorativas.
9. Se implementan instrumentos médicos no soportados por el motor como si funcionaran.
10. Se entregan sólo screenshots de desktop, sin pruebas mobile/scroll/keyboard/safe area.

## 12. ENTREGABLES DE DISEÑO, ANTES DEL PROMPT DE CÓDIGO

D0: Wireframe desktop 1536×960 con 3 paneles, laptop 1280×800, iPad portrait 834×1194 e iPhone 390×844. States normal/selected/loading/error.
D1: Component inventory y design tokens v1; Figma-equivalente de componentes, tamaños y estados.
D2: Mapa React UI vs Rust engine vs asset manager; evitar duplicación de scene/camera.
D3: Test plan visual y funcional con matriz anterior, incluyendo gestos, keyboard, rotation y Stage Manager.
D4: Acceptance review con captura aprobada por el propietario ANTES de generar prompt Antigravity M05.

No entregar código de producción ni `npm install` ni modificar `apps/probe-web`/crates hasta autorización explícita.

## Referencias normativas para el diseño
- MDN: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Values/env
- MDN: https://developer.mozilla.org/en-US/docs/Web/API/VisualViewport
- MDN: https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Containment/Container_size_and_style_queries
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- WCAG 2.5.8 AA: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum
- WCAG 2.5.5 AAA: https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced
