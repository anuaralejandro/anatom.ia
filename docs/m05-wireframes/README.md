# M05 — Wireframes de diseño (sin motor de anatomía)

**Ámbito:** revisión de producto, layout y styling; no implementa React, Rust, WASM, glTF, cache ni PWA. Evita importar o redistribuir modelos Z-Anatomy en artefactos públicos.

## Abrir

Abrir directamente en un navegador:

C:\Users\datam\Documents\anatom.ia\docs\m05-wireframes\index.html

También se puede servir como HTML estático desde un servidor local para ejecutar Playwright.

## Concepto visual

Clinical Precision / Midnight: navegación superior, explorador de estructura, canvas 3D dominante e inspector anatómico. El elemento central es una **ilustración SVG original conceptual**, creada para revisar composición, NO es anatomía clínicamente exacta y NO debe usarse en producción como modelo médico.

Incluye estados de diseño seleccionada/sin selección/cargando/error, tema claro/oscuro, búsqueda ilustrativa y paneles responsivos. Las acciones del inspector son visuales: no tienen efectos anatómicos.

## Tamaños de revisión

- Desktop profesional: **1536 × 960**, tres paneles
- MacBook / laptop: **1280 × 800**, explorador fijo, inspector temporal
- iPad vertical: **834 × 1194**, canvas y explorador/inspector temporales
- iPhone: **390 × 844**, canvas, header compacto y sheet inferior
- Extra recomendados: iPhone apaisado 844 × 390, iPad landscape 1194 × 834, Android 360 × 800 y desktop 1920 × 1080

## Parámetros de URL opcionales

- ?capture=1 oculta los controles de revisión y mantiene la captura limpia
- ?theme=light alterna tema claro
- ?state=selected|empty|loading|error
- ?panel=inspector|explorer abre un panel temporal cuando aplique
- ?sheet=max expande el sheet móvil

## Requisitos de validación

El layout se decide por viewport CSS y altura, nunca User-Agent. Stage minimum target: 720px pro-wide, 640px workstation, 540px tablet, full-width en compact. Check de scroll horizontal, controles, tamaños táctiles, no overlap de paneles y estados. Son capturas de emulación Chrome/Playwright en Windows; NO certifican por sí solas Safari iOS, iPadOS, Android ni Apple Pencil. Los dispositivos reales siguen pendientes.

Contrato fuente: docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md.
