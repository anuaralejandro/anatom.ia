# Orden de implementación y checkpoints

## Fase A — ahora: diseño + auditoría
- Verificar herramientas y carpeta del proyecto.
- Inventariar archivos de referencia sin modificarlos.
- Redactar contrato vertical slice y tests de aceptación.
- Bloqueos: fuente anatómica verificable, licencia, registro espacial y máquinas de prueba.
**Salida:** documentos, herramienta de inventario y reporte. SIN motor/React en esta fase.

## Fase B — prueba de viabilidad
- Fixture sintético de múltiples mallas + fixture real autorizado.
- Compilación mínima Rust+wgpu/WASM y canvas temporal.
- Detectar WebGPU y ruta WebGL2, registrar limitaciones.
- Implementar render básico/cámara/input/selección sin optimización prematura.
**Gate:** representación y selección con IDs sin pérdida en las dos rutas web.

## Fase C — builder primero, con consumidor de prueba
- Blender export de objetos identificados, normalización, LOD y meshopt/compresión compatible.
- Manifiesto, catálogo, reporte de licencia/validador.
- Prohibición de publicar fuente sin autorización.
**Gate:** round trip IDs/LOD + tamaños/integridad.

## Fase D — núcleo de producción
- Scene graph, scheduler, cache, memoria, calidad y recuperación.
- API de comandos/eventos y pruebas de carreras.
**Gate:** pruebas de memoria, switching y fallback.

## Fase E — UI definitiva
- React/Vite/TypeScript, temas turquesa/azul/naranja, búsqueda y paneles adaptativos.
- PWA y modo offline parcial; accesibilidad y rendimiento.
**Gate:** uso móvil físico con trazas y regresiones.

## Orden de prompts futuros
1. Auditoría real + fixture + benchmark mínimo Rust/WASM (no backend HTTP).
2. Builder + contratos/manifiesto/validación.
3. Atlas Core + API, assets, memoria y streaming.
4. Frontend React final + integración + PWA + QA.
No generar prompts finales hasta que se verifique la fuente o se delimite formalmente la fase sintética de viabilidad.

## Criterios para avanzar desde fase A
- **PASS:** archivos originales identificados y accesibles desde `sources/z-anatomy-template/Z-Anatomy/Startup.blend` (commit upstream fijado).
- **PASS parcial:** Blender enumera 7,184 objetos, 4,569 mallas y 951 curvas separadas; falta probar exportación glTF con identidad preservada.
- **PENDIENTE/BLOQUEANTE comercial:** matriz de licencia por asset y restricciones de terceros; licencia global leída, aún no se atribuyó cada malla.
- **PENDIENTE:** candidato de 26 objetos documentado; faltan TA2 IDs estables, escala, curvas, bounds y validación anatómica.
- Blender localizado (4.4); toolchain WASM/meshoptimizer por fijar/verificar antes de implementación.
Si falta material, realizar únicamente fixture sintético para evaluar motor, sin declarar atlas anatómico validado.

## Estado del gate tras fuente confirmada (2026-11-09)
- Origen público localizado y commit inmovilizado: **PASS**.
- `Startup.blend` abierto en Blender 4.4, 7,184 objetos enumerados: **PASS**.
- Fixture candidato de 26 estructuras presentes (18 MESH, 8 CURVE): **PASS de existencia**, todavía no exportación.
- Concordancia de anatomía con IDs TA2 y límites espaciales: **PENDIENTE**.
- Licencias individuales aptas para eventual uso comercial: **PENDIENTE/BLOQUEANTE**.
- Contrato renderizado v1, materiales core PBR y matriz QA: **DISEÑO PASS** (ver `docs/07_RENDERER_WGPU_SPEC.md`, `docs/08_LOD_PICKING_TEST_PLAN.md` y `reports/stage6-contract-validation.json`). Renderizador Rust/WebGL2/WebGPU: **NO IMPLEMENTADO**.
- Benchmarks de memoria y FPS móvil: **NO REALIZADOS**.
Ver `docs/05_Z_ANATOMY_FUENTE_VERIFICADA.md` y `reports/pelvis-fixture-candidate.json`.

**Actualización 2026-11-09:** Los gates de esta etapa histórica ya fueron reemplazados por `docs/09_BLUEPRINT_IMPLEMENTACION.md` y `contracts/implementation-milestones-v1.json`. La auditoría de TA2/GLB y contratos de renderer (etapas 5–7) está documentada en `docs/06_VALIDACION_PELVIS_Y_GLB.md`, `docs/07_RENDERER_WGPU_SPEC.md` y `reports/stage7-blueprint-validation.json`. Los estados PENDIENTE anteriores son fotografía histórica y no deben usarse como estado actual; no se ha implementado el motor.
