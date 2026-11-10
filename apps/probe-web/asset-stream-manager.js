/**
 * asset-stream-manager.js
 * M04-H5: Bounded Transport Scheduler, Request Coalescing, Retry with Backoff,
 * CacheStorage Integrity, and Generational Token Safety.
 *
 * Self-contained ES module portable across the diagnostic probe and M05 React.
 */

export class AssetStreamManager {
  constructor(options = {}) {
    this.manifest = null;
    this.catalog = null;
    this.cacheName = 'anatomia-atlas-uninitialized';
    this.cacheAvailable = typeof window !== 'undefined' && 'caches' in window;
    this.activeAbortController = null;
    this.currentRequestId = 0;
    this.simulatedOffline = false;

    // Concurrency Scheduler
    this.maxConcurrentFetches = options.maxConcurrentFetches || 3;
    this.activeFetchSlots = 0;
    this.fetchQueue = [];

    // In-Flight Request Coalescing (key -> { promise, subscribers: Set<AbortSignal>, abortController })
    this.inFlightRequests = new Map();

    this.logger = options.logger || console.log;
    this.stats = {
      cacheHits: 0,
      cacheMisses: 0,
      bytesDownloaded: 0,
      lastDigestVerificationMs: 0,
      coalescedRequests: 0,
      retriesCount: 0,
    };
  }

  log(msg, level = 'info') {
    if (this.logger) {
      this.logger(msg, level);
    }
  }

  setQualityProfile(profileName) {
    const p = String(profileName).toLowerCase();
    if (p === 'low') {
      this.maxConcurrentFetches = 2;
    } else if (p === 'high') {
      this.maxConcurrentFetches = 4;
    } else {
      this.maxConcurrentFetches = 3;
    }
  }

  async getCache() {
    if (!this.cacheAvailable) return null;
    try {
      return await window.caches.open(this.cacheName);
    } catch (e) {
      this.log(`CacheStorage no disponible o restringido: ${e}`, 'warn');
      return null;
    }
  }

  async computeSha256(arrayBuffer) {
    const t0 = performance.now();
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', arrayBuffer);
    this.stats.lastDigestVerificationMs = performance.now() - t0;
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Initializes and validates manifest and catalog against independent digests.
   */
  async initManifest(manifestUrl = './manifest.json', engine = null, onCatalogLoaded = null) {
    this.log(`Cargando manifest desde ${manifestUrl}...`);
    try {
      let manifestText = null;
      let candidate = null;
      try {
        const resp = await fetch(manifestUrl);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        manifestText = await resp.text();
        candidate = JSON.parse(manifestText);
      } catch (fetchErr) {
        // Offline fallback to CacheStorage if previously verified
        if (typeof caches !== 'undefined') {
          const cached = await caches.match(manifestUrl);
          if (cached) {
            manifestText = await cached.text();
            candidate = JSON.parse(manifestText);
            this.log('Manifest recuperado desde CacheStorage offline.');
          }
        }
        if (!candidate) throw fetchErr;
      }

      const activeEngine = engine || (typeof window !== 'undefined' ? window.atlasEngine : null);
      if (activeEngine) {
        activeEngine.loadManifest(manifestText);
      }

      // Verify the independent catalog before permitting any anatomical load.
      let catalogBytes = null;
      try {
        const catalogResponse = await fetch(candidate.catalog.url);
        if (!catalogResponse.ok) {
          throw new Error(`HTTP ${catalogResponse.status} al cargar catálogo`);
        }
        catalogBytes = await catalogResponse.arrayBuffer();
      } catch (fetchErr) {
        // Offline fallback to CacheStorage
        if (typeof caches !== 'undefined') {
          const cached = await caches.match(candidate.catalog.url);
          if (cached) {
            catalogBytes = await cached.arrayBuffer();
            this.log('Catálogo recuperado desde CacheStorage offline.');
          }
        }
        if (!catalogBytes) throw fetchErr;
      }

      if (catalogBytes.byteLength !== candidate.catalog.bytes) {
        throw new Error('ASSET_CORRUPT: tamaño del catálogo no coincide con el manifest');
      }
      const catalogHash = await this.computeSha256(catalogBytes);
      if (catalogHash.toLowerCase() !== candidate.catalog.sha256.toLowerCase()) {
        throw new Error('ASSET_CORRUPT: SHA-256 del catálogo no coincide con el manifest');
      }
      const catalog = JSON.parse(new TextDecoder().decode(catalogBytes));
      if (!Array.isArray(catalog.structures) || catalog.structures.length === 0) {
        throw new Error('ASSET_CORRUPT: catálogo sin estructuras');
      }
      const ids = catalog.structures.map(item => item.id);
      if (ids.some(id => typeof id !== 'string' || !id) || new Set(ids).size !== ids.length) {
        throw new Error('ASSET_CORRUPT: identificadores anatómicos ausentes o duplicados');
      }

      this.manifest = candidate;
      this.catalog = catalog;
      this.cacheName = `anatomia-atlas-v${candidate.atlasVersion}`;

      // Persist verified manifest and catalog into CacheStorage
      if (typeof caches !== 'undefined') {
        try {
          const cache = await caches.open(this.cacheName);
          await cache.put(manifestUrl, new Response(manifestText, {
            headers: { 'Content-Type': 'application/json' }
          }));
          await cache.put(candidate.catalog.url, new Response(catalogBytes, {
            headers: { 'Content-Type': 'application/json' }
          }));
        } catch (_) {}
      }

      if (typeof onCatalogLoaded === 'function') {
        onCatalogLoaded(catalog);
      }
      this.log(`Manifest/catálogo verificados: version=${candidate.atlasVersion}, packages=${candidate.packages?.length || '?'}, TA2=${ids.length}`);
      return this.manifest;
    } catch (err) {
      this.manifest = null;
      this.catalog = null;
      this.log(`Fallo al verificar manifest/catálogo: ${err?.detail || err?.message || err}`, 'warn');
      return null;
    }
  }

  /**
   * Schedule network task according to concurrency slots.
   */
  async scheduleFetch(taskFn, signal) {
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }

    if (this.activeFetchSlots < this.maxConcurrentFetches) {
      this.activeFetchSlots++;
      try {
        return await taskFn();
      } finally {
        this.activeFetchSlots--;
        this.drainQueue();
      }
    }

    return new Promise((resolve, reject) => {
      const queueItem = {
        taskFn,
        signal,
        resolve: (val) => {
          this.activeFetchSlots++;
          taskFn()
            .then(resolve)
            .catch(reject)
            .finally(() => {
              this.activeFetchSlots--;
              this.drainQueue();
            });
        },
        reject,
      };

      if (signal) {
        signal.addEventListener('abort', () => {
          const idx = this.fetchQueue.indexOf(queueItem);
          if (idx !== -1) {
            this.fetchQueue.splice(idx, 1);
            reject(new DOMException('Aborted in queue', 'AbortError'));
          }
        }, { once: true });
      }

      this.fetchQueue.push(queueItem);
    });
  }

  drainQueue() {
    while (this.activeFetchSlots < this.maxConcurrentFetches && this.fetchQueue.length > 0) {
      const nextItem = this.fetchQueue.shift();
      if (!nextItem.signal?.aborted) {
        nextItem.resolve();
        break;
      }
    }
  }

  /**
   * Fetch with timeout, exponential backoff, and transient error retry.
   */
  async fetchWithRetry(url, options = {}, maxRetries = 2, timeoutMs = 8000) {
    let attempt = 0;
    while (attempt <= maxRetries) {
      if (options.signal?.aborted) {
        throw new DOMException('Aborted', 'AbortError');
      }

      const timeoutController = new AbortController();
      const timeoutId = setTimeout(() => {
        timeoutController.abort();
      }, timeoutMs);

      const combinedSignal = options.signal
        ? anySignal([options.signal, timeoutController.signal])
        : timeoutController.signal;

      try {
        const resp = await fetch(url, { ...options, signal: combinedSignal });
        clearTimeout(timeoutId);

        if (resp.ok) {
          return resp;
        }

        // Check if status is transient (408, 429, 500, 502, 503, 504)
        const isTransient = [408, 429, 500, 502, 503, 504].includes(resp.status);
        if (!isTransient) {
          const terminalErr = new Error(`HTTP ${resp.status}: ${resp.statusText}`);
          terminalErr.isTerminal = true;
          terminalErr.status = resp.status;
          throw terminalErr;
        }

        if (attempt >= maxRetries) {
          throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
        }

        this.stats.retriesCount++;
        attempt++;
        const backoffMs = Math.min(200 * Math.pow(2, attempt) + Math.random() * 100, 2000);
        this.log(`Fallo transitorio HTTP ${resp.status}. Reintento ${attempt}/${maxRetries} en ${backoffMs.toFixed(0)}ms...`, 'warn');
        await new Promise(r => setTimeout(r, backoffMs));
      } catch (err) {
        clearTimeout(timeoutId);
        if (options.signal?.aborted || err?.isTerminal || err?.name === 'AbortError') {
          throw err;
        }
        if (attempt >= maxRetries) {
          throw err;
        }
        this.stats.retriesCount++;
        attempt++;
        const backoffMs = Math.min(200 * Math.pow(2, attempt) + Math.random() * 100, 2000);
        this.log(`Error de red '${err.message}'. Reintento ${attempt}/${maxRetries} en ${backoffMs.toFixed(0)}ms...`, 'warn');
        await new Promise(r => setTimeout(r, backoffMs));
      }
    }
  }

  /**
   * Loads package bytes with request coalescing, cache verification, and scheduler.
   */
  async loadPackageBytes(plan, parentSignal) {
    if (parentSignal?.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }

    const cacheKey = `https://atlas.local/assets/${encodeURIComponent(this.manifest?.atlasVersion || 'v1')}/${encodeURIComponent(plan.package_id)}?sha=${plan.expected_package_sha256}`;

    // 1. Request Coalescing: Register subscriber to master in-flight request
    let entry = this.inFlightRequests.get(cacheKey);
    const isNew = !entry;

    if (isNew) {
      const masterController = new AbortController();
      entry = {
        masterController,
        subscribers: new Map(),
        nextSubId: 1,
        promise: null,
      };
      this.inFlightRequests.set(cacheKey, entry);

      entry.promise = (async () => {
        // 2. Check local CacheStorage
        const cache = await this.getCache();
        if (cache) {
          try {
            const matched = await cache.match(cacheKey);
            if (matched) {
              const candidateBuffer = await matched.arrayBuffer();
              // Verify size and digest
              if (candidateBuffer.byteLength === plan.expected_package_bytes) {
                const digest = await this.computeSha256(candidateBuffer);
                if (digest.toLowerCase() === plan.expected_package_sha256.toLowerCase()) {
                  this.stats.cacheHits++;
                  this.log(`Cache HIT en disco para ${plan.package_id}. Cero peticiones de red.`);
                  return candidateBuffer;
                }
              }
              this.log(`Entrada de caché corrupta para ${plan.package_id}. Purgando...`, 'warn');
              await cache.delete(cacheKey);
            }
          } catch (cacheErr) {
            this.log(`Aviso de lectura en CacheStorage: ${cacheErr}`, 'warn');
          }
        }

        // 3. Offline Check
        if (this.simulatedOffline) {
          throw new Error('Modo sin conexión: paquete no disponible en caché (NETWORK_UNAVAILABLE)');
        }

        // 4. Scheduled Network Fetch
        return await this.scheduleFetch(async () => {
          this.log(`Descargando paquete ${plan.package_id} (${plan.package_url})...`);
          const resp = await this.fetchWithRetry(plan.package_url, { signal: entry.masterController.signal });
          const buffer = await resp.arrayBuffer();

          this.stats.cacheMisses++;
          this.stats.bytesDownloaded += buffer.byteLength;

          // Verify size
          if (buffer.byteLength !== plan.expected_package_bytes) {
            throw new Error(`ASSET_CORRUPT: tamaño recibido (${buffer.byteLength} B) no coincide con el manifest (${plan.expected_package_bytes} B)`);
          }

          // Verify SHA-256
          const digest = await this.computeSha256(buffer);
          if (digest.toLowerCase() !== plan.expected_package_sha256.toLowerCase()) {
            throw new Error(`ASSET_CORRUPT: SHA-256 '${digest}' no coincide con el manifest '${plan.expected_package_sha256}'`);
          }

          // Store in CacheStorage
          if (cache) {
            try {
              await cache.put(cacheKey, new Response(buffer.slice(0), {
                headers: { 'Content-Type': 'model/gltf-binary' }
              }));
              this.log(`Paquete ${plan.package_id} persistido en CacheStorage.`);
            } catch (putErr) {
              this.log(`Fallo al escribir en CacheStorage (cuota): ${putErr}`, 'warn');
            }
          }

          return buffer;
        }, entry.masterController.signal);
      })();

      // Dispatch results to subscribers once settled
      entry.promise
        .then((buffer) => {
          this.inFlightRequests.delete(cacheKey);
          for (const [, sub] of entry.subscribers) {
            if (sub.cleanup) sub.cleanup();
            sub.resolve(buffer);
          }
          entry.subscribers.clear();
        })
        .catch((err) => {
          this.inFlightRequests.delete(cacheKey);
          for (const [, sub] of entry.subscribers) {
            if (sub.cleanup) sub.cleanup();
            sub.reject(err);
          }
          entry.subscribers.clear();
        });
    } else {
      this.stats.coalescedRequests++;
      this.log(`Coalescing con petición en vuelo para ${plan.package_id}`);
    }

    return new Promise((resolve, reject) => {
      const subId = entry.nextSubId++;
      let onAbort = null;
      if (parentSignal) {
        onAbort = () => {
          entry.subscribers.delete(subId);
          reject(new DOMException('Aborted', 'AbortError'));
          if (entry.subscribers.size === 0) {
            entry.masterController.abort();
            this.inFlightRequests.delete(cacheKey);
          }
        };
        parentSignal.addEventListener('abort', onAbort, { once: true });
      }

      const cleanup = onAbort && parentSignal ? () => parentSignal.removeEventListener('abort', onAbort) : null;
      entry.subscribers.set(subId, { resolve, reject, cleanup });
    });
  }

  async purgeCache() {
    if (!this.cacheAvailable) return false;
    const cache = await this.getCache();
    if (cache) {
      const keys = await cache.keys();
      for (const k of keys) {
        await cache.delete(k);
      }
      this.log(`Caché purgado (${keys.length} entradas eliminadas).`);
      return true;
    }
    return false;
  }

  /**
   * High-level region streaming method coordinating plan creation, package retrieval,
   * generational safety, and transactional atomic swap into the WASM engine.
   */
  async loadRegion(engine, regionId = 'pelvis', variantId = 'male-adult', preferredLod = 0, callbacks = {}) {
    if (!engine) {
      throw new Error('AtlasEngine no está inicializado.');
    }

    // Cancel any previous in-flight request
    if (this.activeAbortController) {
      this.activeAbortController.abort();
    }
    this.activeAbortController = new AbortController();
    const signal = this.activeAbortController.signal;

    const requestId = ++this.currentRequestId;
    const expectedGeneration = engine.nextGeneration(requestId);

    this.log(`Iniciando streaming de región '${regionId}' (variante '${variantId}', LOD ${preferredLod}, req=${requestId}, gen=${expectedGeneration})...`);
    if (callbacks.onStart) {
      callbacks.onStart({ regionId, variantId, preferredLod, requestId, expectedGeneration });
    }

    // 1. Authoritative load plan from Rust core
    let plan;
    try {
      plan = engine.createLoadPlan(regionId, variantId, preferredLod);
    } catch (planErr) {
      if (callbacks.onError) {
        callbacks.onError(`Error creando plan de carga: ${planErr?.detail || planErr?.message || planErr}`);
      }
      return false;
    }

    // 2. Load package bytes via bounded scheduler & verified cache
    let buffer;
    try {
      buffer = await this.loadPackageBytes(plan, signal);
    } catch (netErr) {
      if (signal.aborted || engine.currentGeneration() !== expectedGeneration) {
        return false;
      }
      if (callbacks.onError) {
        callbacks.onError(`Error de red/integridad: ${netErr.message || netErr}`);
      }
      return false;
    }

    // 3. Generational safety check before touching GPU
    if (signal.aborted || engine.currentGeneration() !== expectedGeneration) {
      this.log(`Carga de ${plan.package_id} descartada: generación obsoleta o solicitud abortada.`, 'warn');
      return false;
    }

    // 4. Transactional Swap into WASM Engine
    try {
      const bytes = new Uint8Array(buffer);
      const snapshot = engine.applyPackageBytes(bytes, plan, requestId, expectedGeneration);

      this.log(`Región aplicada exitosamente: ${snapshot.region} (rev ${snapshot.scene_revision}, visible ${snapshot.visible_ids.length}, backend ${snapshot.backend})`);
      if (callbacks.onSuccess) {
        callbacks.onSuccess({ plan, snapshot, preferredLod, expectedGeneration });
      }
      return true;
    } catch (applyErr) {
      if (callbacks.onError) {
        callbacks.onError(`Error aplicando paquete en GPU: ${applyErr?.detail || applyErr?.message || applyErr}`);
      }
      return false;
    }
  }
}

// Helper to combine AbortSignals
function anySignal(signals) {
  const controller = new AbortController();
  for (const sig of signals) {
    if (sig.aborted) {
      controller.abort();
      return sig;
    }
    sig.addEventListener('abort', () => controller.abort(), { once: true });
  }
  return controller.signal;
}
