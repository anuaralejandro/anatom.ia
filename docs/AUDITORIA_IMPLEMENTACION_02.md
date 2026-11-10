# Auditoría independiente M03 — anatom.ia
**Fecha:** 2026-11-09 · **Veredicto:** PASS_CORRECTED — GO_M04_LOCAL_ONLY · **Producción:** BLOCKED

## Conclusión
El Atlas Builder de Antigravity sí emite GLB estándar compatibles y un LOD de pelvis utilizable, pero la auditoría reveló fallos materiales de reporte, calidad, seguridad y reproducibilidad. Se aplicaron cambios mínimos y se repitieron los tests; los binarios originales no se modificaron. Esta auditoría prevalece sobre cualquier afirmación histórica incorrecta en `docs/IMPLEMENTATION_02_RESULT.md`.

## Defectos identificados
1. **Falsa medición perceptiva:** `tools/calculate_lod_metrics.py` proyectaba únicamente esquinas de AABB; no rasterizaba contornos. Su cifra p95=0.01px **NO** medía silueta real. Se degradó su salida a `NOT_EVALUATED_BOUNDING_BOX_PROXY_ONLY`; se agregó un evaluador independiente de máscaras reales de triángulos.
2. **Triángulos contradictorios:** el informe mezclaba polígonos de Blender (29,210→25,542) con triángulos glTF efectivos. Datos comprobados de los GLB: **38,605→33,758**, reducción **12.56%**, con 26 ID anatómicos.
3. **Build no reproducible desde fuente:** `build.rs` reutilizaba silenciosamente staging, y usaba un GLB M02 experimental como fallback. Ahora cada build vuelve a ejecutar Blender normalizado y LOD1; falla de forma explícita si no puede producir los assets.
4. **Dependencia de red encubierta:** `npx.cmd --yes gltfpack` no cumple offline. Se eliminó; meshopt sigue opcional exclusivamente con `ATLAS_GLTFPACK_BIN` apuntando a un ejecutable local; sin él se construyen solo LOD0 y LOD1 core.
5. **Informe de calidad falsificable:** `report.rs` fabricaba un `PASS` con métricas estáticas cuando faltaba evidencia; y reutilizaba quality-report antiguo. Ahora exige `silhouette-audit.json`, `PASS_MEASURED`, rasterizado real y SHA-256 de AMBOS GLB coincidentes; de lo contrario `NOT_RUN`/UNVERIFIED. Se eliminó fecha fija simulada.
6. **Seguridad de rutas:** `validate.rs` marcaba path traversal pero continuaba intentando leer el archivo. Ahora rechaza antes de acceso y revisa rutas canónicas para impedir escapar por symlinks/junctions. Exige contenido de catálogo válido y mismos 26 IDs etiquetados en los GLB core.
7. **Prueba que pasaba silenciosamente sin artefactos:** `builder_tests.rs` ya no presenta como validación de release una salida ausente; comprueba explícitamente rechazo de ausencia.

## Mediciones independientes
- **QA 3D proyectada:** `tools/audit_lod_silhouettes.py`. Genera máscaras binarias rasterizando **triángulos reales** de sacro y vejiga a 1280×720 en cinco vistas (anterior, oblicua, posterior, inferior, superior).
- 10 comparaciones; correspondencia 26/26 IDs; IoU mínimo de máscara **0.993367**, máximo **0.999623**; distancia máxima simétrica de borde **1 píxel** en todas las vistas. El p95 puede ser 0 a resolución de píxel porque la mayoría de los bordes coinciden; evitar interpretarlo como error físico subpíxel.
- Aún falta revisión clínica de articulaciones, lumen/topología y geometría interna: esta medición no implica validación científica independiente.
- **Reconstrucción limpia** desde `Startup.blend`: `build/atlas/audit-m03-rebuild-a`; SHA256 original y reconstruido coinciden:
  - LOD0 `1510ed9a93b54c8067543b4a13e92ee713f1d75adc2687324ad29a72b76244ae`
  - LOD1 `4c1054b116b972be97ed367cb4d0a7242098c92d31e094d2127b621168346391`
- `atlas-builder validate`: **PASS** 22 comprobaciones en release regenerado de dos paquetes; release histórico de tres paquetes PASS 27 comprobaciones; meshopt histórico **no es decodificable** por el visor M02.
- **Navegador independiente:** `tools/audit_m03_browser_dual.py` ejercitó LOD0 y LOD1 × WebGPU y WebGL2: **4/4 PASS**, cargando las URL correctas `pelvis-base-lod0.glb` y `pelvis-lod1.glb` (HTTP 200), 26 controles TA2, aislamiento/restauración, sin errores de página.
- **Rust/CI local:** `cargo fmt --all -- --check`, `cargo clippy --workspace --all-targets -- -D warnings`, `cargo test --workspace` (23/23), `cargo check --target wasm32-unknown-unknown --workspace --exclude atlas-builder`: PASS; validadores históricos etapas 5–7 PASS.
- **Upstream:** `git -C sources/z-anatomy-upstream status --porcelain` sin diferencias.

## GitHub
- Repo conectado: `https://github.com/anuaralejandro/anatom.ia`, público, rama `main`, commit de origen de auditoría `dbca7b75edf9723ddbef856912dc67dae9c2e2ec`.
- Se **NO** realizó commit, push, cambios de ramas remotas, publicación de GLB ni despliegue.
- GitHub no versiona GLB/BLEND en el árbol inspeccionado. Sin embargo, los reportes, catálogos y capturas derivados **sí están publicados**. Revisar condiciones de atribución y permiso antes de distribuir imágenes o modelos adicionales; el valor false en `commercial_release_allowed` no cambia permisos legales.
- Verificar los cambios locales antes de crear commits/push. No publicar los assets originales ni derivados sin autorización específica.

## Gates y deuda pendiente
- **G03_BUILDER_REPRODUCIBILITY:** PASS (rebuild regenerado desde Blender con SHA idéntico).
- **G03_PBR_COMPAT:** PASS (LOD0/LOD1 core parseable y pruebas reales en WebGPU/WebGL2).
- **G03_LOD_FIDELITY:** PASS_TÉCNICO_LIMITE para estas dos estructuras y cinco vistas; clínica **NOT_RUN**.
- **G03_RUNTIME_NONREGRESSION:** PASS (23 tests, WASM, render dual).
- **G03_LEGAL_CLEARANCE:** BLOCKED.
- No es validación completa de JSON Schema de publicación ni de licencias individuales. No hay tests físicos iOS/Android, consumo GPU real o escenarios M04 de red/caché.

**Decisión:** Autorizar implementación M04 **en entorno local**, estrictamente sin redistribuir assets ni publicar productos. El siguiente prompt debe partir del estado local auditado, no sobrescribir correcciones ni alterar `sources/`.
