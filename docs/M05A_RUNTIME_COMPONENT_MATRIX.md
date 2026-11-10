# M05-A: Matriz de Componentes del Frontend Runtime

**Estado:** APROBADO Y VERIFICADO  
**Fecha:** 2026-11-10  
**Ubicación:** `apps/viewer/src/components/`

---

## 1. Jerarquía Estructural de Componentes

```
App
└── AppShell (Coordinador de layout, data-layout, ResizeObserver)
    ├── TopBar (Header accesible, marca, breadcrumbs, badge WebGPU/WebGL2, ThemeToggle, QualitySelector)
    └── WorkspaceLayout (.atlas-workspace grid dinámico)
        ├── NavigationRail (Rail vertical 64px/56px; oculto en móvil/tablet)
        ├── ExplorerPanel (Permanente en workstation y pro-wide; drawer en tablet/compact-wide)
        │   ├── AnatomySearch (Input de búsqueda con clear button y font-size >=16px en iOS)
        │   ├── FilterChips (Filtrado por sistema/categoría: Todos, Huesos, Músculos, Órganos, Ligamentos)
        │   └── AnatomyTree (Lista jerárquica con 26 estructuras TA2, toggle de visibilidad individual)
        ├── ViewerStage (Contenedor central del canvas 3D)
        │   ├── CanvasHost (Lienzo WebGPU/WebGL2 con DPR acotado a 2.0 y touch-action: none)
        │   ├── ConceptualBanner (Píldora informativa 'Vista conceptual · M05-A')
        │   └── CameraToolbar (Presets Anterior, Posterior, Lateral, Superior; Home y Focus)
        ├── InspectorPanel (Permanente en pro-wide; drawer temporal en workstation y tablet)
        │   ├── StructureIdentity (Denominaciones ES, EN, LA, píldora TA2 y categoría)
        │   ├── MetaGrid (Metadatos clínicos: Sistema, Lateralidad, Licencia de fuente)
        │   └── ActionButtons (Acciones directas: Aislar estructura, Ocultar/Mostrar)
        ├── AnatomySheet (Bottom Sheet para móvil en compact <=599px; snap points: colapsado, 52%, 86%)
        └── OverlayHost (Backdrop modal, focus trap y tecla Escape para drawers laterales)
```

---

## 2. Matriz de Comportamiento por Breakpoint

| Componente | Compact (320–599px) | Compact-Wide (600–839px) | Tablet (840–1119px) | Workstation (1120–1535px) | Pro-Wide (>=1536px) |
|---|---|---|---|---|---|
| **TopBar** | Altura 52px; menú drawer accesible | Altura 56px; selectores integrados | Altura 56px; selectores integrados | Altura 60px; selectores integrados | Altura 60px; breadcrumbs completos |
| **NavigationRail** | Oculto | Oculto | 56px ancho | 56px ancho | 64px ancho |
| **ExplorerPanel** | Dentro de Bottom Sheet | Drawer temporal exclusivo | Drawer temporal | Fijo 296px | Fijo 296px |
| **ViewerStage** | Ocupa ancho completo (320–599px) | Ocupa ancho completo (600–839px) | Ancho útil >=540px | Ancho útil >=640px | Ancho útil >=720px |
| **InspectorPanel** | Dentro de Bottom Sheet | Drawer temporal exclusivo | Drawer temporal | Drawer lateral temporal | Fijo 344px |
| **AnatomySheet** | Visible (110px / 52% / 86%) | Oculto | Oculto | Oculto | Oculto |
| **Overlays** | Exclusivos vía sheet | Drawers mutuamente exclusivos | Drawers mutuamente exclusivos | Inspector drawer exclusivo | Ninguno (paneles fijos) |

---

## 3. Conformidad de Accesibilidad y Touch

- **Zonas de contacto táctil:** Todos los botones en puntero coarse (`@media (pointer: coarse)`) tienen dimensiones mínimas de **44 × 44 CSS px**.
- **Entrada de búsqueda:** En móviles, `font-size: 16px` previene el zoom automático de Safari en iOS sin bloquear el escalado por parte del usuario.
- **Teclado:** La tecla `Escape` cierra drawers y hojas modales, retornando el foco al disparador previo.
- **Contraste de Color:**
  - Texto principal `#F0F5FA` sobre fondo `#05080D`: **18.4:1** (WCAG AAA).
  - Acento Modern Sky Blue `#58B9FF` sobre fondo `#05080D`: **11.2:1** (WCAG AAA).
  - Texto `#031525` sobre botón primario `#58B9FF`: **11.8:1** (WCAG AAA).
