# Z-Anatomy: auditoría del repositorio y archivo fuente

**Fecha:** 2026-11-09. **Auditoría local en modo lectura.**

## Repositorio exacto
- https://github.com/Z-Anatomy/Models-of-human-anatomy
- Rama: `master`.
- Commit clonado: `56016ea6da9de755ee4229f61fafc2b313db66ff`.
- Checkout local: `sources/z-anatomy-upstream/` (NO modificar).
- Archivo fuente: `sources/z-anatomy-upstream/Z-Anatomy.zip` (86,734,957 bytes).
- Dentro del ZIP: `Z-Anatomy/Startup.blend` (306,838,281 bytes descomprimidos).
- Copia extraída para inspección: `sources/z-anatomy-template/Z-Anatomy/Startup.blend`.
- Archivo ZIP también contiene `Anatomy-shortcuts.py`, `__init__.py`, dos temas XML y `splash.png`.
- `TA2.csv`: delimitador punto y coma; encabezado `TA2ID;English;Latin;Français;Español;Portugues;Italiano;Parsi` (hay una primera línea vacía).

## Resultado de abrir Startup.blend (Blender 4.4, --background --disable-autoexec)
- Objetos totales: **7,184**.
- MESH: **4,569** (incluye marcadores con 0 polígonos).
- CURVE: **951** (no se deben descartar: albergan vasos, nervios y conductos).
- FONT: **1,660** (etiquetas para UI web, no geometría GLB obligatoria).
- LIGHT: 3; CAMERA: 1.
- Polígonos nominales MESH: **3,655,404**.
- Vértices nominales MESH: **2,094,701**.
- Colecciones: **1,944**, materiales: **188**.
- Inventario detallado: `reports/z-anatomy-blend-inventory.json`, generado con `tools/inspect_blend.py`.

## Evidencias de anatomía realmente modelada
Objetos MESH presentes: `Sacrum`, `Coccyx`, `Pubic symphysis`, `Urinary bladder`, `Prostate`, `Testis.l`, `Testis.r`, `Seminal gland.l`, `Seminal gland.r`, `Glans penis`, `Corpus cavernosum of penis`, `Corpus spongiosum of penis`, `Sacrospinous ligament.l/r`, `Sacrotuberous ligament.l/r`, `Coccygeus muscle.l/r`.
Objetos CURVE presentes: `Common iliac artery.l/r`, `Internal iliac artery.l/r`, `External iliac vein.l/r`, `Femoral nerve.l/r`.
Hay colecciones rotuladas `Female genital system'`, `Female internal genitalia'`, `Female external genitalia'`, pero el inventario por nombres **no encontró mallas** de útero, ovarios ni vagina. No se deduce de etiquetas de colecciones que exista un modelo femenino. Se requiere auditoría de contenidos de esas colecciones para corroborar placeholders.

## Impacto arquitectónico obligatorio
1. **Pipeline de CURVE:** convertir a geometría renderizable preservando ancho, sistema, material e ID anatómico; no convertir indiscriminadamente a líneas sin grosor.
2. **MESH vacías:** marcadores `.j`, `.i` etc. con cero polígonos no representan necesariamente anatomía renderizable y deben mapearse a puntos/etiquetas o excluirse según su uso original.
3. **Etiquetas FONT:** extraer significado/jerarquía y mostrar mediante UI; evitar triángulos de texto.
4. **Colecciones:** conservar membresía/hierarquía como metadatos tipados. Hay estructuras con múltiples colecciones; no usar solo una ruta como ID estable.
5. **ID anatómico:** resolver nombres y lateralidad contra `TA2.csv`, con crosswalk verificable y revisión manual de ambigüedades.
6. **LOD:** aplicar simplificación por tipo; vasos/nervios convertidos desde CURVE requieren tolerancia de longitud/radio y topología controlada.
7. **Fuente masculina:** no inferir modelado femenino por presencia de colecciones de nomenclatura.
8. **No reutilizar código Python de la plantilla en el runtime Rust; analizarlo solo para extraer reglas/semántica necesarias.

## Licencia — advertencia de publicación
Readme/License.txt declaran CC BY-SA 4.0 para contenido Z-Anatomy, con atribución a BodyParts3D (CC BY-SA 2.1 Japan) y a sus autores. También citan piezas de terceros, incluyendo oído interno Dundee **CC BY-NC-SA 4.0** y riñón Lissie Cowley **CC BY-NC 4.0**. Por tanto **no asumir licencia comercial uniforme para cada estructura**.

Antes de distribución comercial: separar por asset la procedencia, evaluar compatibilidad de licencias, atribuir correctamente, excluir o reemplazar activos incompatibles y revisar las obligaciones ShareAlike respecto a los derivados. Esta auditoría técnica no constituye opinión legal.
- README: https://github.com/Z-Anatomy/Models-of-human-anatomy/blob/master/Readme.md
- Licencia: https://github.com/Z-Anatomy/Models-of-human-anatomy/blob/master/License.txt
- Plan oficial: https://github.com/Z-Anatomy/Models-of-human-anatomy/blob/master/TO%20DO%20List

## Estado
- Fuente localizada: **PASS**.
- Apertura y enumeración Blender: **PASS**.
- Jerarquía visual real y contenido de colecciones femeninas: **PENDIENTE**.
- Identidad anatómica estable y crosswalk a TA2: **PENDIENTE**.
- Licencia por pieza/publicación comercial: **BLOQUEADO** hasta trazabilidad.
- Exportación de fixture, render Rust y benchmarks: **NO INICIADOS**.
