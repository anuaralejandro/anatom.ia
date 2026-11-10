# ANTIGRAVITY — anatom.ia — IMPLEMENTACIÓN CONTROLADA 01 (M00–M02)

Actúa como ingeniero principal de gráficos en tiempo real, Rust/wgpu/WebAssembly, ingeniería de build y pruebas automatizadas. Trabaja DIRECTAMENTE en la máquina local. Esta es una tarea de IMPLEMENTACIÓN REAL, no de redacción de un plan, maquetas ni pseudocódigo.

RAÍZ ÚNICA DEL PROYECTO:
C:\Users\datam\Documents\anatom.ia

PROPÓSITO:
Implementar y demostrar el primer vertical slice real del atlas anatómico 3D anatom.ia: motor Rust con wgpu, renderizado web mediante WASM con rutas WebGPU y WebGL2, y un shell mínimo para inspeccionar y manipular 26 estructuras de pelvis extraídas de Z-Anatomy. No construyas todavía el atlas completo ni el frontend final.

REGLA MÁS IMPORTANTE:
NO declares una tarea como terminada sin código ejecutable y evidencia de tests. No sustituyas Rust por Three.js/Babylon ni finjas un fallback WebGL2. No inventes capturas, cifras de FPS, pruebas ni permisos. Si alguna prueba no se puede ejecutar, marca NOT_RUN/BLOCKED con causa, conserva lo que sí funciona y continúa con las partes comprobables.

## 0. INSPECCIÓN OBLIGATORIA ANTES DE EDITAR

Lee primero, íntegramente y en este orden:
1. README.md
2. docs/09_BLUEPRINT_IMPLEMENTACION.md
3. docs/10_ADR_GATES.md
4. docs/07_RENDERER_WGPU_SPEC.md
5. docs/08_LOD_PICKING_TEST_PLAN.md
6. docs/01_CONTRATO_PELVIS_VERTICAL_SLICE.md
7. docs/02_CONTRATOS_TECNICOS.md
8. contracts/implementation-milestones-v1.json
9. contracts/engine-bridge-v1.json
10. contracts/render-profile-v1.json
11. contracts/quality-profiles-v1.json
12. contracts/renderer-acceptance-v1.json
13. contracts/atlas-manifest.schema.json
14. reports/pelvis-baseline-validation.json
15. reports/pelvis-pbr-compat-validation.json
16. reports/pelvis-catalog-candidate.json
17. reports/stage7-blueprint-validation.json

Inspecciona la estructura actual de carpetas. NO supongas que ya hay una aplicación, un Cargo workspace o un backend. Verifica las versiones y herramientas realmente instaladas.

Modelo de entrada para pruebas LOCALES:
reports/experimental/pelvis-pbr-core-compat.glb

Referencias intactas:
reports/experimental/pelvis-baseline-uncompressed.glb
sources/z-anatomy-upstream/
sources/z-anatomy-template/Z-Anatomy/Startup.blend

Datos verificados:
- El GLB compatible mide 681,492 bytes.
- Contiene 26 estructuras con extras.atlas_id persistente, 26 meshes, 27 primitives y 38,605 triángulos glTF indexados.
- 10 materiales PBR core, sin texturas, sin skinning y sin morph targets.
- Atributos POSITION y NORMAL, índices u16, primitivas TRIANGLES.
- SHA-256 del GLB compatible: 405da36949f511b197291f2b1274d5fcdd340bb2a31d9042ee2648f8782c5797.
- El original de Z-Anatomy contiene materiales y geometría sujetos a revisión de licencia. SOLO usar estos fixtures para desarrollo/validación local; NO distribuirlos ni publicarlos.

ANTES DE CAMBIAR NADA ejecuta y registra los validadores existentes:
python tools/verify_pelvis_baseline.py
python tools/verify_pbr_core_fixture.py
python tools/validate_stage6_contracts.py
python tools/validate_stage7_blueprint.py

Si cualquiera falla, investiga y documenta la causa. No reescribas contratos ni manipules resultados para simular que pasan.

## 1. ALCANCE ESTRICTO

IMPLEMENTA SOLO:
M00 — workspace, toolchain y builds reproducibles;
M01 — motor mínimo wgpu, canvas y ambos backends web;
M02 — carga del GLB real, cámara, picking, selección, ocultar, aislar, enfocar, restaurar y shell temporal.

NO IMPLEMENTES:
M03 Atlas Builder productivo/LOD/meshopt; M04 caché multinivel/streaming completo; M05 React premium/PWA; M06 despliegue AWS o publicación. Tampoco autenticación, base de datos, IA, radiología, simulación, microservicios, nuevas APIs HTTP, React como renderer, ECS generalista o modelo femenino en esta corrida.

Un servidor de desarrollo Vite o estático ES aceptable solo para servir WASM y el fixture en localhost. NO cuenta como backend del producto.

## 2. M00 — PREFLIGHT Y WORKSPACE

Crea una estructura pequeña y explícita, compatible con los contratos:
- Cargo.toml / Cargo.lock (workspace)
- rust-toolchain.toml
- crates/atlas-core (Rust independiente del DOM)
- crates/atlas-web (adaptador wasm-bindgen + acceso a canvas)
- shaders/ (WGSL)
- apps/probe-web (HTML/TypeScript muy pequeño, no React)
- tests/ o ubicación equivalente de pruebas
- docs/BUILD.md (comandos exactos de Windows)
- reports/implementation/M00, M01, M02 (evidencias, logs y estados)

Mantén cambios dentro de la raíz anatom.ia, salvo instalación de componentes normales de Rust necesarias para compilar, que debes dejar registradas. Reutiliza dependencias existentes cuando sean compatibles. Confirma que rustc/cargo, node/npm, target wasm32-unknown-unknown y herramientas wasm-bindgen/wasm-pack están disponibles; si faltan, instala de forma segura las mínimas necesarias y fija versiones.

El contrato propone wgpu 30 como referencia, pero NO presupongas flags, nombres de API ni features concretas. Verifica documentación y compatibilidad reales de la versión seleccionada, especialmente WebGL2 en wasm32, y fija una versión compilable con lockfile. Si requiere corregir una decisión del contrato, documenta un ADR, justifica el cambio y actualiza tests; nunca cambies silenciosamente el contrato.

WebGL2 puede requerir una compilación WASM separada con features específicas. Prefiero DOS BUILD TARGETS claros (browser-webgpu y browser-webgl2) sobre una supuesta detección automática que siempre termina usando WebGPU. El núcleo Rust debe seguir siendo uno solo.

Crea scripts reproducibles (PowerShell/npm) para:
- preparar dependencias;
- build de ambos bundles WASM;
- arrancar probe-web local;
- ejecutar tests y verificaciones;
- mostrar en el probe qué backend realmente quedó activo.

GATE M00: código compila hasta donde el entorno permita, comandos documentados, fixture verificado, hashes registrados, workspace limpio sin modificar upstream. No declares que el navegador funciona en este gate.

## 3. M01 — RENDERIZADOR RUST/wgpu DUAL BACKEND

Implementa primero un triángulo/cubo sintético y solo después el GLB real.

Requisitos:
- Estado y renderer centralizados en Rust; atlas-core no puede importar web-sys ni manipular directamente el DOM.
- atlas-web expone inicialización asíncrona de un canvas, resize y eventos de pointer.
- Ruta principal WebGPU; ruta separada WebGL2 con límites downlevel_webgl2_defaults y features mínimas.
- Detección REAL: adapter, device, surface, formato, shaders, pipelines y primer draw. navigator.gpu NO demuestra que el backend funcione.
- Si WebGPU falla antes/durante inicialización, intento explícito de WebGL2; reconstruir canvas si el contexto anterior impide otro tipo de contexto. Mensaje de error legible si ambos fallan.
- Permitir forzar backend con selector o parámetro de URL: auto, webgpu y webgl2. Mostrar backend solicitado, backend efectivo y error real.
- Shader WGSL mínimo para POSITION/NORMAL, cámara/object uniforms y material base color. Usar pipeline compatible con WebGL2: sin compute, storage buffers, push constants, draw indirect, ni depender de texturas.
- Configurar depth correctamente, backface/doubleSided según material, DPR, resize y manejo de dispositivo perdido.
- No hacer conversiones sRGB dobles. Dibujar con colores anatómicos estables aunque cambie el color del fondo.
- Render-on-demand: escena quieta no debe continuar renderizando fotogramas sin necesidad; durante interacción sí debe responder fluidamente.
- No renderizado mediante Three.js, Babylon, WebGL JS manual ni otra pila paralela. JS/TS solo bootstrap/input/UI/probe.

GATE M01:
a) Build WASM WebGPU real;
b) Build WASM WebGL2 real;
c) primer objeto sintético visible en cada backend dentro del navegador;
d) sin pantalla negra ni error GPU silenciado;
e) evidencia guardada del backend efectivo, navegador, console logs y capturas REALMENTE obtenidas.

Compilar únicamente no permite marcar el gate de render como PASS. Si no puedes abrir navegador o comprobar WebGL2, declara gate BLOCKED/NOT_RUN según corresponda y deja todos los comandos para reproducirlo manualmente.

## 4. M02 — PELVIS REAL + INTERACCIÓN

Una vez aprobado el render sintético, cargar reports/experimental/pelvis-pbr-core-compat.glb.

Parser/geom:
- Leer GLB desde bytes, soportar su buffer BIN embebido; no depender de paths absolutos en runtime.
- Validar cabecera, chunks, índices, accessors, offsets/strides, tamaño, tipos, límites, valores finitos y extensiones. Rechazar archivos corruptos o abusivos sin panic ni asignación descontrolada.
- Procesar meshes, primitives, node transforms jerárquicos, normales con inverse-transpose, materiales core PBR y doubleSided.
- Mantener un AnatomyId por cada node extras.atlas_id (no usar como ID persistente el índice glTF). La correspondencia node -> mesh/primitive -> AnatomyId debe funcionar si una estructura tiene varias primitives.
- Soportar glTF TRIANGLES, POSITION+NORMAL y u16/u32 índices; otros formatos no soportados pueden dar error tipado sin romper el motor. No implementar decodificadores innecesarios que el fixture no usa.
- Comprobar tras cargar: 26 IDs distintos, 26 meshes, 27 primitives. No alterar los materiales de referencia durante esta fase.

Escena y cámara:
- Render de pelvis completa con fit-to-bounds real.
- Orbit con un dedo/botón principal, pan y pinch/rueda zoom, sin saltos al redimensionar.
- Controls en coordenadas CSS transformadas correctamente a framebuffer/DPR.
- Selección por raycasting CPU: broad-phase con AABB y narrow-phase triángulos; escoger la intersección visible más cercana, no el primer nodo del catálogo.
- La geometría puede permanecer en CPU para picking en este prototipo pequeño; gestiona esa memoria explícitamente.
- Soportar enfoques en nervios/vasos pequeños con un comportamiento razonable, documentando su tolerancia táctil.
- Métodos mínimos de bridge: initialize, loadRegion, selectAt, selectStructure, focusStructure, setVisibility, isolateStructure, resetVisibility, resetCamera, getSceneSnapshot, getCapabilities y dispose. Implementa solamente lo soportado por M02 sin fingir M04; si algún método del contrato requiere adaptación, documenta diferencia y razones.
- Eventos básicos: engine.ready, region.loading/ready, structure.selected, scene.changed y engine.error, con IDs y estados coherentes.
- No mantener la escena en TS. TS solo pinta panel de prueba y envía comandos al motor Rust.

Shell de prueba:
- Canvas casi full screen;
- fondo neutro con selector claro/oscuro básico (NO UI definitiva);
- selector forzado de backend;
- árbol/lista de las 26 estructuras por nombre español de catalog candidate, con TA2 ID;
- clic y toque para seleccionar, focus, hide, isolate, reset;
- indicador de backend, cantidad de primitivas/triángulos/drawcalls, frame time p50/p95 si medible;
- mensajes claros para loading/error;
- 2–3 escenas/cámaras diagnósticas reproducibles y capturas para comparación;
- visibilidad de prueba de glande, vejiga, sacro, ilíacas, nervios femorales y bilateralidad.

NO cambies sin control el esquema TA2: el archivo reports/pelvis-catalog-candidate.json es DRAFT y no constituye auditoría clínica. No muestres que existe anatomía femenina en este fixture.

GATE M02:
1) GLB real renderizado visualmente en WebGPU;
2) mismo GLB renderizado visualmente en WebGL2;
3) 26/26 AnatomyIds presentes y aislables;
4) selección geométrica correcta, incluyendo 1 estructura con varias primitives;
5) ocultar/aislar/restaurar coherente, sin perder la geometría;
6) controles orbit/pan/zoom mouse/touch y resize/DPR;
7) ninguna excepción no capturada al cargar GLB inválido;
8) screenshots, logs y test report reales.

Evita forzar 26 selecciones directas de objetos totalmente ocluidos como si eso probara raycasting: el test de picking debe usar cámaras/condiciones donde sean accesibles y además verificar oclusión.

## 5. PRUEBAS OBLIGATORIAS Y GUARDARRAÍLES

Como mínimo:
- cargo fmt --all -- --check
- cargo check --workspace (host o targets aplicables; registrar exclusiones)
- cargo test --workspace (pruebas que no requieran GPU real)
- cargo clippy en los targets que compilen, sin errores introducidos;
- build --release de cada WASM bundle;
- tests del parser GLB válido, truncado, índice fuera de rango, falta de NORMAL y extras ausentes;
- ray/triangle, AABB, nearest-hit, estructura invisible, selección bilateral;
- reproducción visual del GLB en WebGPU y WebGL2, cada uno CON EVIDENCIA;
- cambio de DPR/viewport y limpieza con dispose;
- no regresión de validadores de stages 5–7.

Prioriza calidad y portabilidad: sin unsafe innecesario, sin unwrap/expect sobre archivos remotos, sin bloqueos del hilo UI durante la carga cuando pueda evitarse, sin allocations enormes, sin copias duplicadas de la geometría por cada órgano.

No implementes capas de streaming/cache/LOD avanzadas ni afirmes soporte offline: fuera de M00–M02. Si surge un problema de rendimiento, mide primero y registra incidencia, no agregues un subsistema nuevo sin datos.

No modifiques archivos de fuentes/z-anatomy-upstream ni el .blend. No hagas git push, deploy, cambios AWS ni publicación web. Conserva la licencia original y las restricciones de no comercialización en los assets derivados. No borres resultados o trabajo existente sin necesidad.

## 6. EVIDENCIA Y REPORTE FINAL EXIGIDO

Actualiza ÚNICAMENTE los resultados que efectivamente hayas comprobado. Las pruebas R00/R01 existentes deben mantenerse; R02–R07 cambian a PASS solo si hay prueba real; R08–R14 seguirán NOT_RUN/BLOCKED/PENDING según su naturaleza. Un test unitario no acredita una prueba gráfica.

Crea:
- docs/IMPLEMENTATION_01_RESULT.md
- reports/implementation/M00/ (logs y entorno)
- reports/implementation/M01/ (builds, versiones, backend efectivo, capturas si existen)
- reports/implementation/M02/ (counts, test results, captures si existen)
- reports/implementation/implementation-01-status.json

El informe final debe incluir EXACTAMENTE:
A. Archivos nuevos/modificados, propósito y ruta;
B. Versiones exactas y comandos que realmente ejecutaste;
C. M00: PASS/FAIL/BLOCKED con evidencias;
D. M01 WebGPU: PASS/FAIL/NOT_RUN y WebGL2: PASS/FAIL/NOT_RUN POR SEPARADO;
E. M02: resultados de render, selección, orbit, hide/isolate y pruebas negativas;
F. Errores, limitaciones y deuda técnica comprobada;
G. Qué falta para completar M00–M02;
H. Qué NO implementaste por estar fuera de alcance;
I. Cómo abrir el probe en mi PC con comandos reproducibles;
J. Riesgos de regresión y confirmación de fuentes Z-Anatomy intactas.

Imprime al final un resumen compacto, sin autocalificarse como producción, con una tabla de gates. No des por terminada la tarea porque 'compila': ejecuta todo lo posible en este equipo. Si no tienes acceso interactivo al navegador, deja el servicio de desarrollo utilizable, instrucciones concretas y los gates gráficos como NOT_RUN.

## 7. PROTOCOLO DE TRABAJO

1. Leer archivos y ejecutar validadores antes de editar.
2. Establecer microplan M00→M01→M02 basado en código real observado.
3. Implementar M00 completamente y comprobarlo.
4. Implementar M01 con render sintético y comprobar ambos backends.
5. Implementar M02 con GLB y selección; comprobarlo.
6. Corregir problemas detectados, no esconderlos.
7. Ejecutar suite de regresión de proyecto y herramientas existentes.
8. Generar evidencias y reportar explícitamente lo pendiente.

No preguntes al usuario por detalles que están en estos documentos. Toma decisiones técnicas pequeñas cuando sea razonable, deja ADR para cambios de arquitectura y limita el trabajo a M00–M02.

PRIORIDAD DE CALIDAD:
funcionamiento real > compilación > pruebas verificables > claridad de código > optimización posterior > estética temporal.

ENTREGA ESPERADA:
Un primer visor anatómico de pelvis genuinamente operativo en Rust/WASM, con dos rutas gráficas cuando el entorno las soporte, integración temporal mínima y una auditoría final verificable. Ningún éxito inventado.
