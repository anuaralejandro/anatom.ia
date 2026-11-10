# Etapa 6 — Política LOD, picking y pruebas visuales

**Estado:** especificación y propuesta medible, **sin LOD alternativos exportados ni tests GPU ejecutados**.

## 1. Punto de partida medido

`reports/pelvis-lod-policy-proposal.json` asigna una política a cada una de las **26 estructuras reales** del fixture. El GLB contiene **38,605 triángulos indexados**, 27 primitives y 681,492 bytes en la variante core PBR.

Resultados:
- LOD1: **solo dos candidatas** a simplificación: sacro (11,676 triángulos; ratio de exploración 0.65) y vejiga (3,036; ratio 0.75).
- LOD2: **solo sacro** como candidato (ratio exploratorio 0.35) sujeto a umbral visual y topológico.
- Nervios femorales (4,032 triángulos cada uno), arterias y venas siguen **sin simplificación** hasta probar preservación de calibre/continuidad.
- Restante anatomía pequeña usa la geometría base. Evitar duplicar LOD prácticamente idénticos.

**Los ratios son solo candidatos.** Deben medirse en píxeles y contra requisitos anatómicos. Un ratio que produce una deformación inaceptable se rechaza incluso si reduce muchos bytes.

## 2. Criterios de aceptación por clase

| Clase | LOD permitido | Restricción |
|---|---|---|
| Huesos grandes | Simplificación selectiva | Conservar silueta, superficies articulares y accidentes clínicamente relevantes |
| Órganos parenquimatosos | Simplificación moderada | Conservar bordes, relación con órganos vecinos, sin inversión de normales |
| Vasos y nervios | Base por defecto | Conservar continuidad, diámetro aparente y ramificaciones |
| Ligamentos finos | Base por defecto | No eliminar conexiones ni fusionar estructuras |
| Componentes de selección | Todos los LOD deben conservar IDs | `AnatomyId` nunca cambia |
| Textos/etiquetas | Solo UI HTML | No crear niveles LOD de triángulos de texto |

## 3. Métrica de error visual propuesta

Para cada LOD candidato:
1. Renderizar escenas con cámara idéntica, luminancia y material consistentes.
2. Comparar silueta contra LOD0 en vistas anterior, posterior, lateral y tres cuartos.
3. Punto de partida de tolerancia: desviación de silueta p95 ≤ **2 px** a viewport de prueba 720 px, sin dejar huecos relevantes.
4. Las estructuras delgadas/vasos/nervios tienen criterio más estricto de continuidad y diámetro, antes de cualquier porcentaje de simplificación.
5. Verificar cada LOD de manera aislada y junto a estructuras vecinas para detectar intersecciones.
6. Registrar *screen-space error* por distancia para seleccionar LOD en tiempo real.

Este umbral es una hipótesis de calidad que debe calibrarse en el prototipo, no un resultado actual.

## 4. Estrategia de buffers y paquetes

Para el prototipo se conserva un único paquete GLB con 26 IDs. En producción, separar por sistema/región/lod cuando lo justifiquen demanda y coste de peticiones.

- El catálogo permite que un `AnatomyId` tenga un número variable de primitives.
- `LOD0` siempre queda disponible como referencia.
- Solicitud LOD1 no elimina LOD0 hasta carga y validación completas, después se intercambia atómicamente.
- Mantener IDs para selección aunque geometría esté expulsada de memoria.
- Paquetes pequeños no requieren inmediatamente meshopt si ello añade trabajo desproporcionado de descompresión.
- gltfpack/meshoptimizer: preparar flags `-kn -ke` y probar que ningún ID o nodo se fusiona indebidamente; no aplicar de forma general hasta roundtrip. Para curvas conservar perfil/radio.

Referencia: https://meshoptimizer.org/gltf/

## 5. Picking CPU especializado en anatomía

Ruta: puntero táctil/ratón -> rayo mundo de cámara -> AABB de nodos visibles -> BVH o intersección triángulo en candidatos -> `AnatomyId` -> evento UI.

- Solo estructuras visibles, seleccionables y residentes en la escena actual.
- Intersección más cercana positiva; cuando existen empates priorizar profundidad real, no orden de catálogo.
- La escena inicial de 26 objetos permite probar raycasts sin BVH complejo; construir estructura espacial al superar presupuesto medido.
- Hit-tests de mallas multipart a nivel de primitive deben devolver el mismo AnatomyId estable.
- Para estructuras muy finas, aplicar tolerancia de toque razonable en píxeles y restringirla espacialmente; nunca seleccionar un objeto oculto.
- No usar lectura síncrona GPU en el camino principal.
- El aislamiento de una estructura no altera sus datos de geometría ni su ID.

## 6. Pruebas de picking y corrección

- Selección de 26 IDs en una vista/ángulos en los que sean accesibles, sin falsas equivalencias.
- Test lateralidad: arteria ilíaca izquierda y derecha, testículos, glándulas seminales y nervios femorales.
- Test de oclusión: una estructura detrás de otra no se selecciona por error.
- Test de transparencia cuando se implemente: documentar si permite 'pick through'.
- Test de coordenadas: viewport con DPR 1/2/3, canvas redimensionado, orientación horizontal y vertical.
- Test de cambios LOD: selección persistente por ID y ausencia de frames vacíos.
- Test táctil: pointer capture, multitouch pinch/pan, no doble disparo por gesture.
- Test de estrés: seleccionar y cambiar de sistema repetidamente sin acumulación de buffers.

## 7. Perfiles de calidad propuestos

Archivo `contracts/quality-profiles-v1.json`:
- **Bajo:** meta 30 FPS, resolución dinámica 0.65–0.85x, sin sombras ni postproceso, límite de recursos GPU propios ~64 MiB.
- **Medio:** meta 45 FPS, resolución 0.85–1x, GPU ~128 MiB.
- **Alto:** meta 60 FPS, multisample hasta 4 si soportado, GPU ~256 MiB.
- Límite de GPU es **residencia estimada del propio motor**, no VRAM total ni consumo completo del navegador. Valores ajustables tras mediciones.
- Rendering on demand cuando la escena esté quieta.
- Priorizar reducción de resolución y LOD antes de añadir memoria.

## 8. Matriz de fallos que debe probarse

| Caso | Resultado exigido |
|---|---|
| WebGPU disponible pero pipeline falla | Intentar WebGL2, reportar causa si ambos fallan |
| WebGL2 sin feature avanzada | Deshabilitarla sin romper escena base |
| Archivo GLB corrupto | Rechazo con error visible, escena conservada |
| Se cambia de región durante descarga | Token de generación descarta resultado obsoleto |
| GPU device lost | Recuperación y restauración de cámara/selección |
| Cuota caché excedida | Funcionamiento online sin persistencia obligatoria |
| Memoria bajo presión | Reducir LOD y liberar buffers no activos |
| Estructura fuera de cámara | No procesar draw, mantener ID y catálogo |

## 9. Puerta previa a implementación extensiva

No continuar a Atlas Builder total hasta completar:
- Un shader WGSL probado en ambos backends.
- Visualización básica con el GLB real, sin pantalla negra.
- Cámara orbit y selección por ID validadas.
- Calidad y FPS medidos al menos en PC con GPU integrada y móvil económico real.
- Integridad anatómica conservada y licencia verificada antes de publicar.

**Siguiente producto:** prototipo mínimo Rust/WASM y shell web temporal, no backend tradicional y no frontend final.
