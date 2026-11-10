# anatom.ia — M05-B: Plan maestro de integración React ↔ Rust/WASM (NO EJECUTADO)

Estado: PLAN v2, 2026-11-10. M05-A.1 superó las suites locales, pero el propietario rechazó seguir probando el Canvas 2D provisional y pidió el GLB real y una alternativa Studio estilo Blender. Se autoriza DESARROLLO LOCAL M05-B según docs/PROMPT_07_ANTIGRAVITY_M05B_REAL_3D.md, con FIRST REAL GPU FRAME como gate 1. Publicación/uso comercial NO autorizados.
Fuentes: docs/14_M05_D1_INTEGRATION_CONTRACT.md, docs/M04_RUNTIME_BRIDGE_CONTRACT.md, docs/12_M05_RESPONSIVE_DESIGN_SYSTEM_SPEC.md, docs/AUDITORIA_IMPLEMENTACION_05A_INDEPENDIENTE.md.

## B0. Gate previo
- Corregir F08–F12 (QA falso PASS, rAF en reposo, touch 44, modal focus, GPU badge falso) y F13–F15 documentados.
- Integración no debe iniciar mientras los controles de demo imiten operaciones 3D realmente inexistentes.
- Preservar todo el working tree local de M03/M04/M05, sin commit/push/merge no autorizado.

## B1. CanvasHost + instancias WASM
- Un AtlasEngine Rust/wgpu por canvas; cargar paquetes WebGPU y WebGL2 con import lazy, comprobar capabilities reales y fallback automático.
- Separar preview 2D del canvas que wgpu tomará para inicializar; nunca pedir context 2D y GPU sobre el mismo canvas después.
- ResizeObserver del stage, DPR/resolución acotados, pointer mapping CSS correcto, disposed idempotente y manejo de React StrictMode.
- Abrir/cerrar panel, cambiar tema, rotar pantalla o alternar calidad no crea otro engine ni pierde selección/cámara.
- Badge de backend sólo muestra motor real tras inicialización y primer frame validado.

## B2. Streaming de pelvis validada
- AssetStreamManager como único transport, manifest+catalog validados SHA/bytes/IDs por Rust y JS sin dos fuentes de verdad.
- Sólo pelvis variante male-adult, 26 estructuras TA2, LOD0 y LOD1 core PBR; no meshopt experimental ni regiones no disponibles.
- Abort individual/coalescing ya auditado, generation/requestId, cuota offline, caché segura y errores tipados; no fetch duplicados desde React.
- No publicar GLBs, blends ni capturas clínicas protegidas en GitHub público sin licencia/acreditación verificada.
- Evento region.ready después del primer frame aceptado; applyPackageBytes sólo significa submitted/pending, no ready.
- LOD swap conserva visibilidad, aislamiento, selección, cámara, IDs y revision sin estado mixto.

## B3. Comandos anatómicos completos
- Árbol↔canvas: selectStructure y selectAt sobre mallas reales, focusStructure, isolateStructure, setVisibility, resetVisibility.
- Camera presets, orbit/pan/zoom, quality low/medium/high con admisión memory presupuesto real; mouse, trackpad, touch, stylus/teclado con alternativas.
- Nombres oficiales, side, TA2 procedentes del catálogo; categorías sólo con taxonomía verificada y versionada. No heurísticas de palabras en español que clasifiquen huesos como órganos.
- Estados loading, verifying, preparing, firstFramePending, ready, error, recovering sin inventar porcentajes, contenido clínico o roles.

## B4. Recovery y PWA
- Bridge tipado con normalización única snake_case/camelCase, callback en microtask para evitar reentrancia RefCell, un subscription per mount y teardown.
- WebGPU→WebGL2 fallback real con user feedback, device loss y resize SurfaceLost/Outdated, no claims físicos sin tests.
- Service worker propio del viewer con scope independiente del probe. Offline real después de visita inicial, manifest+catalog+GLB SHA exactos y versionado consistente.
- MEMORY_LIMIT conserva escena anterior y permite LOD1/degradación. No GPU black screen silenciosa ni request zombie.

## B5. QA de aceptación local
- Rust y viewer builds/tests, Chrome+WebGPU+WebGL2 y Playwright E2E por 16+ viewports y orientación/altura corta, touch 44x44, focus trap, scroll, safe area, zoom.
- Cold/warm/offline con page.reload offline REAL; corruption SHA/size, 404/503 retries, cancel/subscribers, memory budget preflight, LOD0↔LOD1 100 veces y fallback.
- CPU/GPU metrics etiquetadas correctamente: estimaciones de recursos, frame pacing rAF y hardware/backend reales; evitar falsas promesas VRAM o 60FPS.
- Click en canvas selecciona TA2 real y sincroniza inspector y árbol; hide/isolate afecta geometría real; reset restaura escena.
- Pruebas físicas iPhone/iPad/Safari/Android/Mac pertenecen a M05-C y hasta entonces NOT_RUN; licencia comercial BLOCKED.
- Entregables: docs/M05B_IMPLEMENTATION_RESULT.md, ADR bridge si cambia, reports/implementation/M05B con matriz y capturas reales, scripts reproducibles.
- No iniciar M05-C ni producción automáticamente.

Decisión: planificación de M05-B permitida ahora; implementación sólo después de corregir y reauditar M05-A, y aprobación visual del usuario.
