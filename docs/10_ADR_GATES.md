# Etapa 7 — ADR y quality gates

**Tipo:** Architecture Decision Records (ADR) previos al código. **Estado:** diseño aprobado para prototipado local, release todavía bloqueado.

## ADR-001 — Motor especializado, no generalista
**Decisión:** Rust core con scene graph especializado; no Bevy/ECS completo ni Three.js como segundo motor. **Motivo:** geometría anatómica mayormente estática y necesidad de identidad por órgano. **Reversión:** si aparecen requisitos reales de animación/simulación imposibles de sostener sin ECS, medir primero.

## ADR-002 — Dos builds web explícitos
**Decisión:** builds WebGPU y WebGL2 desde Rust/wgpu compartido. **Motivo:** fallback aislado y pipelines verificables. **Condición:** fallback debe probar nuevos canvas/device/pipelines, no solo feature detection. **Reversión:** evaluar build wasm dual solo después de evidencias del tamaño y arranque.

## ADR-003 — glTF/GLB + catálogo externo
**Decisión:** conservar estándares abiertos, extras `atlas_id` y TA2 ID, manifest JSON. **Motivo:** interoperabilidad y auditoría. **Prohibido:** asociar ID permanente a índices glTF, mezclar materiales sin preservar mapeo de estructuras.

## ADR-004 — Procesamiento offline
**Decisión:** Blender/meshoptimizer fuera del dispositivo; no servidores GPU para visualizar. **Motivo:** reducir consumo móvil y complejidad operativa. **Restricción:** no publicar contenido sin provenance+licencia.

## ADR-005 — Calidad definida por medición
**Decisión:** LOD solo por error anatómico/silueta, no ratio uniforme. **Motivo:** nervios y vasos son frágiles. **Métrica inicial:** error de silueta p95 ≤2px a viewport de prueba 720px, pendiente de medición y revisión clínica.

## ADR-006 — Single source of truth
**Decisión:** Rust posee escena/selección/GPU, React presenta; bridge tipado. **Motivo:** evitar dos estados y renderización innecesaria. **Límite:** snapshots/versiones de estado por evento, no sincronizar meshes cada frame.

## ADR-007 — Caché y CDN estáticos
**Decisión:** S3/CloudFront + Cache Storage/IndexedDB + LRU Rust; sin backend dinámico para MVP. **Motivo:** minimizar costos, latencia y superficie de fallos. **Restricción:** caché no está garantizada y no sustituye red.

## ADR-008 — Release condicionado por licencias y revisión anatómica
**Decisión:** el uso local de pruebas no equivale a autorización de distribución. **Motivo:** fuente incluye obligaciones CC BY-SA y materiales terceros NC. **Requisito:** validación de procedencia por pieza, atribuciones y revisión clínica.

## Gate de desarrollo vs gate de publicación

**Desarrollo local (M00–M05):** se pueden utilizar fixtures experimentales con trazabilidad y sin distribuirlos públicamente. La licencia comercial no necesita estar resuelta para comprobar que el motor funciona.

**Publicación (M06):** BLOQUEADA hasta resolver licencia y exactitud anatómica de los assets incluidos; la aprobación técnica no abre automáticamente gate legal.

## Evidencia mínima por etapa

| Gate | Comprobación | Evidencia que debe guardarse |
|---|---|---|
| G-M00 | Workspace y checks reproducibles | comandos, versiones y lockfile |
| G-M01 | WebGPU y WebGL2 con shader real | capturas/logs por backend |
| G-M02 | 26 mallas identificables y gestos | pruebas de selección/lateralidad, capturas |
| G-M03 | LOD / catálogos / licencias | validación schema, hashes y error silueta |
| G-M04 | caché, cancelación, device recovery | trazas, comparativa frío/caliente |
| G-M05 | UI React accesible, móvil y desktop | E2E, accesibilidad, screenshots |
| G-M06 | QA físico + legal + clínico | métricas por hardware, informes de revisión |

**Los gates G-M00–G-M06 empiezan en NOT_RUN.** Las 12 validaciones de etapa 6 solo acreditan consistencia de diseño y archivos de prueba.

## Reporte de aceptación requerido

Cada implementación debe producir un reporte por hito con estas claves:
- `milestoneId`, `commit`, `date`, `deviceAndBrowser`.
- `tests`: prueba, comando, exitCode, resultado PASS/FAIL/NOT_RUN/BLOCKED y enlace a logs internos.
- `performance`: escena, backend, cacheState, frameTimeP50/P95, firstFrame, CPU/GPU estimada.
- `knownIssues`, `regressions`, `releaseBlockers`.
- `gateDecision`: PASS/FAIL/BLOCKED firmado por evidencia.

No se permite declarar PASS por compilar, sin render gráfico, ni por ausencia de captura.

## Pruebas innegociables

1. Baseline inmutable 26 IDs y 27 primitives, hash previamente verificado.
2. Node extras se conservan aunque material y LOD cambien.
3. Simular fallo de WebGPU y abrir WebGL2 o informar indisponibilidad sin bloqueo.
4. Mantener estado al cambiar DPR, canvas size, variante, región y al recuperar dispositivo.
5. Selección de estructuras ocluidas y muy finas funciona según regla documentada.
6. Carga repetida, caída de red y caché llena no generan fuga GPU ni errores silenciosos.
7. No declarar 30/60 FPS garantizados sin muestras en hardware representativo.
8. No publicar derivados sin evidencia de licencia y validación científica.

## Decisiones técnicas por resolver mediante prototipo

- Qué versión patch exacta de wgpu 30 usar y qué flags/target requiere el build.
- Necesidad real de BVH en 26 estructuras frente a raycasting directo.
- Frecuencia y coste de uploads GPU por frame.
- Material de resaltado seleccionado con soporte en WebGL2.
- Máximo real de búferes uniformes / bind groups bajo downlevel.
- Efecto de DPR/resolución y caché sobre Android de baja memoria.
- Si separar la pelvis en múltiples paquetes mejora latencia frente a un solo GLB ~681 KB.
- Proveniencia detallada de mallas y publicación comercial.

## Aprobación de arquitectura

El plan se considera **listo para redactar prompts de implementación**, no listo para producción. Prioridad inmediata: M00 → M01 → M02. No ampliar alcance automáticamente a contenido femenino ni atlas de cuerpo completo.
