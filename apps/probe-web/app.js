// apps/probe-web/app.js
// anatom.ia — Minimal Diagnostic Probe Shell (M00-M02)

const state = {
  engine: null,
  activeBackend: null,
  requestedBackend: 'auto',
  activeScene: 'pelvis',
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

let pointerListenerController = null;

// Recreate canvas to allow switching between WebGPU and WebGL2 contexts cleanly
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

// Time-box a stalled browser WebGPU adapter/device request before auto fallback.
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
// Load WASM engine module based on requested backend
async function bootstrapEngine(backendReq) {
  showLoading(`Iniciando backend ${backendReq.toUpperCase()}...`);
  state.sceneLoaded = false;
  document.documentElement.dataset.atlasBackend = 'none';
  state.requestedBackend = backendReq;
  el.backendSelect.value = backendReq;

  // Dispose previous engine if present
  if (state.engine) {
    try {
      state.engine.dispose();
    } catch (e) {
      log(`Error disposing previous engine: ${e}`, 'warn');
    }
    state.engine = null;
  }

  const canvas = resetCanvas();

  let pkg = null;
  let effectiveBackend = null;
  let initError = null;

  // WebGPU attempt
  if (backendReq === 'webgpu' || backendReq === 'auto') {
    if (!navigator.gpu) {
      const msg = 'navigator.gpu no está disponible en este navegador/entorno.';
      log(msg, 'warn');
      if (backendReq === 'webgpu') {
        showError(msg);
        return false;
      }
    } else {
      try {
        log('Importando módulo WebGPU WASM (pkg-webgpu)...');
        pkg = await import('./pkg-webgpu/atlas_web.js');
        await pkg.default();
        log('Módulo WebGPU WASM instanciado.');

        const engine = new pkg.AtlasEngine();
        log('Solicitando inicialización de GPU con WebGPU...');
        const caps = await initializeWithTimeout(engine, canvas, {
          preferred_backend: 'webgpu',
          power_preference: 'high-performance',
          dpr: window.devicePixelRatio || 1.0,
        }, backendReq === 'auto' ? 5500 : 12000);

        effectiveBackend = caps.backend;
        state.engine = engine;
        engine.setEventCallback((event) => log('Rust event: ' + event.type + (event.id ? ' (' + event.id + ')' : '')));
        state.activeBackend = 'webgpu';
        el.statAdapter.textContent = caps.adapter_name || 'WebGPU Adapter';
        log(`WebGPU inicializado exitosamente: adapter=${caps.adapter_name}, backend=${caps.backend}`);
      } catch (err) {
        initError = err;
        log(`Fallo al inicializar WebGPU: ${err?.detail || err?.message || err}`, 'warn');
        if (backendReq === 'webgpu') {
          showError(`Fallo WebGPU: ${err?.detail || err?.message || err}`);
          return false;
        }
      }
    }
  }

  // Fallback to WebGL2 if auto or if webgl2 was requested
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
      engine.setEventCallback((event) => log('Rust event: ' + event.type + (event.id ? ' (' + event.id + ')' : '')));
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

  return true;
}

// Load Scene (Pelvis GLB or Synthetic Cube)
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
    const defaultGlb = isLod1 ? './pelvis-lod1.glb' : './pelvis-base-lod0.glb';
    const fallbackGlb = './pelvis-pbr-core-compat.glb';
    const glbUrl = window.__customModelUrl || defaultGlb;
    showLoading(isLod1 ? 'Cargando Pelvis LOD1 (M03)...' : 'Cargando Pelvis Anatómica Real (M02/M03)...');
    try {
      log(`Descargando ${glbUrl}...`);
      let resp = await fetch(glbUrl);
      if (!resp.ok && glbUrl === './pelvis-base-lod0.glb') {
        log(`Fallback a ${fallbackGlb}...`, 'warn');
        resp = await fetch(fallbackGlb);
      }
      if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
      const buffer = await resp.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      log(`GLB descargado: ${bytes.byteLength} bytes. Parseando e inicializando en atlas-core...`);

      const snapshot = state.engine.loadGlbBytes(bytes);
      log(`GLB cargado exitosamente. Región: ${snapshot.region}, visible_ids: ${snapshot.visible_ids.length}`);

      state.sceneLoaded = true;
      updateStats();
      scheduleRender();
      hideLoading();
    } catch (err) {
      showError(`Error cargando GLB anatómico: ${err?.detail || err?.message || err}`);
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

    // Name label
    const title = document.createElement('span');
    title.className = 'structure-title';
    title.textContent = item.name_es;

    // TA2 ID badge
    const tag = document.createElement('span');
    tag.className = 'structure-tag';
    tag.textContent = `TA2:${item.ta2Id}`;

    li.appendChild(chk);
    li.appendChild(title);
    li.appendChild(tag);

    li.addEventListener('click', () => {
      selectStructure(item.id);
    });

    el.structureList.appendChild(li);
  });
}

function selectStructure(id) {
  if (!state.engine) return;
  state.selectedId = id;
  state.engine.selectStructure(id);
  el.statSelected.textContent = id || 'Ninguna';

  // Highlight list item
  const items = el.structureList.querySelectorAll('.structure-item');
  items.forEach((li) => {
    if (li.dataset.id === id) {
      li.classList.add('selected');
      li.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } else {
      li.classList.remove('selected');
    }
  });

  updateStats();
  scheduleRender();
  log(`Estructura seleccionada: ${id || 'Deselección'}`);
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
      el.statNodes.textContent = stats.visible_nodes + '/' + stats.total_nodes;
      el.statPrims.textContent = stats.primitive_count;
      el.statTris.textContent = stats.triangle_count.toLocaleString();
      el.statDrawcalls.textContent = stats.draw_call_count;
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
      // Used by headless testing: only ready after a successful WASM-rendered frame.
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

  // Continue rendering while interacting (orbit/pan)
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
    isPan = e.button === 2 || e.shiftKey;
    state.isInteracting = true;
    scheduleRender();
  });

  window.addEventListener('mousemove', (e) => {
    if (!isDown || !state.engine) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      moved = true;
    }

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

    // If click without dragging: perform Raycast Picking!
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

  // Touch support (1 finger orbit, 2 finger pinch/pan)
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

// Wire action buttons
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
    // update checkboxes in list
    const items = el.structureList.querySelectorAll('.structure-item');
    items.forEach((li) => {
      const chk = li.querySelector('input[type="checkbox"]');
      if (chk) chk.checked = li.dataset.id === state.selectedId;
    });
    updateStats();
    scheduleRender();
    log(`Aislada estructura: ${state.selectedId}`);
  }
});

el.btnHide.addEventListener('click', () => {
  if (state.selectedId && state.engine) {
    state.engine.setVisibility(state.selectedId, false);
    const li = el.structureList.querySelector(`[data-id="${state.selectedId}"]`);
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

// Presets
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

// Bootstrap application on page load
async function main() {
  log('Iniciando probe-web...');
  const params = new URLSearchParams(window.location.search);
  const requestedBackend = params.get('backend') || 'auto';
  const initialScene = params.get('scene') || 'pelvis';
  const customModel = params.get('model');
  if (customModel) {
    window.__customModelUrl = customModel;
  }

  await loadStructureCatalog();

  const success = await bootstrapEngine(requestedBackend);
  if (success) {
    await loadScene(initialScene);
    scheduleRender();
    log('Probe-web listo y en ejecución.');
  }
}

main().catch(err => showError(`Error crítico de arranque: ${err}`));
