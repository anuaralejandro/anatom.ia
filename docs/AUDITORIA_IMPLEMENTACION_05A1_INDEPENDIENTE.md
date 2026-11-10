# anatom.ia — Auditoría independiente M05-A.1 y decisión de entrada M05-B
Fecha: 2026-11-10. Repositorio local: C:\Users\datam\Documents\anatom.ia; rama feature/m04-runtime-streaming. Esta revisión NO alteró código de producción, GLB ni fuentes Z-Anatomy.

## Dictamen
**GO_M05B_LOCAL_DEVELOPMENT — NO PUBLICATION.** M05-A.1 aprobado a nivel de UI React conceptual y sus pruebas de navegador dentro de los límites definidos; la visualización real de anatomía no está implementada todavía, por lo que el control de cámara no puede darse por validado funcionalmente.

## Reproducciones independientes
- npm test en apps/viewer: **16/16 PASS**.
- npm run build en apps/viewer: **PASS** (TypeScript/Vite).
- cargo test --workspace: **39/39 PASS**.
- cargo fmt --all -- --check y cargo clippy --workspace --all-targets -- -D warnings: **PASS**.
- python tools/test_m05a_react_suite.py: PASS en **16 viewports**, F08–F16 según el alcance de la suite; no constituye prueba real de cámara Rust.
- python tools/audit_m05a_independent.py: Chrome real con servidor dev en localhost:3000, viewport/arranque/tema/idle/drawer/alto corto PASS. Ver reports/audit/m05a-independent-browser.json.
- http://127.0.0.1:3000 devolvió HTTP 200 durante auditoría.
- Capturas desktop dark/light revisadas. Dark Obsidian Navy/Modern Sky Blue aprobado como dirección de diseño; light actual usa fondo casi blanco, canvas azul-gris claro y CTA verde petróleo, rechazado subjetivamente por el propietario.
- Fuentes Z-Anatomy sin modificaciones; no hubo commit/push ni cambios al motor.

## Hallazgos de integración NO cubiertos por los PASS de M05-A.1
1. **M05B-01 (bloqueante funcional):** ViewerStage.tsx sigue ejecutando Canvas 2D; dibuja una silueta sintética plana. No inicializa el AtlasEngine wgpu ni carga GLB. Es intencional en M05-A.1; debe ser sustituido como primera tarea de M05-B y desaparecer del camino de producción. No permitir un fallback a silueta 2D etiquetado como anatomía real.
2. **M05B-02 (bloqueante funcional):** AxisNavigationGizmo controla azimuth/elevation en estado React interno y onSelectAxis sólo hace console.info. No está enlazado a cámara Rust, carece de lectura real de orientación y cambia sin que se mueva un modelo; hoy solo son tests matemáticos del icono. Además, el texto lateral invierte referencia anatómica: manifest.coordinateSystem.patientLeft="+X", por lo que +X es lateral del PACIENTE izquierdo, no derecho. Requiere getCameraState y setCameraAxis/snap para seis ejes comprobados.
3. **M05B-03 (accesibilidad táctil):** SVG de seis ejes añade círculos invisibles de radio 16 (diámetro 32px), potencialmente superpuestos dentro de un gizmo 64–76px. El QA comprueba tamaño del contenedor, NO seis hit targets independientes 44×44. En coarse/touch se necesita un menú de seis botones de >=44x44 al abrir gizmo; evitar seis targets 44x44 solapados.
4. **M05B-04 (estado):** AtlasRuntimeClient posee snapshots y capacidades inicializados a valores ficticios "webgpu"/"Mock/Synthetic Engine" y varios comandos aplican optimistic state a React aunque engine esté ausente. Al integrar M05-B, eliminar los falsos defaults en runtime real. Selección/visibilidad/escena se confirman por Rust después de aplicar comandos.
5. **M05B-05 (paleta alternativa):** light actual no es la identidad visual deseada. Rediseñar exclusivamente light como **Blender Studio Gray**: neutral gris grafito/metal, sin acento turquesa, mismo azul cielo, y viewport 3D casi negro; probar contraste/estados/desktop y iPhone. Conservar dark sin regresión.
6. **M05B-06 (QA físico):** pruebas Chrome Windows no certifican iPhone Safari, iPadOS Stage Manager, Apple Pencil, Android físico ni precisión clínica/comercial; mantener NOT_RUN/BLOCKED.

## Decisión
Autorizar prompt de ejecución **M05-B** acotado primero a REAL GPU GLB en React. Priorizar hard gate de screenshot auténtico con 26 TA2 y WebGPU + WebGL2 ANTES de refinamientos de light, gizmo, offline, streaming. El objetivo del propietario es probar el visualizador anatómico REAL. No continuar creando siluetas ni fake backends. Después de aprobar M05-B local, continuar certificación física M05-C y auditoría legal por asset antes de publicación.
