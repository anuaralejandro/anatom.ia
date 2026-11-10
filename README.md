# anatom.ia — Atlas Engine

**Estado (2026-11-09): M00–M02 IMPLEMENTADOS Y AUDITADOS para prototipo local. M03 Atlas Builder pendiente. No existe frontend React definitivo ni backend convencional. Prohibida publicación de los assets sin auditoría legal/clínica.**

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

Fuente localizada y auditada. La propuesta de pelvis contiene 26 objetos (18 MESH, 8 CURVE). Correspondencia léxica TA2 única 26/26 y lateralidad preliminar coherente en 18 objetos bilaterales. Se exportó `reports/experimental/pelvis-baseline-uncompressed.glb` (682,900 bytes) y su validador de identidades obtuvo PASS (26/26). Reportes: `reports/pelvis-ta2-crosswalk.json`, `reports/pelvis-spatial-curve-audit.json`, `reports/pelvis-catalog-candidate.json`, `reports/pelvis-baseline-export-report.json` y `reports/pelvis-baseline-validation.json`. Etapa 6: variante experimental PBR core de 681,492 bytes con la misma geometría e identificadores, contrato wgpu WebGPU/WebGL2, perfiles de calidad y propuesta LOD: solo dos estructuras candidatas a simplificar. `reports/stage6-contract-validation.json` confirma PASS_DESIGN_ONLY (12 invariantes). Etapa 7 cerrada: arquitectura y plan de implementación M00–M06, contrato del bridge y ADR definidos; `reports/stage7-blueprint-validation.json` obtuvo PASS_DESIGN_ONLY (21 verificaciones). La implementación 01 realizó M00–M02: Rust/wgpu WebGPU+WebGL2, motor WASM, carga real de 26 IDs, cámara y selección. Auditoría independiente de 2026-11-09: 18/18 tests Rust y ambos backends de Chrome headless PASS local; corregidos ray/AABB, listeners de canvas y rustfmt. Ver `docs/AUDITORIA_IMPLEMENTACION_01.md` y `reports/audit/audit-implementation-01-verdict.json`. Siguiente M03, prompt guardado en `docs/PROMPT_02_ANTIGRAVITY_M03.md`. M04–M06 aún no implementados, licencias y validación clínica pendientes.
