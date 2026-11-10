# Etapa 6 — Especificación de renderizado Rust/wgpu v1

**Estado:** diseño cerrado para prototipo, sin shaders compilados ni runtime implementado (2026-11-09).

## 1. Evidencia experimental de la pelvis

Fuente original `reports/experimental/pelvis-baseline-uncompressed.glb`:
- 26 nodos anatómicos seleccionables, 26 meshes, 27 primitives, **38,605 triángulos indexados** (no confundir con los 25,717 polígonos de Blender, algunos eran quads).
- Todas las primitives son `mode=4` (triángulos).
- Atributos `POSITION` y `NORMAL` en las 27; índices `UNSIGNED_SHORT` (glTF 5123) en las 27.
- 10 materiales, 0 texturas, 0 animaciones, 0 skinning, 0 morph targets y 0 colores de vértice.
- Extensiones usadas por materiales originales: `KHR_materials_specular` y `KHR_materials_ior`; NO están en `extensionsRequired`.
- Varios materiales originales poseen metallic >0, incluido nervio 0.897 y hueso 0.490; para la visualización médica se prefirió un perfil mate.
- El perfil compatible `reports/experimental/pelvis-pbr-core-compat.glb` ocupa **681,492 bytes**; elimina esas extensiones opcionales y fija metallic=0 con roughness por categoría, conservando colores base, alpha, culling, nodos y payload binario **idénticos**.
- `tools/verify_pbr_core_fixture.py` verificó identidad y conservación binaria: **PASS**, NO prueba visual.
- Informes: `reports/graphics-baseline-audit.json`, `reports/pelvis-pbr-compat-report.json`, `reports/pelvis-pbr-compat-validation.json`.

## 2. Objetivo del motor

Un único núcleo Rust con wgpu; dos adaptadores/builds web cuando sea necesario:
- Principal: WebGPU nativo del navegador.
- Compatible: wgpu/WebGL2, probando explícitamente límites de `wgpu::Limits::downlevel_webgl2_defaults()`.
- Selección de backend por prueba REAL de adaptador, dispositivo y pipelines, no solamente por `navigator.gpu`.
- WebGL2 es best-effort y tiene funcionalidad reducida frente a WebGPU. No prometer compatibilidad universal.
- Preferir WGSL; no asumir que un shader WGSL válido se traduce automáticamente en GLSL ES 3.00 válido: probar ambos.
- Evitar construcciones fuera del perfil mínimo: compute, storage buffers, push constants, GPU-driven indirect draw, geometría teselada en GPU.
- No utilizar `@interpolate(linear)` (noperspective), que puede fallar en GLSL ES/WebGL2; usar interpolación de perspectiva predeterminada.

Documentación de plataforma:
https://wgpu.rs/doc/wgpu/documentation/platforms/web/index.html
https://wgpu.rs/doc/wgpu/struct.Limits.html
https://wgpu.rs/doc/wgpu/documentation/shaders/index.html

## 3. Contrato de vértices e índices

- Atributo 0: posición world-local, `float32x3`.
- Atributo 1: normal local, `float32x3`.
- Índices aceptados: `u16` y `u32` (fixture actual es `u16`). Modo triángulos.
- Los buffers se generan desde glTF tras validar cada accessor, offset, stride, count, índice y valores finitos.
- Tras importar, no perder el mapa `RenderPart -> AnatomyId`. Una estructura puede contener múltiples primitives.
- glTF y los nodos usan coordenadas con +Y superior. Para normales, usar la matriz normal (inversa transpuesta de transform 3x3).
- Primera versión: modo interleaved opcional, NO requerir formato binario propietario.

## 4. Uniformes propuestos

**Bind group 0 — Camera**: `viewProjection` (mat4), posición de cámara y valores auxiliares alineados.

**Bind group 1 — Object**: `model` (mat4), `normalMatrix` (mat3 empaquetada en vec4s para alineación), flags de selección.

**Bind group 2 — Material/Lighting**: `baseColorFactor`, `roughness`, `metallic` (el fixture usa 0), iluminación (dirección + intensidad + fill) y opacidad visible.

- Usar buffers uniformes pequeños; no storage buffers ni texturas obligatorias.
- Respetar alineación exigida para uniform dynamic offsets cuando se active; la primera versión puede usar buffers por objeto/pipeline simples.
- React no toca uniformes GPU; Rust es dueño de cámara, escenas y recursos.

## 5. Shaders mínimos — especificación, sin implementación

### Vertex
Entrada POSITION/NORMAL; calcula clipPosition = viewProjection × model × position; produce normal normalizada transformada y coordenadas apropiadas. Respeta inversión de normales en transformaciones reflejadas.

### Fragment opaque
Lee baseColor linealizado, normal interpolada, luz direccional + relleno/ambiente y roughness. Produce salida con tratamiento sRGB correcto. Primera versión permite iluminación difusa de estudio con especular sutil, NO afirmar equivalencia visual exacta al BRDF PBR completo de glTF. El contrato de materiales core ya queda preservado para futura implementación GGX.

### Highlight
Resaltado del seleccionado con tinte turquesa/contorno discreto activado solo cuando hay selección. No depender de readback GPU síncrono ni de postprocesado obligatorio.

### Transparency
Fuera del G1: si se incorpora en G2, blending alfa con ordenación aproximada por profundidad, limitaciones documentadas. No prometer orden-independiente/OIT sin diseño y prueba.

### Depth/culling/output
- Depth24Plus y surface SRGB preferidos, sujetos a capabilities reales.
- El fixture original marca todos los materiales como doubleSided; mantenerlo primero y evaluar backface culling donde la malla sea cerrada y verificable.
- Precisión de colores médicos entre modo claro y oscuro; solo ambiente/contraste del fondo cambia, no colores anatómicos del modelo.
- Render bajo demanda al estar la cámara quieta.

## 6. Frame lifecycle

`Initializing -> LoadingScene -> Ready -> RenderingOnDemand`; `Suspended/DeviceLost -> Recovering -> Ready`; `Failed` recuperable o no según código.
- Marcar frame dirty cuando cambia cámara, selección, estado de visibilidad, tamaño o recurso residente.
- Controlar DPR y tamaño real en píxeles: limitar al máximo permitido por la GPU.
- No ejecutar 60 FPS en escena estática.
- Subidas GPU y decodificaciones tienen presupuesto por frame.
- No aumentar la memoria para precargar LOD no visibles sin beneficio medido.

## 7. Política de errores y fallback

Fallos durante inicialización WebGPU (incluida creación de shaders/pipelines) -> probar WebGL2 cuando esté compilado y disponible; si falla, reportar `GPU_UNAVAILABLE` con alternativa UI.
Nunca esconder errores de shader como una pantalla negra.
Un asset con extensión requerida no soportada -> `ASSET_UNSUPPORTED_EXTENSION`, nunca ignorar silenciosamente.
Material con extensión opcional desconocida: usar valores core si son semánticamente coherentes y registrar degradación.
Si un recurso deja de ser residente no eliminar su identidad de catálogo.

## 8. Pruebas de aceptación

Referencia ejecutable en `contracts/renderer-acceptance-v1.json`.
- R00 baseline: PASS.
- R01 PBR core + geometry identical: PASS.
- R02 WGSL + pipelines reales en WebGPU y WebGL2: NOT_RUN.
- R03/R04 render real en ambos backends: NOT_RUN.
- R05–R12 selección, LOD, gestión GPU, memoria y rendimiento: NOT_RUN.
- R13 licencia individual: BLOCKED.
- R14 precisión anatómica: PENDING.

**No declarar backend WebGL2 aprobado hasta visualizar realmente este GLB en navegador y medir el frame.**

## 9. Contratos máquina-legibles
- `contracts/render-profile-v1.json` = conjunto de features y estructura GPU.
- `contracts/quality-profiles-v1.json` = hipótesis de rendimiento y presupuestos.
- `contracts/renderer-acceptance-v1.json` = pruebas/pasos mínimos y estados verificados.

## 10. Siguiente acción de ingeniería

Prototipo Rust/wgpu mínimo: dibujar el GLB core PBR en WebGPU/WebGL2, cámara orbit, pick CPU por AnatomyId, ocultar/aislar y registrar trazas. No optimizar a ciegas antes de medir. El primer prompt podrá centrarse exclusivamente en ese alcance.
