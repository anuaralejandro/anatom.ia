# ADR-004: ADOPCIÓN DE CACHESTORAGE PARA STREAMING Y PERSISTENCIA DE ASSETS

**Estado:** ACEPTADO  
**Fecha:** 2026-11-09  
**Hito:** M04 (Asset Streaming, Cache, Memory & Device Recovery)  
**Autor:** Principal Rust WebGPU/WASM Reliability Engineer  

---

## 1. CONTEXTO Y PROBLEMA

El motor gráfico anatom.ia requiere un mecanismo de almacenamiento local en el navegador del cliente para almacenar en caché de forma persistente los paquetes 3D versionados (`manifest.json`, catálogos y archivos GLB de regiones anatómicas como `pelvis-base-lod0.glb` y `pelvis-lod1.glb`).

Los requisitos innegociables para M04 son:
1. Reutilización instantánea en recargas (`cache warm`) sin peticiones de red redundantes.
2. Soporte de modo sin conexión (`offline`) sirviendo activos validados desde el disco local del cliente.
3. Verificación de integridad criptográfica SHA-256 antes de persistir y antes de transferir a la GPU.
4. Degradación elegante (`graceful fallback`) ante falta de permisos, modo incógnito estricto o cuota de almacenamiento agotada.
5. Cero duplicación de código ni capas innecesarias de base de datos relacional para simples blobs binarios.

---

## 2. OPCIONES EVALUADAS

### Opción A: IndexedDB
- **Ventajas:** API madura soportada en prácticamente todos los navegadores desde 2011; permite indexación por múltiples claves.
- **Desventajas:**
  - Requiere estructurar una base de datos con `IDBOpenDBRequest`, `onupgradeneeded`, transacciones y cursores.
  - Serialización structured clone overhead para `ArrayBuffer` o `Uint8Array`.
  - Propenso a errores de bloqueo de versión entre pestañas (`versionchange`).
  - El timeout de transacciones inactivas en hilos de renderizado complejos añade fragilidad.

### Opción B: Cache Storage API (`window.caches`)
- **Ventajas:**
  - Diseñado específicamente por el W3C para almacenar pares `Request` / `Response` binarios directamente contra el subsistema de red del navegador.
  - Almacenamiento nativo de `Response` y `Blob` a nivel de disco de navegador sin overhead de structured-clone en JS.
  - Claves URL semánticas e inmutables: encaja 1:1 con las URLs relativas del manifest (`/atlas-cache/v0.3.0/...`).
  - Permite verificar el digest criptográfico SHA-256 en memoria con Web Crypto API (`crypto.subtle.digest`) antes de llamar a `cache.put()`.
  - Si en hitos posteriores (M05/M06) se incorpora un Service Worker, las entradas de `CacheStorage` son accesibles de forma transparente e inmediata sin migración.
- **Desventajas:**
  - Puede estar deshabilitado en modos de navegación extremadamente restringidos (por ejemplo, iframes de terceros con sandbox sin `allow-same-origin`).

---

## 3. DECISIÓN

Se adopta **`CacheStorage`** como el único mecanismo de persistencia para el Asset Streamer de anatom.ia en M04.

### Reglas de Implementación:
1. **Nombre del Cache:**  
   `anatomia-atlas-v{atlasVersion}` (ej. `anatomia-atlas-v0.3.0`).
2. **Formato de Clave Virtual:**  
   `https://atlas.local/assets/v0.3.0/${packageId}?sha=${expectedSha256}`  
   Garantiza unicidad absoluta por paquete y por hash inmutable; un cambio de versión o de geometría nunca colisionará ni producirá caché obsoleta.
3. **Flujo de Integridad:**  
   - **Cache Miss:** Descargar vía `fetch` con `AbortController` → Verificar tamaño exacto → Calcular SHA-256 con `crypto.subtle.digest('SHA-256', buffer)` → Si coincide: `cache.put()` y decodificar en WASM. Si no coincide: rechazar con error tipado `ASSET_CORRUPT`.
   - **Cache Hit:** Recuperar `Response` de `cache.match()` → Verificar digest SHA-256 → Si pasa: aplicar al motor sin tocar la red. Si el digest falla (corrupción en disco): purgar entrada con `cache.delete()` y reintentar descarga limpia si hay red. Si no hay red: retornar error recuperable `ASSET_CORRUPT`.
4. **Resiliencia de Almacenamiento:**  
   Si `window.caches` es `undefined` (por ejemplo en entornos headless muy restringidos o modo privado estricto), el `AssetStreamManager` continúa operando en memoria sin lanzar excepciones no controladas.

---

## 4. CONSECUENCIAS

- **Rendimiento:** Cero latencia de serialización; decodificación directa del `ArrayBuffer` en WebAssembly.
- **Mantenibilidad:** Menos de 150 líneas de transporte en `apps/probe-web/app.js` frente a >400 líneas requeridas para una capa robusta de IndexedDB con migraciones.
- **Seguridad:** Ningún asset corrupto o con hash no coincidente se almacena jamás en el disco del cliente.
