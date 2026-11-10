# anatom.ia — apps/viewer (M05-A Foundations)

Frontend oficial en React + TypeScript estricto + Vite para el visualizador anatómico 3D de alta precisión clínica.

## 1. Arquitectura y Tecnologías
- **Framework:** React 18.3 + TypeScript 5.6 (strict mode)
- **Bundler:** Vite 6
- **Estilos:** CSS Tokens puro sin dependencias externas pesadas (`.atlas-*`)
- **Paleta oficial:** Obsidian Navy (`#05080D`, `#03060B`, `#0B111C`) con acento funcional Modern Sky Blue (`#58B9FF`, `#7AC8FF`, `#2E9CFF`)
- **Modo Claro:** Preservado íntegramente (`#F5F8FA` / `#087A7A`)
- **Responsive:** Matrix adaptativa de 5 niveles:
  - `compact`: 320–599px (Bottom Sheet móvil con 3 estados: colapsado, 52% medio, 86% expandido)
  - `compact-wide`: 600–839px (Drawers laterales mutuamente exclusivos)
  - `tablet`: 840–1119px (Rail vertical + drawer temporal)
  - `workstation`: 1120–1535px (Rail + explorador fijo + inspector drawer)
  - `pro-wide`: >=1536px (Rail + explorador 296px + stage central >=720px + inspector 344px)

## 2. Comandos de Desarrollo en Windows (PowerShell)

### Instalación
```powershell
cd apps/viewer
npm install
```

### Ejecución en Desarrollo
```powershell
npm run dev
# Servidor local en http://127.0.0.1:3000
```

### Verificación de Tipos y Compilación de Producción
```powershell
npm run build
# Ejecuta: tsc -b && vite build
```

### Ejecución de Pruebas Unitarias
```powershell
npm test
# Ejecuta: npx tsx --test tests/**/*.test.ts
```

### Suite de Integración y Visual Playwright
```powershell
python ../../tools/test_m05a_react_suite.py
```

## 3. Estado del Hito (M05-A / M05-A.1 Closeout)
- **Preview de Diseño:** El visor 3D en M05-A muestra una vista conceptual sintética autorizada para validación de layout, orientada mediante el nuevo **3D Axis Navigation Gizmo (F16)** al estilo Blender.
- **Rendimiento en Reposo (F09):** Cero loops perpetuos en reposo (`0 callbacks rAF en 750ms` bajo reduced-motion).
- **Accesibilidad y Foco (F10, F11):** Diálogo semántico con trampa de foco Tab/Shift+Tab, restauración en Escape y hitboxes $\ge 44 \times 44$ CSS px.
- **Catálogo y Taxonomía (F14):** 26/26 estructuras pélvicas sincronizadas y clasificadas con la Terminologia Anatomica 2 (TA2) sin heurísticas.
- **M05-B:** Conexión del atlas clínico GLB real y streaming de paquetes 3D reservada para la siguiente fase.
