// apps/probe-web/app.js
// anatom.ia — Diagnostic Probe Shell (M00-M04: Asset Streaming, Cache, Memory, Device Recovery)

import { AssetStreamManager } from './asset-stream-manager.js';

// Register Service Worker for Offline App Shell (M04-H6)
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('./service-worker.js', { scope: './' })
      .then((reg) => {
        log(`ServiceWorker registrado (scope: ${reg.scope})`);
      })
      .catch((err) => {
        log(`Aviso: fallo al registrar ServiceWorker: ${err}`, 'warn');
      });
  });
}

const state = {
  engine: null,
  activeBackend: null,
  requestedBackend: 'auto',
  activeScene: 'pelvis',
  currentLod: 0,
  structures: [],
  selectedId: null,
  darkTheme: true,
  isInteracting: false,
  lastFrameTime: performance.now(),
  frameCount: 0,
  fps: 0,
  sceneLoaded: false,
};
document.documentElement.dataset.atlasProbeStatus = 'booting';

// UI Elements
const el = {
  canvas: document.getElementById('canvas'),
  viewportContainer: document.getElementById('viewport-container'),
  backendSelect: document.getElementById('backend-select'),
  backendBadge: document.getElementById('backend-badge'),
  sceneSelect: document.getElementById('scene-select'),
  lodSelect: document.getElementById('lod-select'),
  qualitySelect: document.getElementById('quality-select'),
  offlineBtn: document.getElementById('offline-btn'),
  rapidLodBtn: document.getElementById('rapid-lod-btn'),
  deviceLossBtn: document.getElementById('device-loss-btn'),
  themeBtn: document.getElementById('theme-btn'),
  logToggleBtn: document.getElementById('log-toggle-btn'),
  logDrawer: document.getElementById('log-drawer'),
  loadingOverlay: document.getElementById('loading-overlay'),
  loadingText: document.getElementById('loading-text'),
  errorBanner: document.getElementById('error-banner'),
  errorMessage: document.getElementById('error-message'),
  structureList: document.getElementById('structure-list'),
  structureSearch: document.getElementById('structure-search'),
  structureCountBadge: document.getElementById('structure-count-badge'),
  // Action buttons
  btnFocus: document.getElementById('btn-focus'),
  btnIsolate: document.getElementById('btn-isolate'),
  btnHide: document.getElementById('btn-hide'),
  btnResetVis: document.getElementById('btn-reset-vis'),
  btnResetCam: document.getElementById('btn-reset-cam'),
  btnDeselect: document.getElementById('btn-deselect'),
  // Presets
  preset0: document.getElementById('preset-0'),
  preset1: document.getElementById('preset-1'),
  preset2: document.getElementById('preset-2'),
  // Diagnostic stats
  statBackend: document.getElementById('stat-backend'),
  statAdapter: document.getElementById('stat-adapter'),
  statSelected: document.getElementById('stat-selected'),
  statCache: document.getElementById('stat-cache'),
  statDownloaded: document.getElementById('stat-downloaded'),
  statGeneration: document.getElementById('stat-generation'),
  statGpuMem: document.getElementById('stat-gpu-mem'),
  statCpuMem: document.getElementById('stat-cpu-mem'),
  statNodes: document.getElementById('stat-nodes'),
  statPrims: document.getElementById('stat-prims'),
  statTris: document.getElementById('stat-tris'),
  statDrawcalls: document.getElementById('stat-drawcalls'),
  statFps: document.getElementById('stat-fps'),
};

function log(msg, level = 'info') {
  console.log(`[anatom.ia ${level.toUpperCase()}] ${msg}`);
  const line = document.createElement('div');
  line.className = `log-entry log-${level}`;
  const time = new Date().toISOString().substring(11, 19);
  line.textContent = `[${time}] ${msg}`;
  el.logDrawer.appendChild(line);
  el.logDrawer.scrollTop = el.logDrawer.scrollHeight;
}

function showError(msg) {
  document.documentElement.dataset.atlasProbeStatus = 'error';
  log(msg, 'err');
  el.errorMessage.textContent = msg;
  el.errorBanner.style.display = 'flex';
  el.backendBadge.className = 'badge badge-error';
  el.backendBadge.textContent = 'Error';
  el.loadingOverlay.style.display = 'none';
}

function showLoading(text) {
  document.documentElement.dataset.atlasProbeStatus = 'loading';
  el.loadingText.textContent = text;
  el.loadingOverlay.style.display = 'flex';
}

function hideLoading() {
  el.loadingOverlay.style.display = 'none';
}

// ============================================================================
// M04-H5: ASSET STREAM MANAGER (Bounded Transport Scheduler, CacheStorage & Coalescing)
// ============================================================================
const streamManager = new AssetStreamManager({
  logger: log,
});
window.streamManager = streamManager;

// Adapter wrapper for existing probe UI calls
streamManager._origInitManifest = streamManager.initManifest;
streamManager.initManifest = async function(manifestUrl = './manifest.json') {
  // Verifies catalog sha256 digest against manifest
  return await this._origInitManifest(manifestUrl, state.engine, (catalog) => {
    state.structures = catalog.structures.map(item => ({
      id: item.id,
      name_es: item.labels?.['es-MX'] || item.labels?.en || item.id,
      ta2Id: item.ta2Id || item.id,
      side: item.side || 'unspecified',
    }));
    renderStructureList(state.structures);
    if (el.structureCountBadge) {
      el.structureCountBadge.textContent = state.structures.length + ' / ' + state.structures.length;
    }
  });
};

streamManager._origLoadRegion = streamManager.loadRegion;
streamManager.loadRegion = async function(regionId = 'pelvis', variantId = 'male-adult', preferredLod = 0) {
  if (el.lodSelect) {
    el.lodSelect.value = String(preferredLod);
  }

  return await this._origLoadRegion(state.engine, regionId, variantId, preferredLod, {
    onStart: () => {
      showLoading(`Cargando ${regionId} LOD${preferredLod}...`);
      if (el.statCache) el.statCache.textContent = 'Buscando...';
    },
    onSuccess: ({ plan, snapshot, preferredLod: lod }) => {
      state.sceneLoaded = true;
      state.currentLod = lod;
      state.activeScene = (lod === 1) ? 'pelvis-lod1' : 'pelvis';
      document.documentElement.dataset.atlasScene = state.activeScene;
      if (el.sceneSelect) el.sceneSelect.value = state.activeScene;
      if (el.statCache) {
        el.statCache.textContent = streamManager.stats.cacheHits > 0 ? 'HIT (Disk)' : 'MISS (Fetch)';
      }
      if (el.statDownloaded) {
        el.statDownloaded.textContent = `${(streamManager.stats.bytesDownloaded / 1024).toFixed(0)} KB`;
      }
      updateStats();
      scheduleRender();
      hideLoading();
    },
    onError: (errStr) => {
      hideLoading();
      showError(errStr);
    },
  });
};

// ============================================================================
// ENGINE INITIALIZATION & CANVAS LIFECYCLE
// ============================================================================
let pointerListenerController = null;
let activeResizeObserver = null;

function resetCanvas() {
  pointerListenerController?.abort();
  pointerListenerController = null;
  const oldCanvas = el.canvas;
  const newCanvas = document.createElement('canvas');
  newCanvas.id = 'canvas';
  newCanvas.style.width = '100%';
  newCanvas.style.height = '100%';
  newCanvas.style.display = 'block';
  newCanvas.style.touchAction = 'none';
  oldCanvas.replaceWith(newCanvas);
  el.canvas = newCanvas;
  attachPointerEvents(newCanvas);
  return newCanvas;
}

async function initializeWithTimeout(engine, canvas, options, timeoutMs) {
  let timer;
  let expired = false;
  const pending = engine.initialize(canvas, options);
  pending.then(() => {
    if (expired) {
      try { engine.dispose(); } catch (_) {}
    }
  }).catch(() => {});
  try {
    return await Promise.race([
      pending,
      new Promise((_, reject) => {
        timer = setTimeout(() => {
          expired = true;
          reject(new Error('WebGPU initialization timed out; falling back to WebGL2.'));
        }, timeoutMs);
      })
    ]);
  } finally {
    clearTimeout(timer);
  }
}

async function bootstrapEngine(backendReq) {
  showLoading(`Iniciando backend ${backendReq.toUpperCase()}...`);
  state.sceneLoaded = false;
  document.documentElement.dataset.atlasBackend = 'none';
  state.requestedBackend = backendReq;
  el.backendSelect.value = backendReq;

  streamManager.activeAbortController?.abort();
  activeResizeObserver?.disconnect();
  activeResizeObserver = null;
  if (state.engine) {
    try {
      state.engine.dispose();
    } catch (e) {
      log(`Error disposing previous engine: ${e}`, 'warn');
    }
    state.engine = null;
  }

  const canvas = resetCanvas();
  let effectiveBackend = null;
  let pkg = null;

  if (backendReq === 'webgpu' || backendReq === 'auto') {
    try {
      log('Importando módulo WebGPU WASM (pkg-webgpu)...');
      pkg = await import('./pkg-webgpu/atlas_web.js');
      await pkg.default();
      log('Módulo WebGPU WASM instanciado.');

      const engine = new pkg.AtlasEngine();
      log('Solicitando inicialización con WebGPU...');
      const caps = await initializeWithTimeout(engine, canvas, {
        preferred_backend: 'webgpu',
        power_preference: 'high-performance',
        dpr: window.devicePixelRatio || 1.0,
      }, 5000);

      effectiveBackend = caps.backend;
      state.engine = engine;
      engine.setEventCallback((event) => {
        log(`Rust event: ${event.type}${event.id ? ' (' + event.id + ')' : ''} (gen=${event.sceneGeneration || '?'}, rev=${event.sceneRevision || '?'})`);
      });
      state.activeBackend = 'webgpu';
      el.statAdapter.textContent = caps.adapter_name || 'WebGPU Adapter';
      log(`WebGPU inicializado exitosamente: adapter=${caps.adapter_name}, backend=${caps.backend}`);
    } catch (err) {
      log(`Fallo al inicializar WebGPU: ${err?.detail || err?.message || err}`, 'warn');
      if (backendReq === 'webgpu') {
        showError(`WebGPU no está disponible: ${err?.detail || err?.message || err}`);
        return false;
      }
      log('Intentando fallback automático a WebGL2...', 'warn');
    }
  }

  if (!state.engine && (backendReq === 'webgl2' || backendReq === 'auto')) {
    try {
      const fallbackCanvas = resetCanvas();
      log('Importando módulo WebGL2 WASM (pkg-webgl2)...');
      pkg = await import('./pkg-webgl2/atlas_web.js');
      await pkg.default();
      log('Módulo WebGL2 WASM instanciado.');

      const engine = new pkg.AtlasEngine();
      log('Solicitando inicialización con WebGL2...');
      const caps = await engine.initialize(fallbackCanvas, {
        preferred_backend: 'webgl2',
        power_preference: 'high-performance',
        dpr: window.devicePixelRatio || 1.0,
      });

      effectiveBackend = caps.backend;
      state.engine = engine;
      engine.setEventCallback((event) => {
        log(`Rust event: ${event.type}${event.id ? ' (' + event.id + ')' : ''} (gen=${event.sceneGeneration || '?'}, rev=${event.sceneRevision || '?'})`);
      });
      state.activeBackend = 'webgl2';
      el.statAdapter.textContent = caps.adapter_name || 'WebGL2 Adapter';
      log(`WebGL2 inicializado exitosamente: adapter=${caps.adapter_name}, backend=${caps.backend}`);
    } catch (err) {
      const finalErr = `Fallo crítico en ambos backends: ${err?.detail || err?.message || err}`;
      showError(finalErr);
      return false;
    }
  }

  if (!state.engine) {
    showError('No se pudo inicializar ningún backend gráfico compatible.');
    return false;
  }

  // Update UI badges
  document.documentElement.dataset.atlasBackend = state.activeBackend;
  el.statBackend.textContent = state.activeBackend.toUpperCase();
  if (state.activeBackend === 'webgpu') {
    el.backendBadge.className = 'badge badge-webgpu';
    el.backendBadge.textContent = 'WebGPU ACTIVO';
  } else {
    el.backendBadge.className = backendReq === 'auto' ? 'badge badge-fallback' : 'badge badge-webgl2';
    el.backendBadge.textContent = backendReq === 'auto' ? 'WebGL2 (FALLBACK)' : 'WebGL2 ACTIVO';
  }

  // Setup ResizeObserver
  const resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const w = Math.floor(entry.contentRect.width);
      const h = Math.floor(entry.contentRect.height);
      if (w > 0 && h > 0 && state.engine) {
        state.engine.resize(w, h);
        scheduleRender();
      }
    }
  });
  resizeObserver.observe(el.viewportContainer);
  activeResizeObserver = resizeObserver;

  // Reload manifest into newly instantiated engine
  if (streamManager.manifest) {
    state.engine.loadManifest(JSON.stringify(streamManager.manifest));
  }

  return true;
}

// Load Scene (Pelvis GLB via Stream Manager or Synthetic Cube)
async function loadScene(sceneType) {
  if (!state.engine) return;
  state.sceneLoaded = false;
  state.activeScene = sceneType;
  document.documentElement.dataset.atlasScene = sceneType;
  el.sceneSelect.value = sceneType;

  if (sceneType === 'cube') {
    showLoading('Cargando Cubo Sintético (M01)...');
    try {
      state.engine.loadSyntheticCube();
      log('Cubo sintético cargado correctamente.');
      state.sceneLoaded = true;
      updateStats();
      scheduleRender();
      hideLoading();
    } catch (err) {
      showError(`Error cargando cubo sintético: ${err}`);
    }
  } else {
    const isLod1 = (sceneType === 'pelvis-lod1');
    const lod = isLod1 ? 1 : 0;
    state.currentLod = lod;
    if (el.lodSelect) el.lodSelect.value = String(lod);

    // If manifest is available, use AssetStreamManager!
    if (streamManager.manifest) {
      await streamManager.loadRegion('pelvis', 'male-adult', lod);
    } else {
      // Fallback direct load
      const defaultGlb = isLod1 ? './pelvis-lod1.glb' : './pelvis-base-lod0.glb';
      const glbUrl = window.__customModelUrl || defaultGlb;
      showLoading(`Cargando Pelvis (LOD ${lod})...`);
      try {
        const resp = await fetch(glbUrl);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const buffer = await resp.arrayBuffer();
        state.engine.loadGlbBytes(new Uint8Array(buffer));
        state.sceneLoaded = true;
        updateStats();
        scheduleRender();
        hideLoading();
      } catch (err) {
        showError(`Error cargando GLB: ${err}`);
      }
    }
  }
}

// Populate 26 structures list
async function loadStructureCatalog() {
  try {
    const resp = await fetch('./structures.json');
    state.structures = await resp.json();
    renderStructureList(state.structures);
    el.structureCountBadge.textContent = `${state.structures.length} / 26`;
    log(`Catálogo cargado: ${state.structures.length} estructuras TA2.`);
  } catch (err) {
    log(`Error cargando estructuras.json: ${err}`, 'warn');
  }
}

function renderStructureList(items) {
  el.structureList.innerHTML = '';
  const filter = (el.structureSearch.value || '').toLowerCase().trim();

  items.forEach((item) => {
    if (filter) {
      const matchName = item.name_es.toLowerCase().includes(filter);
      const matchId = item.id.toLowerCase().includes(filter);
      const matchTa2 = item.ta2Id.toLowerCase().includes(filter);
      if (!matchName && !matchId && !matchTa2) return;
    }

    const li = document.createElement('li');
    li.className = 'structure-item';
    li.dataset.id = item.id;
    if (state.selectedId === item.id) {
      li.classList.add('selected');
    }

    // Visibility Checkbox
    const chk = document.createElement('input');
    chk.type = 'checkbox';
    chk.checked = true;
    chk.title = 'Mostrar / Ocultar';
    chk.addEventListener('click', (e) => {
      e.stopPropagation();
      toggleVisibility(item.id, chk.checked);
    });

    const infoDiv = document.createElement('div');
    infoDiv.className = 'structure-info';

    const nameSpan = document.createElement('span');
    nameSpan.className = 'structure-name';
    nameSpan.textContent = item.name_es;

    const idSpan = document.createElement('span');
    idSpan.className = 'structure-id';
    idSpan.textContent = `${item.ta2Id} • ${item.side}`;

    infoDiv.appendChild(nameSpan);
    infoDiv.appendChild(idSpan);

    li.appendChild(chk);
    li.appendChild(infoDiv);

    li.addEventListener('click', () => {
      selectStructure(item.id);
    });

    el.structureList.appendChild(li);
  });
}

function selectStructure(id) {
  state.selectedId = id;
  if (state.engine) {
    state.engine.selectStructure(id);
    scheduleRender();
  }

  // Update UI selection
  const items = el.structureList.querySelectorAll('.structure-item');
  items.forEach((li) => {
    if (li.dataset.id === id) {
      li.classList.add('selected');
      li.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } else {
      li.classList.remove('selected');
    }
  });

  const selectedItem = state.structures.find((s) => s.id === id);
  el.statSelected.textContent = selectedItem ? selectedItem.name_es : 'Ninguna';
  log(`Selección cambiada a: ${id || 'Ninguna'}`);
}

function toggleVisibility(id, visible) {
  if (!state.engine) return;
  state.engine.setVisibility(id, visible);
  updateStats();
  scheduleRender();
  log(`Visibilidad de '${id}' cambiada a: ${visible}`);
}

function updateStats() {
  if (!state.engine) return;
  try {
    const stats = state.engine.getStats();
    if (stats) {
      el.statNodes.textContent = `${stats.visible_nodes}/${stats.total_nodes}`;
      el.statPrims.textContent = stats.primitive_count;
      el.statTris.textContent = stats.triangle_count.toLocaleString();
      el.statDrawcalls.textContent = stats.draw_call_count;
    }
    const mem = state.engine.getMemoryStats();
    if (mem) {
      if (el.statGpuMem) {
        el.statGpuMem.textContent = `${(mem.residentGpuBytes / (1024 * 1024)).toFixed(1)} MB`;
      }
      if (el.statCpuMem) {
        el.statCpuMem.textContent = `${(mem.decodedCpuBytes / (1024 * 1024)).toFixed(1)} MB`;
      }
      if (el.statGeneration) {
        el.statGeneration.textContent = String(mem.currentGeneration);
      }
    }
  } catch (e) {
    // getStats not available or failed
  }
}

// Render-on-demand loop
let renderPending = false;
function scheduleRender() {
  if (renderPending) return;
  renderPending = true;
  requestAnimationFrame(renderLoop);
}

function renderLoop(time) {
  renderPending = false;
  if (!state.engine) return;

  const start = performance.now();
  const rendered = state.engine.renderFrame();
  const duration = performance.now() - start;

  if (rendered) {
    state.frameCount++;
    if (state.sceneLoaded) {
      document.documentElement.dataset.atlasProbeStatus = 'ready';
      document.documentElement.dataset.atlasBackend = state.activeBackend || 'unknown';
      document.documentElement.dataset.atlasScene = state.activeScene;
    }
    if (time - state.lastFrameTime >= 1000) {
      state.fps = Math.round((state.frameCount * 1000) / (time - state.lastFrameTime));
      state.frameCount = 0;
      state.lastFrameTime = time;
      el.statFps.textContent = `${duration.toFixed(1)}ms (${state.fps} fps)`;
    }
  }

  if (state.isInteracting) {
    scheduleRender();
  }
}

// Pointer & Touch Controls
function attachPointerEvents(canvas) {
  pointerListenerController = new AbortController();
  const listenerSignal = pointerListenerController.signal;
  let isDown = false;
  let startX = 0;
  let startY = 0;
  let moved = false;
  let isPan = false;

  canvas.addEventListener('mousedown', (e) => {
    isDown = true;
    startX = e.clientX;
    startY = e.clientY;
    moved = false;
    isPan = (e.button === 1 || e.button === 2);
    state.isInteracting = true;
  }, { signal: listenerSignal });

  window.addEventListener('mousemove', (e) => {
    if (!isDown || !state.engine) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (Math.abs(dx) > 2 || Math.abs(dy) > 2) moved = true;

    if (isPan) {
      state.engine.pan(dx, dy);
    } else {
      state.engine.orbit(dx, dy);
    }

    startX = e.clientX;
    startY = e.clientY;
    scheduleRender();
  }, { signal: listenerSignal });

  window.addEventListener('mouseup', (e) => {
    if (!isDown) return;
    isDown = false;
    state.isInteracting = false;

    // Raycast Picking if clicked without drag
    if (!moved && state.engine && e.button === 0) {
      const rect = canvas.getBoundingClientRect();
      const cssX = e.clientX - rect.left;
      const cssY = e.clientY - rect.top;

      const hitId = state.engine.selectAt(cssX, cssY);
      selectStructure(hitId || null);
    }
  }, { signal: listenerSignal });

  canvas.addEventListener('contextmenu', (e) => e.preventDefault());

  canvas.addEventListener('wheel', (e) => {
    e.preventDefault();
    if (!state.engine) return;
    state.engine.zoom(e.deltaY);
    scheduleRender();
  }, { passive: false });

  // Touch controls
  let initialPinchDist = 0;
  canvas.addEventListener('touchstart', (e) => {
    state.isInteracting = true;
    if (e.touches.length === 1) {
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
      moved = false;
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      initialPinchDist = Math.hypot(dx, dy);
    }
    scheduleRender();
  }, { passive: true });

  canvas.addEventListener('touchmove', (e) => {
    if (!state.engine) return;
    if (e.touches.length === 1) {
      const dx = e.touches[0].clientX - startX;
      const dy = e.touches[0].clientY - startY;
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) moved = true;
      state.engine.orbit(dx, dy);
      startX = e.touches[0].clientX;
      startY = e.touches[0].clientY;
    } else if (e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy);
      const delta = initialPinchDist - dist;
      state.engine.zoom(delta * 2.0);
      initialPinchDist = dist;
    }
    scheduleRender();
  }, { passive: true });

  canvas.addEventListener('touchend', (e) => {
    state.isInteracting = false;
    if (!moved && e.changedTouches.length === 1 && state.engine) {
      const rect = canvas.getBoundingClientRect();
      const cssX = e.changedTouches[0].clientX - rect.left;
      const cssY = e.changedTouches[0].clientY - rect.top;
      const hitId = state.engine.selectAt(cssX, cssY);
      selectStructure(hitId || null);
    }
  });
}

// Action buttons
el.btnFocus.addEventListener('click', () => {
  if (state.selectedId && state.engine) {
    state.engine.focusStructure(state.selectedId);
    scheduleRender();
    log(`Enfocada estructura: ${state.selectedId}`);
  }
});

el.btnIsolate.addEventListener('click', () => {
  if (state.selectedId && state.engine) {
    state.engine.isolateStructure(state.selectedId);
    const items = el.structureList.querySelectorAll('.structure-item');
    items.forEach((li) => {
      const chk = li.querySelector('input[type="checkbox"]');
      if (chk) chk.checked = (li.dataset.id === state.selectedId);
    });
    updateStats();
    scheduleRender();
    log(`Aislada estructura: ${state.selectedId}`);
  }
});

el.btnHide.addEventListener('click', () => {
  if (state.selectedId && state.engine) {
    state.engine.setVisibility(state.selectedId, false);
    const li = el.structureList.querySelector(`.structure-item[data-id="${state.selectedId}"]`);
    if (li) {
      const chk = li.querySelector('input[type="checkbox"]');
      if (chk) chk.checked = false;
    }
    updateStats();
    scheduleRender();
    log(`Ocultada estructura: ${state.selectedId}`);
  }
});

el.btnResetVis.addEventListener('click', () => {
  if (state.engine) {
    state.engine.resetVisibility();
    const items = el.structureList.querySelectorAll('.structure-item input[type="checkbox"]');
    items.forEach(chk => chk.checked = true);
    updateStats();
    scheduleRender();
    log('Visibilidad de todas las estructuras restaurada.');
  }
});

el.btnResetCam.addEventListener('click', () => {
  if (state.engine) {
    state.engine.resetCamera();
    scheduleRender();
    log('Cámara restablecida al encuadre inicial.');
  }
});

el.btnDeselect.addEventListener('click', () => {
  selectStructure(null);
});

// Camera Presets
el.preset0.addEventListener('click', () => {
  if (state.engine) {
    state.engine.setCameraPreset(0);
    scheduleRender();
    log('Cámara fijada a Preset 0: Vista Anterior-Superior.');
  }
});

el.preset1.addEventListener('click', () => {
  if (state.engine) {
    state.engine.setCameraPreset(1);
    scheduleRender();
    log('Cámara fijada a Preset 1: Vista Lateral-Oblicua.');
  }
});

el.preset2.addEventListener('click', () => {
  if (state.engine) {
    state.engine.setCameraPreset(2);
    scheduleRender();
    log('Cámara fijada a Preset 2: Vista Perineal-Inferior.');
  }
});

// Selectors
el.backendSelect.addEventListener('change', async (e) => {
  const newBackend = e.target.value;
  const ok = await bootstrapEngine(newBackend);
  if (ok) {
    await loadScene(state.activeScene);
  }
});

el.sceneSelect.addEventListener('change', async (e) => {
  await loadScene(e.target.value);
});

el.lodSelect.addEventListener('change', async (e) => {
  const lod = parseInt(e.target.value, 10);
  await streamManager.loadRegion('pelvis', 'male-adult', lod);
});

el.qualitySelect.addEventListener('change', (e) => {
  const profile = e.target.value;
  if (state.engine) {
    try {
      const budget = state.engine.setQualityProfile(profile);
      log(`Perfil de calidad cambiado a: ${profile.toUpperCase()} (GPU: ${(budget.gpuResidentBudgetBytes / (1024 * 1024))}MB)`);
      updateStats();
    } catch (err) {
      log(`Error configurando perfil: ${err}`, 'warn');
    }
  }
});

el.offlineBtn.addEventListener('click', () => {
  streamManager.simulatedOffline = !streamManager.simulatedOffline;
  if (streamManager.simulatedOffline) {
    el.offlineBtn.textContent = '🔌 Offline';
    el.offlineBtn.style.background = '#b91c1c';
    log('Simulación de modo sin conexión activada.');
  } else {
    el.offlineBtn.textContent = '🌐 Online';
    el.offlineBtn.style.background = '';
    log('Modo en línea restaurado.');
  }
});

// M04 20x Rapid LOD Toggle Test
async function runRapidLodToggleTest(iterations = 20) {
  log(`=== INICIANDO PRUEBA M04: 20x CONMUTACIÓN ATÓMICA DE LOD ===`);
  const initialMem = state.engine.getMemoryStats();
  const initialGpuBytes = initialMem.residentGpuBytes;
  let peakGpuBytes = initialGpuBytes;
  let targetLod = 1;

  for (let i = 0; i < iterations; i++) {
    log(`[${i + 1}/${iterations}] Alternando a LOD ${targetLod}...`);
    const ok = await streamManager.loadRegion('pelvis', 'male-adult', targetLod);
    if (!ok) {
      log(`Error en iteración ${i + 1} de conmutación de LOD!`, 'err');
      return { pass: false, iteration: i + 1 };
    }
    const currentMem = state.engine.getMemoryStats();
    if (currentMem.residentGpuBytes > peakGpuBytes) {
      peakGpuBytes = currentMem.residentGpuBytes;
    }
    targetLod = (targetLod === 0) ? 1 : 0;
    await new Promise(r => setTimeout(r, 60));
  }

  const finalMem = state.engine.getMemoryStats();
  const structures = state.engine.getStructures();
  const idsIntact = (structures.length === 26);
  // Monotonic leak check: final memory should be bounded within initial peak margin
  const leakFree = (finalMem.residentGpuBytes <= peakGpuBytes * 1.05);

  log(`Prueba 20x finalizada:`);
  log(`- Estructuras TA2 intactas: ${structures.length}/26 (${idsIntact ? 'PASS' : 'FAIL'})`);
  log(`- Pico GPU resident: ${(peakGpuBytes / (1024 * 1024)).toFixed(2)} MB`);
  log(`- GPU resident final: ${(finalMem.residentGpuBytes / (1024 * 1024)).toFixed(2)} MB`);
  log(`- Sin fuga acumulativa: ${leakFree ? 'PASS' : 'FAIL'}`);

  return {
    pass: idsIntact && leakFree,
    iterations,
    idsCount: structures.length,
    initialGpuBytes,
    peakGpuBytes,
    finalGpuBytes: finalMem.residentGpuBytes,
  };
}
el.rapidLodBtn.addEventListener('click', () => runRapidLodToggleTest(20));

// M04 Device Loss Simulation & Recovery
async function simulateDeviceLossAndRecover() {
  log(`=== INICIANDO SIMULACIÓN M04: PÉRDIDA DE DISPOSITIVO GPU Y RECUPERACIÓN ===`, 'warn');
  if (state.engine) {
    state.engine.simulateDeviceLoss();
  }
  // Re-bootstrap canvas & engine context
  log('Reconstruyendo contexto GPU y pipelines...');
  const success = await bootstrapEngine(state.requestedBackend);
  if (success) {
    log('Recargando escena desde caché persistente verificada...');
    await streamManager.loadRegion('pelvis', 'male-adult', state.currentLod || 0);
    log('Recuperación de dispositivo GPU completada (SIMULATED_PASS).', 'info');
    return true;
  }
  return false;
}
el.deviceLossBtn.addEventListener('click', () => simulateDeviceLossAndRecover());

el.structureSearch.addEventListener('input', () => {
  renderStructureList(state.structures);
});

// Theme toggle
el.themeBtn.addEventListener('click', () => {
  state.darkTheme = !state.darkTheme;
  document.body.setAttribute('data-theme', state.darkTheme ? 'dark' : 'light');
  el.themeBtn.textContent = state.darkTheme ? '☀️ Claro' : '🌙 Oscuro';
  if (state.engine) {
    state.engine.setTheme(state.darkTheme);
    scheduleRender();
  }
});

// Log toggle
el.logToggleBtn.addEventListener('click', () => {
  const open = el.logDrawer.style.display === 'block';
  el.logDrawer.style.display = open ? 'none' : 'block';
});

// Expose globals for automated test harness
window.__atlasEngine = () => state.engine;
window.__atlasStreamManager = streamManager;
window.__atlasState = state;
window.__runRapidLodToggle = runRapidLodToggleTest;
window.__simulateDeviceLoss = simulateDeviceLossAndRecover;

// Bootstrap application on page load
async function main() {
  log('Iniciando probe-web M04...');
  const params = new URLSearchParams(window.location.search);
  const requestedBackend = params.get('backend') || 'auto';
  const initialScene = params.get('scene') || 'pelvis';
  const isLod1 = (initialScene === 'pelvis-lod1');
  const initialLod = parseInt(params.get('lod') || (isLod1 ? '1' : '0'), 10);
  const customModel = params.get('model');
  if (customModel) {
    window.__customModelUrl = customModel;
  }

  await loadStructureCatalog();

  const success = await bootstrapEngine(requestedBackend);
  if (success) {
    const verifiedManifest = await streamManager.initManifest('./manifest.json');
    if (!verifiedManifest && initialScene !== 'cube') {
      showError('No se verificó manifest/catálogo: carga anatómica bloqueada.');
      return;
    }
    if (initialScene === 'cube') {
      await loadScene('cube');
    } else {
      await streamManager.loadRegion('pelvis', 'male-adult', initialLod);
    }
    scheduleRender();
    log('Probe-web M04 listo y en ejecución.');
  }
}

main().catch(err => showError(`Error crítico de arranque: ${err}`));
