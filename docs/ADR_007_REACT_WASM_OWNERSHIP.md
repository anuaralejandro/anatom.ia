# ADR 007: Delimitación de Autoridad entre React y el Motor Rust/WASM

**Estado:** ACEPTADO  
**Fecha:** 2026-11-10  
**Contexto:** anatom.ia (Hito M05-A)

---

## 1. Contexto del Problema

La integración de un motor de gráficos de alto rendimiento en Rust (compilado a WebAssembly con wgpu para WebGPU y WebGL2) dentro de una interfaz de usuario reactiva en React y TypeScript plantea desafíos críticos de concurrencia y duplicación de estado:
1. **Riesgo de Reentrancia en RefCell de Rust:** El motor Rust despacha eventos mediante `setEventCallback`. Si el callback de JavaScript invoca sincrónicamente métodos de `AtlasEngine` (por ejemplo `getSceneSnapshot` o `selectStructure`), se produce un pánico inmediato por doble préstamo mutable (`already borrowed: BorrowMutError`).
2. **Duplicación Innecesaria de Estado 3D:** Mantener copias de mallas, matrices de transformación, cámara y buffers en el Virtual DOM de React degradaría el rendimiento a 60 FPS, saturando el recolector de basura.
3. **Inconsistencia de Nomenclatura:** Rust serializa las estructuras `SceneSnapshot` y `EngineCapabilities` en `snake_case` (`selected_id`, `scene_revision`, `visible_ids`, `adapter_name`), mientras que la aplicación React exige contratos estrictos en `camelCase`.

---

## 2. Decisión Arquitectónica

### 2.1 Matriz de Propiedad de Estado

| Dominio | Autoridad Exclusiva | Rol de React |
|---|---|---|
| Geometría 3D, Mallas GPU, Shaders, Cámara, Picking y Selección Foco | **atlas-core / Rust (WASM)** | Envía comandos tipados (`selectStructure`, `isolateStructure`, `setCameraPreset`) y recibe snapshots inmutables bajo demanda. |
| Gestión de Red, CacheStorage y Concurrencia de Descarga | **AssetStreamManager (JS)** | Coordinado mediante un único `AtlasRuntimeClient`. |
| Catálogo Médico, Nomenclatura TA2 (ES, EN, LA), Jerarquías | **catalog.json canónico** | Almacenado en `useUIStore`, utilizado para alimentar el buscador, filtros y tarjetas de información. |
| Layout Responsive, Paneles, Modales, Búsqueda, Sheet y Tema UI | **useUIStore (React / TypeScript)** | Controla el diseño visual (`compact`, `tablet`, `workstation`, `pro-wide`), drawers y navegación. |
| Canvas Surface, Device Pixel Ratio (DPR) y Render-on-Demand | **CanvasLifecycle / Rust** | Solo reacciona a redimensionamiento físico mediante `ResizeObserver`, sin desmontar contextos. |

### 2.2 Desacoplamiento de Eventos por Microtask Queue

Para prevenir de forma absoluta la reentrancia en `RefCell`:
```typescript
this.engine.setEventCallback((rawEvent: unknown) => {
  queueMicrotask(() => {
    if (this.disposed) return;
    const normalized = normalizeEvent(rawEvent);
    this.dispatch(normalized);
  });
});
```
Todos los eventos procedentes de Rust se encolan como microtareas, garantizando que el préstamo mutable en Rust se haya completado y liberado antes de que cualquier manejador de React o JavaScript intente consultar o modificar el estado del motor.

### 2.3 Adaptador Normalizador Único

Se establece una capa de transformación inmutable en `src/runtime/normalizer.ts`:
- Convierte `selected_id` $\to$ `selectedId`
- Convierte `scene_revision` $\to$ `sceneRevision`
- Convierte `visible_ids` $\to$ `visibleIds`
- Convierte `adapter_name` $\to$ `adapterName`
- Valida tipos en tiempo de ejecución, asignando valores seguros en caso de fallo.

### 2.4 Control del Ciclo de Render

React nunca ejecuta `setState` en cada frame a 60 FPS. El motor opera bajo demanda (*render-on-demand*): solo genera un fotograma cuando cambia la cámara, la selección, la visibilidad o se recibe un paquete de geometría.

---

## 3. Consecuencias

### Positivas
- **Cero Pánicos por Reentrancia:** Demostrado en pruebas unitarias (`tests/client.test.ts`).
- **Fluidez y Cero Fugas:** Las 20 iteraciones rápidas de redimensionamiento y conmutación de paneles no acumulan contextos GPU ni listeners.
- **Tipado Estricto de Extremo a Extremo:** No se utiliza `any` masivo en el código de aplicación.

### Negativas / Mitigaciones
- Las lecturas de estado del motor requieren snapshots puntuales o subscripciones discretas en lugar de bindings bidireccionales automáticos.
