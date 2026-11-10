# anatom.ia — Atlas Engine

**Estado independiente (2026-11-10): M00–M03 aprobados para desarrollo local. M04-H endurecido con 39 tests Rust PASS y F01–F03 verificados. M05-A y M05-A.1 (QA Closeout) completados con éxito: frontend React en apps/viewer, paleta Obsidian Navy + Modern Sky Blue (0% turquesa), 3D Axis Navigation Gizmo (F16), hitboxes >=44x44px, renderizado on-demand (0 rAF en reposo), trampa de foco modal, guarda de altura compact-wide y taxonomía TA2 26/26 validada. Pruebas unitarias React (16/16) y gates QA (10/10) PASS. Listo para auditoría independiente previa a M05-B.**

Atlas anatómico 3D multiplataforma. Arquitectura objetivo: núcleo Rust + wgpu, web mediante WASM, React/TypeScript para UI, activos glTF/GLB versionados y distribución estática. El primer objetivo NO es renderizar todo el cuerpo, sino validar la pelvis como *vertical slice* con compatibilidad WebGPU/WebGL2 y rendimiento móvil.

## Documentación

1. [Auditoría local](docs/00_AUDITORIA_LOCAL.md): inventario inicial del entorno.
1a. [Fuente Z-Anatomy verificada](docs/05_Z_ANATOMY_FUENTE_VERIFICADA.md): repositorio, commit, inventario Blender y licencia.
1b. [Validación de pelvis y GLB experimental](docs/06_VALIDACION_PELVIS_Y_GLB.md): TA2, lateralidad, curvas, archivo exportado y gates.
2. [Contrato del prototipo](docs/01_CONTRATO_PELVIS_VERTICAL_SLICE.md): alcance, invariantes y criterios de aprobación.
3. [Contratos técnicos](docs/02_CONTRATOS_TECNICOS.md): datos, runtime, errores, memoria y compatibilidad.
4. [Plan de validación](docs/03_PLAN_DE_VALIDACION.md): matriz de pruebas y medición.
5. [Secuencia de ejecución](docs/04_SECUENCIA_Y_GATE.md): hitos y condiciones para pasar a implementación.
6. [JSON Schema del manifiesto](contracts/atlas-manifest.schema.json): formato verificable v1.
7. [Inventario GLB local](reports/local-candidate-glb.json): solo metadatos, sin modificación de fuentes.
8. [Renderer wgpu v1](docs/07_RENDERER_WGPU_SPEC.md): shaders previstos, materiales, WebGPU/WebGL2, datos reales.
9. [LOD, picking y QA](docs/08_LOD_PICKING_TEST_PLAN.md): política por estructura y pruebas gráficas.
10. [Contratos de renderer](contracts/render-profile-v1.json), [calidad](contracts/quality-profiles-v1.json) y [aceptación](contracts/renderer-acceptance-v1.json): verificables por scripts.
11. [Blueprint de implementación](docs/09_BLUEPRINT_IMPLEMENTACION.md): hitos M00–M06 y criterios de terminado.
12. [ADR y quality gates](docs/10_ADR_GATES.md): decisiones de arquitectura, bloqueos y evidencia exigida.
13. [Plan de hitos](contracts/implementation-milestones-v1.json) y [bridge Rust↔React](contracts/engine-bridge-v1.json): contratos de implementación versionados.
14. [Validación de la etapa 7](reports/stage7-blueprint-validation.json): comprobaciones de consistencia del diseño.
15. [Prompt Antigravity 01 M00–M02](docs/PROMPT_01_ANTIGRAVITY_M00_M02.md): primera implementación.
16. [Auditoría independiente M00–M02](docs/AUDITORIA_IMPLEMENTACION_01.md): evidencia real, correcciones y autorización local para M03.
17. [Prompt Antigravity 02 M03](docs/PROMPT_02_ANTIGRAVITY_M03.md): Atlas Builder, LOD piloto y validación de assets.
18. [Auditoría independiente M03](docs/AUDITORIA_IMPLEMENTACION_02.md): correcciones verificadas y gate para M04.
19. [Prompt Antigravity 03 M04](docs/PROMPT_03_ANTIGRAVITY_M04.md): streaming, caché, memoria y recuperación GPU.
20. [Implementación 03 M04](docs/IMPLEMENTATION_03_RESULT.md): reporte de streaming, gestión de memoria, caché y recuperación.
21. [ADR 004](docs/ADR_004_CACHE_STORAGE.md): arquitectura de CacheStorage e integridad criptográfica.
22. [Guía de build de runtime](docs/BUILD_RUNTIME.md): instrucciones reproducibles para compilar WASM y ejecutar probe-web.
23. [Auditoría independiente M04](docs/AUDITORIA_IMPLEMENTACION_03.md): PASS parcial, defectos corregidos y requisitos pendientes antes de M05 definitivo.
24. [Prompt Antigravity 04 M04-H Hardening](docs/PROMPT_04_ANTIGRAVITY_M04_HARDENING.md): especificación obligatoria de hardening.
25. [ADR 005 — Swap GPU y Recuperación](docs/ADR_005_GPU_SWAP_AND_RECOVERY.md): arquitectura transaccional de dos fases, rollback y device-loss.
26. [ADR 006 — Memoria y Scheduler](docs/ADR_006_MEMORY_AND_SCHEDULER.md): control preflight de presupuestos, contabilidad de overlap y bounded fetch scheduler.
27. [Contrato de Puente WASM↔JS](docs/M04_RUNTIME_BRIDGE_CONTRACT.md): API real, estados de ciclo de vida y semántica de eventos para M05.
28. [Resultados Hardening M04-H](docs/M04_HARDENING_RESULT.md): reporte exhaustivo de verificación, gates A–N y benchmarks de hardware.
29. [Contrato responsive M05](docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md): estilos, breakpoints, safe areas y QA.
30. [Wireframes M05 aprobados](docs/13_M05_WIREFRAME_REVIEW.md): galería y prototipo interactivo de D0.
31. [Contrato D1 para M05](docs/14_M05_D1_INTEGRATION_CONTRACT.md): propiedad React/Rust, componentes, eventos y gates F01–F03.
32. [Prompt Antigravity 05 — M05-A](docs/PROMPT_05_ANTIGRAVITY_M05A_FOUNDATIONS.md): primera corrida de fundaciones React y reparación del scheduler/preflight, sin M05-B.
33. [Resultado Implementación M05-A](docs/M05A_IMPLEMENTATION_RESULT.md): arquitectura React, 16 viewports evaluados, mitigación de F01–F03 y verificación de paleta Obsidian Navy + Modern Sky Blue.
34. [ADR 007 — Propiedad de Estado React vs Rust/WASM](docs/ADR_007_REACT_WASM_OWNERSHIP.md): delimitación de autoridad, microtask queue y prevención de reentrancia en RefCell.
35. [Matriz de Componentes del Frontend Runtime](docs/M05A_RUNTIME_COMPONENT_MATRIX.md): especificación estructural y responsiva de apps/viewer.
36. [README del Frontend Viewer](apps/viewer/README.md): instrucciones de ejecución y comandos en Windows.
37. [Auditoría independiente M05-A](docs/AUDITORIA_IMPLEMENTACION_05A_INDEPENDIENTE.md): PASS parcial, pruebas Chrome y defectos QA/accessibility a cerrar.
38. [Prompt M05-A.1 QA Closeout](docs/PROMPT_06_ANTIGRAVITY_M05A_QA_CLOSEOUT.md): corrección de F08–F15 antes de integrar motor.
39. [Plan M05-B](docs/15_M05B_INTEGRATION_PLAN.md): fases de integración Rust/WASM + React, todavía sin ejecución.
40. [Resultado Cierre QA M05-A.1](docs/M05A_QA_CLOSEOUT_RESULT.md): resolución rigurosa de F08–F16, pruebas rAF, hitboxes, focus trap y gizmo 3D.

## Reglas de proyecto

- No crear API/backend tradicional en el MVP; assets estáticos y procesamiento offline.
- No asumir que los GLB locales son Z-Anatomy; la fuente y licencia se deben verificar.
- Preservar IDs anatómicos a través de importación, LOD, compresión y render.
- No procesar/exportar todos los órganos antes de validar una región representativa.
- Los números de rendimiento son hipótesis hasta benchmark en hardware físico.
- No publicar assets sin trazabilidad de licencia y atribución.
- No crear prompts finales ni iniciar implementación masiva hasta aprobar el gate de diseño.

## Estado de la auditoría

Rust/Cargo, Node, Python y Git disponibles. Carpeta inicialmente vacía. Blender 4.4 localizado en `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe` (fuera de PATH). Se clonó Z-Anatomy en `sources/z-anatomy-upstream` (commit `56016ea6`) y se extrajo `Startup.blend` en `sources/z-anatomy-template`. El inventario Blender confirma 7,184 objetos, 4,569 MESH, 951 CURVE y 1,660 FONT (ver `reports/z-anatomy-blend-inventory.json`). Los dos GLB localizados previamente no son referencia validada para selección anatómica individual.

## Estado y siguiente acción

Fuente localizada y auditada. La propuesta de pelvis contiene 26 objetos (18 MESH, 8 CURVE). Correspondencia léxica TA2 única 26/26 y lateralidad preliminar coherente en 18 objetos bilaterales. Se exportó `reports/experimental/pelvis-baseline-uncompressed.glb` (682,900 bytes) y su validador de identidades obtuvo PASS (26/26). Reportes: `reports/pelvis-ta2-crosswalk.json`, `reports/pelvis-spatial-curve-audit.json`, `reports/pelvis-catalog-candidate.json`, `reports/pelvis-baseline-export-report.json` y `reports/pelvis-baseline-validation.json`. Etapa 6: variante experimental PBR core de 681,492 bytes con la misma geometría e identificadores, contrato wgpu WebGPU/WebGL2, perfiles de calidad y propuesta LOD: solo dos estructuras candidatas a simplificar. `reports/stage6-contract-validation.json` confirma PASS_DESIGN_ONLY (12 invariantes). Etapa 7 cerrada: arquitectura y plan de implementación M00–M06, contrato del bridge y ADR definidos; `reports/stage7-blueprint-validation.json` obtuvo PASS_DESIGN_ONLY (21 verificaciones). La implementación 01 realizó M00–M02: Rust/wgpu WebGPU+WebGL2, motor WASM, carga real de 26 IDs, cámara y selección. Auditoría independiente de 2026-11-09: 18/18 tests Rust y ambos backends de Chrome headless PASS local; corregidos ray/AABB, listeners de canvas y rustfmt. Ver `docs/AUDITORIA_IMPLEMENTACION_01.md` y `reports/audit/audit-implementation-01-verdict.json`. M04 implementado parcialmente y auditado: manifiesto y catálogo SHA, cargas por generación, caché de geometría y compatibilidad dual funcionando; recursos/evicción y recuperación real aún incompletos. No se diseñó ni implementó M05 en esta auditoría. Ver `docs/AUDITORIA_IMPLEMENTACION_03.md`. M05–M06 permanecen pendientes, licencias y validación clínica pendientes.
