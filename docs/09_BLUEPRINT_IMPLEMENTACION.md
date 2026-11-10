# Etapa 7 — Blueprint ejecutable de implementación

**Fecha:** 2026-11-09 · **Estado:** DISEÑO FINAL PRE-PROMPTS · No hay motor ni frontend implementados.

## 1. Resultado previsto

Un visualizador de anatomía 3D con Rust + wgpu y navegador mediante WebAssembly, compatible tanto con WebGPU como con WebGL2 mediante una ruta controlada. El objetivo inicial NO es construir el atlas entero: es cargar la pelvis real de 26 estructuras en ambas rutas gráficas, interactuar correctamente con ella y demostrar su rendimiento.

Los productos separados serán:

1. `atlas-core`: escena, cámara, picking, renderizado, gestión GPU, assets y memoria. Rust puro, sin DOM.
2. `atlas-web`: superficie canvas, WASM, interop JS, fetch/caché. No contiene segunda escena 3D.
3. `atlas-builder`: herramienta offline para Blender/glTF, TA2, LOD, licencias y manifiestos.
4. `apps/probe-web`: shell HTML/TS mínima para la primera prueba; se elimina como UI de producción después.
5. `apps/viewer`: React/TS/CSS premium, solo después de aprobar el prototipo.

No se requieren API de usuarios, base de datos, Redis, microservicios, contenedores ni servidores GPU. El servidor local de desarrollo es solo para servir los archivos; producción se basará en S3+CloudFront después de aprobación.

## 2. Orden exacto de trabajo

| Hito | Construcción | Dependencias | Gate |
|---|---|---|---|
| M00 | Toolchain/fixtures/workspace reproducibles | Ninguna | G-M00 |
| M01 | Canvas y shaders mínimos WebGPU **y** WebGL2 | M00 | G-M01 |
| M02 | GLB real 26 IDs, cámara, seleccionar, ocultar, aislar | M01 | G-M02 |
| M03 | Builder incremental, catálogo, material, LOD de prueba | M02 | G-M03 |
| M04 | Streaming/cache/memoria/recovery | M03 | G-M04 |
| M05 | React definitivo, temas, búsqueda, gestos y PWA | M02 y M04 | G-M05 |
| M06 | QA físico, licencias, validación clínica, release | M05 | G-M06 |

**Importante:** M01 y M02 son el primer prompt de implementación. No es necesario esperar a generar LOD para probar Rust. No encadenar todos los hitos en una misma ejecución de Codex: cada uno requiere evidencia y gate.

## 3. Criterio de terminado por hito

### M00: Preflight

- Rust y cargo versionados, `Cargo.lock`, `rust-toolchain.toml`, wasm32 target, `wasm-bindgen-cli`.
- Dos builds reproducibles; versiones/flags documentados.
- Referencia de entrada fija: `reports/experimental/pelvis-pbr-core-compat.glb`.
- Validación scripts disponibles y hash previo. No modificar upstream.

### M01: Render mínimo dual backend

- Un triángulo/cubo sintético se muestra desde Rust+wGPU en WebGPU y WebGL2.
- Ambos paths compilan y se prueban; pipeline WGSL validado en browsers reales.
- WebGL2 utiliza límites `downlevel_webgl2_defaults()` y features mínimas.
- Evitar compute/storage buffers/indirect draw y texturas obligatorias.
- Tras un fallo WebGPU, inicializar **un canvas nuevo** para WebGL2 cuando no pueda reutilizarse el contexto.
- Si ambas rutas fallan, error visible. No declarar éxito por compilar solamente.

### M02: Pelvis seleccionable

- GLB de 26 nodos, 27 primitives y 10 materiales core PBR; IDs TA2 presentes.
- Lectura y validación de accessors, offsets, índices, buffers, transformaciones, extras, extensiones.
- Cámara orbit/pan/zoom, center-fit, hover/selección por rayo CPU, focus, hide/isolate/reset.
- Tests en diferentes ángulos, DPR y soporte de mouse/touch.
- Capture de referencia + logs de cada backend.
- No modificar la geometría de prueba durante esta fase.

### M03: Builder incremental

- Normalización y conversión de CURVE→MESH/etiquetas a partir de copias, con Blender headless.
- Catálogo TA2, mallas separadas, licencia/procedencia por pieza.
- LOD experimental solo de sacro/vejiga inicialmente; preservar invariantes.
- Hash SHA-256 y esquema de `manifest` existente, sin formato propietario.
- Comparación visual LOD0 vs LOD1 y rechazo de deformación anatómica.
- Publicación limitada a artefactos internos de prueba.

### M04: Streaming y robustez

- Colas con `scene_generation` y `requestId`, resultados tardíos descartados.
- Cache Storage/IndexedDB y LRU RAM/GPU sin duplicación reactiva.
- LOD base primero y swap atómico; recursos liberados bajo presupuesto.
- DeviceLost y reconexión; navegación/interacción no bloqueada por fetch.
- Instrumentación que separe download, decode, upload y frame.

### M05: UI final

- React + TypeScript (sin render loops en React). Bridge desde `contracts/engine-bridge-v1.json`.
- Canvas fullscreen, paneles y barra mínima, bottom sheet móvil, buscar por TA2.
- Temas claros/oscuros con turquesa, azul y naranja, respetando colores anatómicos reales.
- Accessibility, teclado, targets táctiles, almacenamiento de preferencias.
- PWA/offline solo con política de quota y degradación verificada.

### M06: Release

- Evidencia en dispositivos físicos y navegadores definidos; costos de memoria medidos.
- Licencias de cada activo y atribuciones aprobadas antes de publicar.
- Revisión anatómica independiente para orientación, escala, etiquetas y relaciones.
- Smoke/regresiones, rollback de assets, archivos inmutables y puntero `current.json`.
- NO distribuir públicamente derivaciones si gate comercial está bloqueado.

## 4. Contratos que no se reescribirán durante implementación

- `contracts/atlas-manifest.schema.json`: catálogo y paquetes referenciados por SHA-256.
- `contracts/render-profile-v1.json`: conjunto de capacidades y límites.
- `contracts/quality-profiles-v1.json`: presupuestos iniciales no medidos.
- `contracts/renderer-acceptance-v1.json`: pruebas R00–R14.
- `contracts/engine-bridge-v1.json`: única API commands/events, versionada.
- `contracts/implementation-milestones-v1.json`: dependencias, estados, evidencias.

Se admite corregir un contrato cuando una prueba demuestre un defecto; requiere ADR, versión y test de migración, no modificaciones silenciosas.

## 5. Construcción y bifurcación del navegador

El proyecto adoptará **dos builds WASM explícitos** inicialmente: `browser-webgpu` y `browser-webgl2`, compartiendo el mismo Rust core. Esto simplifica reproducibilidad, aislamiento de features y fallback.

El loader web puede detectar `navigator.gpu` como señal pero NO confiar en ello: debe confirmar requestAdapter, requestDevice, creación de surface y pipelines. En caso de error debe disponer de ruta WebGL2. El navegador puede impedir cambiar el tipo de contexto de un canvas ya utilizado; reemplazar canvas cuando corresponda.

Los flags/versions reales se fijarán tras la primera compilación dual exitosa. `wgpu` 30.0.x es baseline de evaluación, no dependencia instalada y comprobada.

Fuentes técnicas:
- https://wgpu.rs/doc/wgpu/documentation/platforms/web/index.html
- https://wgpu.rs/doc/wgpu/struct.Limits.html
- https://docs.rs/crate/wgpu/latest/source/README.md

## 6. Riesgos y decisiones contra regresiones

1. **Upstream pesado:** solo extraer el subset de pelvis; nunca abrir Blender por request.
2. **Doble backend:** mantener core WGSL reducido hasta pasar WebGL2 real.
3. **glTF IDs:** número de nodo no es identidad persistente; conservar extras y crosswalk.
4. **Lateralidad:** no inferir geometría femenina desde un atlas masculino.
5. **LICENCIA:** el repositorio tiene contenido CC BY-SA y referencias de terceros NC. Bloquear comercialización sin auditoría.
6. **Rendimiento:** no medir FPS solo en la RTX; probar Intel UHD y móviles físicos.
7. **Caché agresiva:** cuotas no garantizadas; nunca bloquear carga si almacenamiento persistente falla.
8. **Plataformas nativas:** quedan fuera de MVP; no prometer Android/iOS nativos con el mismo código de ventana.
9. **Estado duplicado:** no replicar escena/RAM GPU en React.
10. **Complejidad:** sin ECS de videojuegos, motores 3D duplicados ni formatos propietarios.

## 7. Condiciones exactas para generar prompts de Codex

La arquitectura queda lista para convertirla en prompts. El primero debe pedir **solo M00–M02**, con el fixture existente, instrumentos de prueba, comandos reproducibles y prohibición de iniciar M03–M06 sin gate. El segundo se concentrará en M03, el tercero en M04 y el cuarto en M05–M06 con QA.

Los prompts deben indicar explícitamente:
- repo y ruta de trabajo: `C:\Users\datam\Documents\anatom.ia`.
- no tocar `sources/z-anatomy-upstream`.
- no reemplazar los contratos sin ADR y pruebas.
- evidencias: comando, resultados, logs, capturas, errores y limitaciones.
- cualquier gate no ejecutado permanece `NOT_RUN`, nunca se declara PASS por suposición.

**Estado actual:** diseño listo; implementación no iniciada.
