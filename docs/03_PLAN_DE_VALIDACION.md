# Matriz de validación — Pelvis Vertical Slice

## A. Fixtures
- **golden-synthetic:** primitivas simples y estructuras diferenciadas para test independiente de Z-Anatomy.
- **pelvis-real:** 15–30 estructuras originales con fuente/licencia documentadas, incluidas partes pequeñas.
- **broken:** manifiesto inválido, SHA discrepante, índices glTF corruptos, GLB truncado, extensiones incompatibles.
- **lod-crosswalk:** misma lista de anatomy IDs en todos los LOD exportados.
**Regla:** fixture sintético prueba infraestructura pero NO acredita fidelidad anatómica.

## B. Pruebas automatizadas mínimas
| ID | Área | Prueba | Éxito |
| --- | --- | --- | --- |
| T01 | Esquema | Manifest y catálogo validables | 0 errores |
| T02 | Integridad | SHA y tamaños antes de activar assets | mismatch rechazado |
| T03 | Anatomía | correspondencia ID fuente→LOD | 0 estructuras perdidas |
| T04 | Render | imagen visible en WebGPU | sin error GPU |
| T05 | Fallback | imagen visible WebGL2 | sin función obligatoria incompatible |
| T06 | Selección | cada objeto del fixture seleccionable | 100% correcto fixture |
| T07 | Visibilidad | hide/isolate/reset y piezas multipart | 100% coherente |
| T08 | LOD | cambio atómico, cámara persistente | sin parpadeo por ausencia de malla |
| T09 | Carrera | cambio de región durante descarga | generación anterior no muta escena |
| T10 | Red | offline, timeout, paquete truncado | error recuperable |
| T11 | GPU | pérdida y recuperación de dispositivo | sin estado lógico corrupto |
| T12 | Memoria | cambios repetidos de región | consumo converge tras liberación |
| T13 | Origen | fuente y licencia por asset | no publicar archivos no auditados |
| T14 | Accesibilidad | controles táctiles/teclado, tema | acciones críticas accesibles |

## C. Matriz de dispositivos
- PC de desarrollo: RTX 4070 Laptop; ejecutar además con Intel UHD cuando sea posible.
- Windows: Chrome/Edge WebGPU y WebGL2 forzado.
- Android de entrada: dispositivo físico con GPU limitada (por adquirir/seleccionar); Chrome.
- Android medio/alto: físico; Chrome.
- iPhone: Safari en hardware real, incluyendo versión antigua soportada.
- Red de prueba: cold-cache y warm-cache; Wi-Fi estable, throttling, offline y red intermitente.
- No afirmar 30/60 FPS universal sin resultados físicos.

## D. Telemetría de pruebas
Por escenario registrar `device`, `OS`, `browser`, `backend`, `quality`, `resolution`, `scene_hash`, `cache_state`, `network_profile`, `first_frame_ms`, `ready_ms`, `fps`, `frame_p50_ms`, `frame_p95_ms`, `interaction_p95_ms`, `draw_calls`, `triangles`, `cpu_mem_estimate`, `gpu_mem_estimate`, `error_count`.
La memoria GPU será estimada por recursos propios; no afirmar VRAM total exacta del navegador.

## E. SLO candidatos, NO resultados
- Gama baja: frame p95 ≲ 33.3ms en interacción en escena de referencia.
- Gama media: frame p95 ≲ 22.2ms como meta inicial de 45 FPS.
- Gama alta: frame p95 ≲ 16.7ms como meta inicial de 60 FPS.
- Selección con estructura residente: latencia p95 <100ms.
- 0 errores de integridad de IDs y hashes.
- First frame útil tras warm-cache: meta <1000ms, sujeta a tamaño de asset/dispositivo.
- Decisiones de release basadas en métricas reales, no solo promedios.

## F. Gate report
Cada gate documenta:
1. Resultado: PASS / FAIL / BLOCKED.
2. Dispositivo y escena exacta.
3. Evidencia reproducible: comando, log, screenshot o test report.
4. Regresión respecto a benchmark anterior.
5. Responsable de corrección y criterio de re-ejecución.

Un gate bloqueado por ausencia de archivo fuente no se marca PASS con datos sintéticos.
