#!/usr/bin/env python3
"""
tools/test_m04_streaming.py
Automated browser test suite for M04:
- Cold Fetch & First Render
- Warm Cache Hit (0 network requests)
- Offline Persistence & Recoverable Error on Cache Miss
- SHA-256 Cache Corruption Detection & Auto-Purge
- 20x Rapid Atomic LOD Swap (Geometry & TA2 ID retention, no monotonic memory leak)
- Request Cancellation & Generational Token (A -> B -> A)
- GPU Device Loss & Surface Recovery (Reporting SIMULATED_PASS)
- Render-on-Demand Idle Inactivity
- Dual Backend (WebGPU and WebGL2)
"""

import http.server
import json
import os
import sys
import threading
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from serve_probe import DualWasmHandler

PORT = 8098
REPORTS_DIR = ROOT / "reports" / "implementation" / "M04"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def main():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), DualWasmHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    suite_results = {
        "status": "RUNNING",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "test_cases": [],
        "memory_metrics": {},
        "cache_metrics": {},
    }

    try:
        with sync_playwright() as pw:
            chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
            browser = pw.chromium.launch(
                executable_path=chrome_path,
                headless=True,
                args=[
                    "--enable-unsafe-webgpu",
                    "--use-angle=d3d11",
                    "--disable-gpu-sandbox",
                ],
            )

            try:
                # -------------------------------------------------------------
                # Test 1 & 2: WebGPU Cold Fetch & Warm Cache Hit
                # -------------------------------------------------------------
                print("[M04-TEST] 1. Cold Fetch vs Warm Cache Hit (WebGPU)...", flush=True)
                ctx = browser.new_context(viewport={"width": 1280, "height": 800})
                page = ctx.new_page()
                glb_requests = []
                page.on(
                    "response",
                    lambda r: glb_requests.append(
                        {"url": r.url.split("/")[-1], "status": r.status}
                    )
                    if r.url.endswith(".glb")
                    else None,
                )

                # Cold load
                page.goto(
                    f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0",
                    wait_until="domcontentloaded",
                )
                page.wait_for_function(
                    'document.documentElement.dataset.atlasProbeStatus === "ready"',
                    timeout=30000,
                )

                cold_glb_count = len(glb_requests)
                backend_active = page.locator("#stat-backend").inner_text()
                tris_cold = page.locator("#stat-tris").inner_text()
                cache_status_cold = page.locator("#stat-cache").inner_text()

                cold_pass = (
                    cold_glb_count >= 1
                    and backend_active == "WEBGPU"
                    and "38,605" in tris_cold
                )
                suite_results["test_cases"].append({
                    "name": "cold_fetch_webgpu",
                    "status": "PASS" if cold_pass else "FAIL",
                    "glb_network_requests": cold_glb_count,
                    "backend": backend_active,
                    "triangles": tris_cold,
                    "cache_label": cache_status_cold,
                })
                print(
                    f"  -> Cold fetch: {cold_glb_count} GLB request(s), Backend={backend_active}, Tris={tris_cold} (PASS={cold_pass})"
                )

                # Warm reload (same page context with CacheStorage active)
                print("[M04-TEST] 2. Warm Cache Hit Reload...", flush=True)
                glb_requests.clear()
                page.reload(wait_until="domcontentloaded")
                page.wait_for_function(
                    'document.documentElement.dataset.atlasProbeStatus === "ready"',
                    timeout=30000,
                )

                warm_glb_count = len(glb_requests)
                cache_status_warm = page.locator("#stat-cache").inner_text()
                tris_warm = page.locator("#stat-tris").inner_text()

                warm_pass = (
                    warm_glb_count == 0
                    and "HIT" in cache_status_warm
                    and "38,605" in tris_warm
                )
                suite_results["test_cases"].append({
                    "name": "warm_cache_hit",
                    "status": "PASS" if warm_pass else "FAIL",
                    "glb_network_requests": warm_glb_count,
                    "cache_label": cache_status_warm,
                    "triangles": tris_warm,
                })
                print(
                    f"  -> Warm reload: {warm_glb_count} GLB network requests, Cache={cache_status_warm} (PASS={warm_pass})"
                )

                # -------------------------------------------------------------
                # Test 3: Offline Mode & Recoverable Error on Uncached Miss
                # -------------------------------------------------------------
                print("[M04-TEST] 3. Offline Mode & Cache Miss Behavior...", flush=True)
                # Test 3a: Cached asset loads offline
                offline_cached_result = page.evaluate("""async () => {
                    window.__atlasStreamManager.simulatedOffline = true;
                    // LOD 0 is already in cache
                    const ok = await window.__atlasStreamManager.loadRegion('pelvis', 'male-adult', 0);
                    return { ok, cacheHits: window.__atlasStreamManager.stats.cacheHits };
                }""")
                offline_hit_pass = offline_cached_result.get("ok") is True

                # Test 3b: Uncached asset when offline produces recoverable error, not crash
                offline_miss_result = page.evaluate("""async () => {
                    window.__atlasStreamManager.simulatedOffline = true;
                    // Purge cache entry for LOD 1 to simulate uncached asset offline
                    const cache = await window.__atlasStreamManager.getCache();
                    if (cache) {
                        const keys = await cache.keys();
                        for (const k of keys) {
                            if (k.url.includes('pelvis-lod1')) await cache.delete(k);
                        }
                    }
                    const ok = await window.__atlasStreamManager.loadRegion('pelvis', 'male-adult', 1);
                    return { ok };
                }""")
                offline_miss_pass = offline_miss_result.get("ok") is False

                # Restore online
                page.evaluate("window.__atlasStreamManager.simulatedOffline = false;")
                suite_results["test_cases"].append({
                    "name": "offline_mode_resilience",
                    "status": "PASS"
                    if (offline_hit_pass and offline_miss_pass)
                    else "FAIL",
                    "cached_load_offline": offline_hit_pass,
                    "uncached_error_graceful": offline_miss_pass,
                })
                print(
                    f"  -> Offline cached load: {offline_hit_pass}, Uncached miss rejected cleanly: {offline_miss_pass}"
                )

                # -------------------------------------------------------------
                # Test 4: Cache Corruption Detection & Auto-Purge
                # -------------------------------------------------------------
                print("[M04-TEST] 4. Cache Corruption Detection & Auto-Purge...", flush=True)
                corrupt_result = page.evaluate("""async () => {
                    const cache = await window.__atlasStreamManager.getCache();
                    if (!cache) return { supported: false };
                    // Find LOD0 key
                    const keys = await cache.keys();
                    let targetKey = null;
                    for (const k of keys) {
                        if (k.url.includes('pelvis-base-lod0')) {
                            targetKey = k;
                            break;
                        }
                    }
                    if (!targetKey) return { targetFound: false };
                    // Overwrite with corrupted byte buffer
                    const corruptBytes = new Uint8Array([0xde, 0xad, 0xbe, 0xef, 0x00, 0x01, 0x02]);
                    await cache.put(targetKey, new Response(corruptBytes));

                    // Now attempt to load LOD 0
                    // The manager should detect digest mismatch, delete corrupted entry, and re-fetch from network
                    const reloaded = await window.__atlasStreamManager.loadRegion('pelvis', 'male-adult', 0);
                    // Check if entry in cache is now valid
                    const recheck = await cache.match(targetKey);
                    let recheckOk = false;
                    if (recheck) {
                        const buf = await recheck.arrayBuffer();
                        const h = await window.__atlasStreamManager.computeSha256(buf);
                        recheckOk = (h === '1510ed9a93b54c8067543b4a13e92ee713f1d75adc2687324ad29a72b76244ae');
                    }
                    return { supported: true, reloaded, recheckOk };
                }""")
                corrupt_pass = corrupt_result.get("reloaded") is True and corrupt_result.get(
                    "recheckOk"
                ) is True
                suite_results["test_cases"].append({
                    "name": "cache_corruption_recovery",
                    "status": "PASS" if corrupt_pass else "FAIL",
                    "detail": corrupt_result,
                })
                print(
                    f"  -> Cache corruption detected, purged and recovered: {corrupt_pass}"
                )

                # -------------------------------------------------------------
                # Test 5: 20x Rapid Atomic LOD Swap & ID/Memory Retention
                # -------------------------------------------------------------
                print("[M04-TEST] 5. 20x Rapid Atomic LOD Swap...", flush=True)
                # Select an item and isolate it first to ensure state transfers across swaps
                page.locator(".structure-item").first.click()
                selected_before = page.locator("#stat-selected").inner_text()
                page.locator("#btn-isolate").click()
                isolated_nodes_before = page.locator("#stat-nodes").inner_text()

                rapid_result = page.evaluate("""async () => {
                    return await window.__runRapidLodToggle(20);
                }""")

                selected_after = page.locator("#stat-selected").inner_text()
                isolated_nodes_after = page.locator("#stat-nodes").inner_text()
                structures_count = page.locator(".structure-item").count()

                selection_preserved = (selected_before == selected_after)
                isolation_preserved = ("1/" in isolated_nodes_after)
                swap_pass = (
                    rapid_result.get("pass") is True
                    and selection_preserved
                    and isolation_preserved
                    and structures_count == 26
                )

                suite_results["test_cases"].append({
                    "name": "rapid_20x_atomic_lod_swap",
                    "status": "PASS" if swap_pass else "FAIL",
                    "selection_preserved": selection_preserved,
                    "isolation_preserved": isolation_preserved,
                    "structures_count": structures_count,
                    "rapid_metrics": rapid_result,
                })
                suite_results["memory_metrics"]["20x_swap"] = rapid_result
                print(
                    f"  -> 20x LOD Swap: PASS={swap_pass}, TA2 IDs={structures_count}/26, Selection={selection_preserved}, Isolation={isolation_preserved}"
                )
                print(
                    f"     Pico GPU: {rapid_result.get('peakGpuBytes')} B, Final GPU: {rapid_result.get('finalGpuBytes')} B"
                )

                # Restore visibility
                page.locator("#btn-reset-vis").click()

                # -------------------------------------------------------------
                # Test 6: Request Cancellation & Race Condition (A -> B -> A)
                # -------------------------------------------------------------
                print("[M04-TEST] 6. Request Cancellation & Superseding...", flush=True)
                race_result = page.evaluate("""async () => {
                    const sm = window.__atlasStreamManager;
                    // Fire 3 calls rapidly without awaiting
                    const p1 = sm.loadRegion('pelvis', 'male-adult', 0);
                    const p2 = sm.loadRegion('pelvis', 'male-adult', 1);
                    const p3 = sm.loadRegion('pelvis', 'male-adult', 0);
                    const results = await Promise.all([p1, p2, p3]);
                    const currentGen = window.__atlasEngine().currentGeneration();
                    const stats = window.__atlasEngine().getStats();
                    return { results, currentGen, tris: stats.triangle_count };
                }""")
                race_pass = (
                    race_result.get("tris") == 38605
                )  # The last winning request was LOD 0 (38,605)
                suite_results["test_cases"].append({
                    "name": "request_cancellation_race_resolution",
                    "status": "PASS" if race_pass else "FAIL",
                    "detail": race_result,
                })
                print(
                    f"  -> Race cancellation: Final winning Tris={race_result.get('tris')} (PASS={race_pass})"
                )

                # -------------------------------------------------------------
                # Test 7: GPU Device Loss Simulation & Recovery
                # -------------------------------------------------------------
                print("[M04-TEST] 7. GPU Device Loss Simulation...", flush=True)
                device_loss_result = page.evaluate("""async () => {
                    return await window.__simulateDeviceLoss();
                }""")
                time.sleep(1.0)
                page.wait_for_function(
                    'document.documentElement.dataset.atlasProbeStatus === "ready"',
                    timeout=15000,
                )
                recovered_nodes = page.locator("#stat-nodes").inner_text()
                recovered_backend = page.locator("#stat-backend").inner_text()
                dev_pass = device_loss_result is True and "26/" in recovered_nodes

                suite_results["test_cases"].append({
                    "name": "simulated_device_loss_recovery",
                    "status": "SIMULATED_PASS" if dev_pass else "FAIL",
                    "recovered_nodes": recovered_nodes,
                    "recovered_backend": recovered_backend,
                })
                print(
                    f"  -> Simulated Device Loss Recovery: {dev_pass} (Status: SIMULATED_PASS, Backend={recovered_backend})"
                )

                # -------------------------------------------------------------
                # Test 8: Render-on-demand Inactivity Verification
                # -------------------------------------------------------------
                print("[M04-TEST] 8. Render-on-Demand Idle Inactivity...", flush=True)
                idle_frames_rendered = page.evaluate("""() => {
                    const engine = window.__atlasEngine();
                    // When idle and no interaction occurred, renderFrame returns false
                    return engine.renderFrame();
                }""")
                idle_pass = (idle_frames_rendered is False)
                suite_results["test_cases"].append({
                    "name": "render_on_demand_inactivity",
                    "status": "PASS" if idle_pass else "FAIL",
                    "idle_rendered": idle_frames_rendered,
                })
                print(
                    f"  -> Idle renderFrame returned: {idle_frames_rendered} (PASS={idle_pass})"
                )

                # -------------------------------------------------------------
                # Test 9: WebGL2 Backend Verification with Stream Manager
                # -------------------------------------------------------------
                print("[M04-TEST] 9. WebGL2 Backend Streaming...", flush=True)
                ctx_gl2 = browser.new_context(viewport={"width": 1280, "height": 800})
                page_gl2 = ctx_gl2.new_page()
                page_gl2.goto(
                    f"http://127.0.0.1:{PORT}/index.html?backend=webgl2&scene=pelvis&lod=1",
                    wait_until="domcontentloaded",
                )
                page_gl2.wait_for_function(
                    'document.documentElement.dataset.atlasProbeStatus === "ready"',
                    timeout=30000,
                )
                backend_gl2 = page_gl2.locator("#stat-backend").inner_text()
                tris_gl2 = page_gl2.locator("#stat-tris").inner_text()
                nodes_gl2 = page_gl2.locator("#stat-nodes").inner_text()

                gl2_pass = (
                    backend_gl2 == "WEBGL2"
                    and "33,758" in tris_gl2
                    and "26/" in nodes_gl2
                )
                suite_results["test_cases"].append({
                    "name": "webgl2_streaming_lod1",
                    "status": "PASS" if gl2_pass else "FAIL",
                    "backend": backend_gl2,
                    "triangles": tris_gl2,
                    "nodes": nodes_gl2,
                })
                print(
                    f"  -> WebGL2 Streaming LOD1: Backend={backend_gl2}, Tris={tris_gl2}, Nodes={nodes_gl2} (PASS={gl2_pass})"
                )
                ctx_gl2.close()

                # Screenshot capture of active M04 viewer
                shot_path = REPORTS_DIR / "m04-probe-rendered.png"
                page.screenshot(path=str(shot_path), full_page=True)
                print(f"  -> Captura auténtica guardada en: {shot_path}")

                ctx.close()
            finally:
                browser.close()
    finally:
        server.shutdown()

    # Determine overall status
    all_passed = all(
        c["status"] in ("PASS", "SIMULATED_PASS")
        for c in suite_results["test_cases"]
    )
    suite_results["status"] = "PASS" if all_passed else "FAIL"

    out_file = REPORTS_DIR / "m04-streaming-suite-result.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(suite_results, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f" M04 TEST SUITE VERDICT: {suite_results['status']}")
    print(f" Resultados guardados en: {out_file}")
    print("=" * 70)

    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
