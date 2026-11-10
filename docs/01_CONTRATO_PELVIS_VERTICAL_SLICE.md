# Contrato de validación — Pelvis Vertical Slice v1

**Estado:** propuesta verificable, pendiente de fuente anatómica y benchmark. **Alcance:** una región, motor mínimo, procesamiento reproducible y una UI de prueba, NO atlas completo.

## 1. Resultado indispensable
Desde un GLB anatómico legítimo con mallas separadas, el sistema:
1. Inventaría y valida una selección representativa de estructuras de la pelvis.
2. Produce un paquete GLB base, un catálogo y al menos un LOD alternativo.
3. Carga en Rust/WASM y presenta un fotograma WebGPU o WebGL2.
4. Permite rotar, desplazar, zoom, tocar/seleccionar, enfocar, ocultar, aislar y restaurar.
5. Cambia LOD sin perder identidad ni controles.
6. Reusa contenido descargado cuando la caché está disponible.
7. Se recupera de red fallida y de context loss cuando el backend lo permite.

## 2. Fixture anatómico de referencia
Se identificaron 26 objetos existentes como candidato inicial en `reports/pelvis-fixture-candidate.json` (18 MESH y 8 CURVE, 17,221 polígonos MESH nominales sin incluir teselado de curvas). Este es un inventario de nombres existentes, NO un fixture exportado ni validado anatómicamente. Debe incluir cuando existan:
- pelvis ósea izquierda y derecha;
- sacro o estructura ósea central;
- vejiga y recto;
- vasos ilíacos/femorales de distinto calibre;
- nervios visibles de pequeño diámetro;
- una estructura genital propia de la variante;
- mallas con 1 y varias primitives.

**No inventar estructuras ausentes.** Si la fuente no reúne estas categorías, se documentará una excepción justificada o se buscará una segunda fuente con licencia compatible. La anatomía femenina no es condición de arranque del motor si falta material autorizado; su representación se añadirá tras validar la base.

## 3. Invariantes
- Cada estructura tiene `anatomy_id` estable, único en catálogo, independiente del índice de nodo glTF.
- Una estructura puede contener N primitives; varias estructuras NO comparten una unidad inseparable de visibilidad.
- Cada LOD preserva el mismo conjunto de IDs requeridos o declara un sustituto seleccionado de manera explícita y validada.
- Ocultar/aislar/seleccionar funciona sobre todas las primitives de un `anatomy_id`.
- Coordinadas de publicación en metros, +Y superior, +Z anterior, +X izquierda anatómica, transformaciones validadas.
- Información de fuente y licencia por asset antes de publicar, no solo en el README.
- Ningún archivo externo ni shader suministrado por GLB remoto puede ejecutarse arbitrariamente.
- El cambio de región o variante nunca mezcla generaciones de escenas.
- El primer fotograma no depende de haber descargado LOD altos.

## 4. Entrega de builder
- `manifest.json` conforme al esquema `contracts/atlas-manifest.schema.json`.
- `catalog.json` con ids, nombre, sistema, región, lateralidad y vínculos de representación.
- Paquetes `*.glb` verificables por SHA-256.
- `build-report.json` con mapa `source_object -> anatomy_id -> package/node -> LOD`, conteos y reducción.
- `license-report.json` con procedencia y estado de publicación de cada fuente.
- `validation-report.json`: errores y advertencias estructurales/anatómicas, pruebas de round-trip.

## 5. Entrega de motor
- Shell web mínimo, sin diseño UI final.
- Backend WebGPU y fallback WebGL2 seleccionados por capacidades, con errores tipados.
- Scene graph, renderer básico, input, selección y gestión de recursos.
- Control de visibilidad por ID y enfoque sin recalcular geometría en React.
- Máquina de estados de assets y token `scene_generation` para descartar cargas tardías.
- LOD básico con cambio atómico; no streaming fino de geometría dentro de un GLB en esta etapa.
- Diagnóstico básico: backend, fps/frame-time, tris, draws, ocupación estimada y duración de carga.

## 6. Exclusiones deliberadas
No backend de usuarios, cuentas, pagos, ECS genérico, animación ósea, ray tracing, OIT, corte avanzado, IA, radiología, modo examen, apps nativas ni empaquetado de cuerpo entero.

## 7. Puertas de aprobación (go/no-go)
- **G0/Fuente:** identificadores por estructura, licencia verificable, fixture documentado.
- **G1/Gráficos:** escena visible en Chrome/Edge WebGPU y al menos una ruta WebGL2 válida, sin pantalla negra.
- **G2/Identidad:** selección/ocultación de todas las estructuras del fixture; 0 IDs duplicados o perdidos.
- **G3/Integridad:** GLB + catálogos + SHA-256 consistentes y validables de forma automatizada.
- **G4/Interacción:** controles táctiles/mouse sin bloqueo durante cargas y cambios LOD.
- **G5/Resiliencia:** navegación rápida, caché ausente, red interrumpida y paquete corrupto no corrompen escena.
- **G6/Rendimiento:** métricas y presupuesto aprobados con mediciones en hardware físico definido.

Si cualquier gate bloqueante falla, no se ampliará el atlas ni se optimizará a ciegas. Corregir en el prototipo y repetir el gate.
