from pathlib import Path
root=Path(r"C:\Users\datam\Documents\anatom.ia")
p=root/"apps/probe-web/app.js"
s=p.read_text(encoding="utf-8")
def swap(a,b,count=1):
    global s
    assert s.count(a)==count,(a[:50],s.count(a))
    s=s.replace(a,b,count)

swap("  fps: 0,\n};",'''  fps: 0,
  sceneLoaded: false,
};
document.documentElement.dataset.atlasProbeStatus = 'booting';''')
swap("function showError(msg) {\n  log(msg, 'err');",'''function showError(msg) {
  document.documentElement.dataset.atlasProbeStatus = 'error';
  log(msg, 'err');''')
swap("function showLoading(text) {\n  el.loadingText.textContent = text;",'''function showLoading(text) {
  document.documentElement.dataset.atlasProbeStatus = 'loading';
  el.loadingText.textContent = text;''')
swap("// Load WASM engine module based on requested backend",'''// Time-box a stalled browser WebGPU adapter/device request before auto fallback.
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
// Load WASM engine module based on requested backend''')
swap("  state.requestedBackend = backendReq;",'''  state.sceneLoaded = false;
  document.documentElement.dataset.atlasBackend = 'none';
  state.requestedBackend = backendReq;''')
swap("""        const caps = await engine.initialize(canvas, {
          preferred_backend: 'webgpu',
          power_preference: 'high-performance',
          dpr: window.devicePixelRatio || 1.0,
        });""","""        const caps = await initializeWithTimeout(engine, canvas, {
          preferred_backend: 'webgpu',
          power_preference: 'high-performance',
          dpr: window.devicePixelRatio || 1.0,
        }, backendReq === 'auto' ? 5500 : 12000);""")
swap("  // Update UI badges\n  el.statBackend.textContent",'''  // Update UI badges
  document.documentElement.dataset.atlasBackend = state.activeBackend;
  el.statBackend.textContent''')
swap("  state.activeScene = sceneType;\n  el.sceneSelect.value = sceneType;",'''  state.sceneLoaded = false;
  state.activeScene = sceneType;
  document.documentElement.dataset.atlasScene = sceneType;
  el.sceneSelect.value = sceneType;''')
swap("      updateStats();\n      scheduleRender();\n      hideLoading();",'''      state.sceneLoaded = true;
      updateStats();
      scheduleRender();
      hideLoading();''',2)
swap("  if (rendered) {\n    state.frameCount++;",'''  if (rendered) {
    state.frameCount++;
    if (state.sceneLoaded) {
      // Used by headless testing: only ready after a successful WASM-rendered frame.
      document.documentElement.dataset.atlasProbeStatus = 'ready';
      document.documentElement.dataset.atlasBackend = state.activeBackend || 'unknown';
      document.documentElement.dataset.atlasScene = state.activeScene;
    }''')
p.write_text(s,encoding="utf-8")
for name in ("serve_probe.py","test_browser_headless.py"):
    p=root/"tools"/name
    c=p.read_text(encoding="utf-8")
    old='socketserver.TCPServer(("", '
    assert c.count(old)==1,(name,c.count(old))
    p.write_text(c.replace(old,'socketserver.TCPServer(("127.0.0.1", ',1),encoding="utf-8")
p=root/"tools/test_browser_headless.py"
s=p.read_text(encoding="utf-8")
def patch(a,b):
    global s
    assert s.count(a)==1,(a[:60],s.count(a))
    s=s.replace(a,b,1)
patch("import json\n", "import json\nimport re\n")
patch("timeout=30)", "timeout=45)")
patch('reports/implementation/M02/probe-auto-headless.png','reports/implementation/M02/probe-auto-audit.png')
patch('reports/implementation/M01/probe-webgl2-headless.png','reports/implementation/M01/probe-webgl2-audit.png')
patch('reports/implementation/M01/probe-cube-headless.png','reports/implementation/M01/probe-cube-audit.png')
patch("time_budget_ms=7000\n    )\n    has_26","time_budget_ms=16000\n    )\n    has_26")
patch('''    results["auto_pelvis"] = {
        "exit_code": code1,''','''    ready1 = 'data-atlas-probe-status="ready"' in dom1
    backend1 = re.search(r'data-atlas-backend="([^"]+)"', dom1)
    scene1 = 'data-atlas-scene="pelvis"' in dom1
    results["auto_pelvis"] = {
        "verified_ready": bool(code1 == 0 and ready1 and backend1 and scene1 and has_26),
        "backend": backend1.group(1) if backend1 else None,
        "exit_code": code1,''')
patch('''    results["webgl2_pelvis"] = {
        "exit_code": code2,''','''    ready2 = 'data-atlas-probe-status="ready"' in dom2
    backend2 = 'data-atlas-backend="webgl2"' in dom2
    scene2 = 'data-atlas-scene="pelvis"' in dom2
    results["webgl2_pelvis"] = {
        "verified_ready": bool(code2 == 0 and ready2 and backend2 and scene2 and "ta2:1071" in dom2),
        "backend": "webgl2" if backend2 else None,
        "exit_code": code2,''')
patch('''    results["synthetic_cube"] = {
        "exit_code": code3,''','''    ready3 = 'data-atlas-probe-status="ready"' in dom3 and 'data-atlas-scene="cube"' in dom3
    results["synthetic_cube"] = {
        "verified_ready": bool(code3 == 0 and ready3),
        "exit_code": code3,''')
patch('reports/implementation/M02/browser-headless-execution.json','reports/implementation/M02/browser-headless-audit.json')
patch('''        print(f" -> {k}: code={v['exit_code']}, screenshot={v['screenshot_exists']} ({v['screenshot_size']} bytes)")''','''        print(f" -> {k}: ready={v['verified_ready']}, code={v['exit_code']}, screenshot={v['screenshot_exists']} ({v['screenshot_size']} bytes)")''')
patch('''    httpd.shutdown()

if __name__ == "__main__":
    main()''','''    httpd.shutdown()
    if not all(item["verified_ready"] for item in results.values()):
        sys.exit(2)

if __name__ == "__main__":
    main()''')
p.write_text(s,encoding="utf-8")
print("PATCHED browser readiness, bounded auto fallback, and localhost-only servers.")
