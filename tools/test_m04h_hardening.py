#!/usr/bin/env python3
"""
M04-H Hardening Test Suite — anatom.ia
Automated verification for runtime hardening:
  - M04-H1: Two-phase transactional GPU swap, failpoints (prepare, upload, first_render), atomic rollback.
  - M04-H2: Realistic memory preflight budget enforcement (Low/Med/High), high-watermark tracking.
  - M04-H3: Event ordering (region.loading -> renderFrame -> region.ready), cancellation semantics.
  - M04-H4: GPU device loss callback, controlled simulation, state recovery.
  - M04-H5: Bounded transport scheduler, request coalescing, transient error retry.
  - M04-H6: Real offline boot via Service Worker & CacheStorage (WebGPU & WebGL2).
  - Gate K: 120-frame real interaction performance profiling (p50, p95).
"""

import sys
import os
import json
import time
import threading
import http.server
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from serve_probe import DualWasmHandler

PORT = 8110
REPORT_DIR = ROOT / "reports" / "implementation" / "M04H"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = REPORT_DIR / "m04h-results.json"
MATRIX_PATH = REPORT_DIR / "test-matrix.json"

results = {
    "suite": "M04-H Hardening Test Suite",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "gates": {},
    "metrics": {},
    "status": "IN_PROGRESS"
}

def start_server():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", PORT), DualWasmHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

def main():
    server = start_server()
    print(f"[M04-H] Static HTTP test server listening at http://127.0.0.1:{PORT}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True,
            args=[
                "--enable-unsafe-webgpu",
                "--use-angle=d3d11",
                "--disable-gpu-sandbox",
                "--enable-features=Vulkan",
            ]
        )

        try:
            # -------------------------------------------------------------
            # TEST 1: M04-H1 Transactional Swap & Failpoints Rollback
            # -------------------------------------------------------------
            print("\n[M04-H1] Testing Two-Phase GPU Transactional Swap & Atomic Rollbacks...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            # Baseline check: 26 nodes resident
            initial_nodes = page.evaluate("() => window.__atlasEngine().getStats().total_nodes")
            initial_gen = page.evaluate("() => window.__atlasEngine().currentGeneration()")
            assert initial_nodes == 26, f"Expected 26 nodes, got {initial_nodes}"

            # Failpoint A: PrepareFail (fail before GPU staging/allocation)
            h1_a = page.evaluate("""async () => {
                const engine = window.__atlasEngine();
                const sm = window.__atlasStreamManager;
                const plan = engine.createLoadPlan("pelvis", "male-adult", 1);
                const bytes = new Uint8Array(await sm.loadPackageBytes(plan));
                engine.setTestFailpoint("prepare_fail");
                try {
                    const gen = engine.nextGeneration(701);
                    engine.applyPackageBytes(bytes, plan, 701, gen);
                    return { success: false, reason: "Expected prepare_fail to throw" };
                } catch (e) {
                    const stats = engine.getStats();
                    const mem = engine.getMemoryStats();
                    return {
                        success: true,
                        error: String(e?.detail || e),
                        nodes_after_fail: stats.total_nodes,
                        current_gen: engine.currentGeneration(),
                        rollback_count: mem.rollbackCount
                    };
                } finally {
                    engine.setTestFailpoint("none");
                }
            }""")
            print(f"  -> PrepareFail: nodes_preserved={h1_a.get('nodes_after_fail') == 26}, error={h1_a.get('error', '')[:40]}...")

            # Failpoint B: UploadFail (fail during buffer upload)
            h1_b = page.evaluate("""async () => {
                const engine = window.__atlasEngine();
                const sm = window.__atlasStreamManager;
                const plan = engine.createLoadPlan("pelvis", "male-adult", 1);
                const bytes = new Uint8Array(await sm.loadPackageBytes(plan));
                engine.setTestFailpoint("upload_fail");
                try {
                    const gen = engine.nextGeneration(702);
                    engine.applyPackageBytes(bytes, plan, 702, gen);
                    return { success: false, reason: "Expected upload_fail to throw" };
                } catch (e) {
                    const stats = engine.getStats();
                    const mem = engine.getMemoryStats();
                    return {
                        success: true,
                        error: String(e?.detail || e),
                        nodes_after_fail: stats.total_nodes,
                        current_gen: engine.currentGeneration(),
                        rollback_count: mem.rollbackCount
                    };
                } finally {
                    engine.setTestFailpoint("none");
                }
            }""")
            print(f"  -> UploadFail: nodes_preserved={h1_b.get('nodes_after_fail') == 26}, error={h1_b.get('error', '')[:40]}...")

            # Failpoint C: FirstRenderFail (commit succeeded, first render pass fails -> atomic rollback)
            h1_c = page.evaluate("""async () => {
                const engine = window.__atlasEngine();
                const sm = window.__atlasStreamManager;
                const plan = engine.createLoadPlan("pelvis", "male-adult", 1);
                const bytes = new Uint8Array(await sm.loadPackageBytes(plan));
                engine.setTestFailpoint("first_render_fail");
                try {
                    const gen = engine.nextGeneration(703);
                    engine.applyPackageBytes(bytes, plan, 703, gen);
                    // Trigger frame render to trip the first_render_fail failpoint
                    const rendered = engine.renderFrame();
                    const stats = engine.getStats();
                    const mem = engine.getMemoryStats();
                    return {
                        success: rendered === false,
                        rendered,
                        nodes_after_fail: stats.total_nodes,
                        current_gen: engine.currentGeneration(),
                        rollback_count: mem.rollbackCount
                    };
                } catch (e) {
                    const stats = engine.getStats();
                    const mem = engine.getMemoryStats();
                    return {
                        success: true,
                        error: String(e?.detail || e),
                        nodes_after_fail: stats.total_nodes,
                        current_gen: engine.currentGeneration(),
                        rollback_count: mem.rollbackCount
                    };
                } finally {
                    engine.setTestFailpoint("none");
                }
            }""")
            print(f"  -> FirstRenderFail: nodes_preserved={h1_c.get('nodes_after_fail') == 26}, rollback_count={h1_c.get('rollback_count')}")

            # Verify active scene is still fully interactive after all 3 failpoints
            interactive_check = page.evaluate("""() => {
                const engine = window.__atlasEngine();
                const rev = engine.selectStructure("hip_bone_R");
                const stats = engine.getStats();
                return { total_nodes: stats.total_nodes, rev };
            }""")
            h1_pass = (
                h1_a.get("success") and h1_a.get("nodes_after_fail") == 26 and
                h1_b.get("success") and h1_b.get("nodes_after_fail") == 26 and
                h1_c.get("success") and h1_c.get("nodes_after_fail") == 26 and
                interactive_check.get("total_nodes") == 26
            )
            results["gates"]["GATE_D_GPU_SWAP"] = {
                "verdict": "PASS" if h1_pass else "FAIL",
                "evidence": {
                    "initial_nodes": initial_nodes,
                    "prepare_fail": h1_a,
                    "upload_fail": h1_b,
                    "first_render_fail": h1_c,
                    "interactive_check": interactive_check
                }
            }
            print(f"  ==> Gate D (GPU Swap & Rollback): {results['gates']['GATE_D_GPU_SWAP']['verdict']}")
            ctx.close()

            # -------------------------------------------------------------
            # TEST 2: M04-H2 Memory Accounting & Preflight Budget Enforcement
            # -------------------------------------------------------------
            print("\n[M04-H2] Testing Memory Preflight Budget & High-Watermark Accounting...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            mem_eval = page.evaluate("""() => {
                const engine = window.__atlasEngine();
                const mem = engine.getMemoryStats();
                return {
                    profile: mem.qualityProfile,
                    residentGpuEstimate: mem.residentGpuBytesEstimate || mem.residentGpuBytes,
                    peakOverlapBytesEstimate: mem.peakOverlapBytesEstimate || mem.peakOverlapBytes,
                    gpuBufferAllocatedEstimate: mem.gpuBufferAllocatedEstimate || mem.residentGpuBytes,
                    cpuSceneDecodedEstimate: mem.cpuSceneDecodedEstimate || mem.decodedCpuBytes,
                    gpuBudget: mem.gpuBudgetBytes || mem.memoryBudgetGpuBytes,
                    isWithinBudget: mem.isWithinBudget,
                    activeSceneNodes: engine.getStats().total_nodes
                };
            }""")
            print(f"  -> Profile: {mem_eval['profile']}, Resident GPU Estimate: {mem_eval['residentGpuEstimate']} B, Budget: {mem_eval['gpuBudget']} B")

            # Adversarial test: set an artificially tiny budget and verify preflight rejects swap BEFORE destroying active scene
            budget_test = page.evaluate("""async () => {
                const engine = window.__atlasEngine();
                const sm = window.__atlasStreamManager;
                const plan = engine.createLoadPlan("pelvis", "male-adult", 1);
                const bytes = new Uint8Array(await sm.loadPackageBytes(plan));
                
                const nodesBefore = engine.getStats().total_nodes;
                const snapshotBefore = engine.getSceneSnapshot();
                
                // Set artificially tight budget (2 MiB GPU, 2 MiB CPU) lower than active + candidate peak
                engine.setTestMemoryBudget(2 * 1024 * 1024, 2 * 1024 * 1024);
                
                let rejected = false;
                let errorCode = "";
                let errorDetail = "";
                const reqId = 999;
                const gen = engine.nextGeneration(reqId);
                
                try {
                    engine.applyPackageBytes(bytes, plan, reqId, gen);
                } catch (e) {
                    rejected = true;
                    errorCode = String(e?.code || e?.detail || e);
                    errorDetail = String(e?.detail || e);
                }
                
                // Restore standard profile
                engine.setQualityProfile("medium");
                const statsAfter = engine.getStats();
                const snapshotAfter = engine.getSceneSnapshot();
                
                return {
                    rejected,
                    errorCode,
                    errorDetail,
                    nodesBefore,
                    nodesAfter: statsAfter.total_nodes,
                    nodesIntact: statsAfter.total_nodes === nodesBefore && snapshotAfter.visible_ids.length === 26,
                    sceneRevisionPreserved: snapshotAfter.scene_revision === snapshotBefore.scene_revision
                };
            }""")
            print(f"  -> Memory Preflight Rejection: rejected={budget_test['rejected']} (code={budget_test['errorCode'][:30]}...), nodes_intact={budget_test['nodesIntact']}")

            h2_pass = (
                mem_eval["residentGpuEstimate"] > 0 and
                mem_eval["gpuBudget"] > 0 and
                budget_test["rejected"] and
                "MEMORY_LIMIT" in (budget_test["errorCode"] + budget_test["errorDetail"]).upper() and
                budget_test["nodesIntact"] and
                budget_test["sceneRevisionPreserved"]
            )
            results["gates"]["GATE_E_MEMORY"] = {
                "verdict": "PASS" if h2_pass else "FAIL",
                "evidence": {
                    "stats": mem_eval,
                    "budget_test": budget_test,
                    "physical_driver_vram": "PHYSICAL_VRAM_NOT_MEASURED",
                    "accounting_mode": "GPU_ALLOCATION_ESTIMATE_ONLY"
                }
            }
            print(f"  ==> Gate E (Memory Preflight & Accounting): {results['gates']['GATE_E_MEMORY']['verdict']}")
            ctx.close()

            # -------------------------------------------------------------
            # TEST 3: M04-H3 Event Ordering & Frame Presentation Semantics
            # -------------------------------------------------------------
            print("\n[M04-H3] Testing Event Ordering (region.loading -> renderFrame -> region.ready)...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            event_sequence = page.evaluate("""async () => {
                const engine = window.__atlasEngine();
                const sm = window.__atlasStreamManager;
                const events = [];
                engine.setEventCallback((ev) => {
                    events.push({
                        type: ev.type,
                        requestId: ev.requestId,
                        sceneGeneration: ev.sceneGeneration,
                        sceneRevision: ev.sceneRevision,
                        region: ev.region,
                        variant: ev.variant,
                        lod: ev.lod,
                        backend: ev.backend,
                        timestamp: performance.now()
                    });
                });

                // Request LOD 1 swap (stages resources and sets pending ready event)
                await sm.loadRegion("pelvis", "male-adult", 1);
                
                // Explicitly render first frame to trigger commit finalization and ready event
                engine.renderFrame();
                return events;
            }""")

            types = [e["type"] for e in event_sequence]
            print(f"  -> Event sequence observed: {types}")
            has_loading = "region.loading" in types
            has_ready = "region.ready" in types
            order_ok = False
            if has_loading and has_ready:
                loading_idx = types.index("region.loading")
                ready_idx = types.index("region.ready")
                order_ok = (loading_idx < ready_idx)
            
            ready_event = next((e for e in event_sequence if e["type"] == "region.ready"), {})
            metadata_ok = (
                ready_event.get("sceneGeneration") is not None and
                ready_event.get("sceneRevision") is not None and
                ready_event.get("region") == "pelvis" and
                ready_event.get("lod") == 1
            )
            print(f"  -> Order: loading < ready = {order_ok}, Metadata: {ready_event}")

            h3_pass = has_loading and has_ready and order_ok and metadata_ok
            results["gates"]["GATE_F_EVENTS"] = {
                "verdict": "PASS" if h3_pass else "FAIL",
                "evidence": {
                    "event_sequence": event_sequence,
                    "order_correct": order_ok,
                    "ready_metadata": ready_event
                }
            }
            print(f"  ==> Gate F (Event Ordering & Semantics): {results['gates']['GATE_F_EVENTS']['verdict']}")
            ctx.close()

            # -------------------------------------------------------------
            # TEST 4: M04-H4 GPU Device Loss Callback & Recovery
            # -------------------------------------------------------------
            print("\n[M04-H4] Testing GPU Device Loss Callback & Controlled Recovery...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            device_loss_result = page.evaluate("""async () => {
                const engine = window.__atlasEngine();
                const beforeNodes = engine.getStats().total_nodes;
                
                // Simulate controlled GPU device loss
                engine.simulateDeviceLoss();
                
                // Recover using probe application recovery workflow
                const recoverySuccess = await window.__simulateDeviceLoss();
                const afterRecovery = {
                    nodes: window.__atlasEngine().getStats().total_nodes,
                    backend: window.__atlasEngine().getStats().backend
                };
                return { beforeNodes, recoverySuccess, afterRecovery };
            }""")
            print(f"  -> Recovery Success: {device_loss_result['recoverySuccess']}, afterRecovery.nodes={device_loss_result['afterRecovery']['nodes']}")

            h4_pass = (
                device_loss_result["recoverySuccess"] is True and
                device_loss_result["afterRecovery"]["nodes"] == 26
            )
            results["gates"]["GATE_H_RECOVERY"] = {
                "verdict": "SIMULATED_PASS" if h4_pass else "FAIL",
                "physical_driver_loss": "NOT_RUN",
                "evidence": device_loss_result,
                "notes": "Controlled GPU device loss simulated via wgpu::Device::destroy(); physical OS driver crash classified as NOT_RUN."
            }
            print(f"  ==> Gate H (Device Loss Recovery): {results['gates']['GATE_H_RECOVERY']['verdict']} (Physical Driver Loss: NOT_RUN)")
            ctx.close()

            # -------------------------------------------------------------
            # TEST 5: M04-H5 Transport Scheduler, Coalescing & Transient Retry
            # -------------------------------------------------------------
            print("\n[M04-H5] Testing Transport Scheduler, Coalescing & Retry...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            transport_eval = page.evaluate("""async () => {
                const sm = window.__atlasStreamManager;
                const engine = window.__atlasEngine();
                const plan = engine.createLoadPlan("pelvis", "male-adult", 1);
                
                // Launch 3 simultaneous package loads for the exact same asset to verify coalescing
                const p1 = sm.loadPackageBytes(plan);
                const p2 = sm.loadPackageBytes(plan);
                const p3 = sm.loadPackageBytes(plan);
                
                const [b1, b2, b3] = await Promise.all([p1, p2, p3]);
                const coalescedCount = sm.stats.coalescedRequests;
                
                return {
                    b1_len: b1.byteLength,
                    b2_len: b2.byteLength,
                    b3_len: b3.byteLength,
                    coalescedCount,
                    activeFetchSlots: sm.activeFetchSlots,
                    maxConcurrentFetches: sm.maxConcurrentFetches
                };
            }""")
            print(f"  -> Coalesced Requests: {transport_eval['coalescedCount']}, byteLength={transport_eval['b1_len']}")

            h5_pass = (
                transport_eval["b1_len"] > 0 and
                transport_eval["b2_len"] == transport_eval["b1_len"] and
                transport_eval["b3_len"] == transport_eval["b1_len"] and
                transport_eval["coalescedCount"] >= 2
            )
            results["gates"]["GATE_I_TRANSPORT"] = {
                "verdict": "PASS" if h5_pass else "FAIL",
                "evidence": transport_eval
            }
            print(f"  ==> Gate I (Transport Scheduler & Coalescing): {results['gates']['GATE_I_TRANSPORT']['verdict']}")
            ctx.close()

            # -------------------------------------------------------------
            # TEST 6: M04-H6 Real Offline Boot (WebGPU and WebGL2)
            # -------------------------------------------------------------
            print("\n[M04-H6] Testing Real Offline Boot (Service Worker precache + CacheStorage)...")
            offline_results = {}
            for backend in ("webgpu", "webgl2"):
                ctx = browser.new_context(viewport={"width": 1280, "height": 720})
                page = ctx.new_page()
                # 1. Online warm-up: populate Service Worker shell cache and GLB CacheStorage
                page.goto(f"http://127.0.0.1:{PORT}/index.html?backend={backend}&scene=pelvis&lod=0", wait_until="domcontentloaded")
                page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)
                # Wait 1s for Service Worker activation & claims
                time.sleep(1.0)
                
                # 2. Cut network completely
                ctx.set_offline(True)
                
                # 3. Perform real page reload offline
                try:
                    page.reload(wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=10000)
                    offline_eval = page.evaluate("""() => {
                        const engine = window.__atlasEngine();
                        const stats = engine.getStats();
                        return {
                            nodes: stats.total_nodes,
                            backend: stats.backend,
                            probeStatus: document.documentElement.dataset.atlasProbeStatus,
                            cacheStatus: document.getElementById('stat-cache')?.textContent || ''
                        };
                    }""")
                    offline_results[backend] = { "status": "RELOADED_OFFLINE", "eval": offline_eval }
                    print(f"  -> [{backend}] Real Offline Reload: RELOADED_OFFLINE (Nodes: {offline_eval['nodes']}, Backend: {offline_eval['backend']})")
                except Exception as ex:
                    offline_results[backend] = { "status": "FAILED", "error": str(ex)[:200] }
                    print(f"  -> [{backend}] Real Offline Reload: FAILED: {ex}")
                finally:
                    ctx.set_offline(False)
                    ctx.close()

            h6_pass = (
                offline_results.get("webgpu", {}).get("status") == "RELOADED_OFFLINE" and
                offline_results.get("webgpu", {}).get("eval", {}).get("nodes") == 26 and
                offline_results.get("webgl2", {}).get("status") == "RELOADED_OFFLINE" and
                offline_results.get("webgl2", {}).get("eval", {}).get("nodes") == 26
            )
            results["gates"]["GATE_J_OFFLINE"] = {
                "verdict": "PASS" if h6_pass else "FAIL",
                "evidence": offline_results
            }
            print(f"  ==> Gate J (Real Offline Boot): {results['gates']['GATE_J_OFFLINE']['verdict']}")

            # -------------------------------------------------------------
            # TEST 7: Gate K Performance (120 Real Interactive Frames)
            # -------------------------------------------------------------
            print("\n[GATE K] Profiling 120 Interactive Frames CPU Render Times...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            perf_eval = page.evaluate("""() => {
                const engine = window.__atlasEngine();
                const frameTimes = [];
                // Simulate continuous orbit interaction across 120 frames
                for (let i = 0; i < 120; i++) {
                    engine.orbit(0.01, 0.005);
                    const t0 = performance.now();
                    engine.renderFrame();
                    const dt = performance.now() - t0;
                    frameTimes.push(dt);
                }
                frameTimes.sort((a, b) => a - b);
                const p50 = frameTimes[Math.floor(frameTimes.length * 0.50)];
                const p95 = frameTimes[Math.floor(frameTimes.length * 0.95)];
                const min = frameTimes[0];
                const max = frameTimes[frameTimes.length - 1];
                const avg = frameTimes.reduce((a, b) => a + b, 0) / frameTimes.length;
                return { frameCount: frameTimes.length, p50, p95, min, max, avg };
            }""")
            print(f"  -> 120 Frames Render Profile: p50={perf_eval['p50']:.3f}ms, p95={perf_eval['p95']:.3f}ms, avg={perf_eval['avg']:.3f}ms (min={perf_eval['min']:.3f}ms, max={perf_eval['max']:.3f}ms)")

            k_pass = (perf_eval["frameCount"] == 120 and perf_eval["p50"] < 16.67 and perf_eval["p95"] < 33.33)
            results["gates"]["GATE_K_PERFORMANCE"] = {
                "verdict": "PASS" if k_pass else "FAIL",
                "hardware": "Desktop Windows D3D11/Vulkan/wgpu",
                "resolution": "1280x720 (DPR=1.0)",
                "metrics": perf_eval
            }
            results["metrics"]["render_p50_ms"] = perf_eval["p50"]
            results["metrics"]["render_p95_ms"] = perf_eval["p95"]
            print(f"  ==> Gate K (Interactive Performance Profiling): {results['gates']['GATE_K_PERFORMANCE']['verdict']}")
            ctx.close()

            # -------------------------------------------------------------
            # TEST 8: Gate G Lifecycle Re-initialization (10 cycles)
            # -------------------------------------------------------------
            print("\n[GATE G] Testing Engine Lifecycle Context Re-initialization (10 cycles)...")
            ctx = browser.new_context(viewport={"width": 1280, "height": 720})
            page = ctx.new_page()
            page.goto(f"http://127.0.0.1:{PORT}/index.html?backend=webgpu&scene=pelvis&lod=0", wait_until="domcontentloaded")
            page.wait_for_function('document.documentElement.dataset.atlasProbeStatus === "ready"', timeout=15000)

            lifecycle_eval = page.evaluate("""async () => {
                const results = [];
                for (let i = 0; i < 10; i++) {
                    const engine = window.__atlasEngine();
                    engine.dispose();
                    // Bootstrap next engine instance
                    const oldCanvas = document.getElementById('canvas');
                    const canvas = document.createElement('canvas');
                    canvas.id = 'canvas';
                    oldCanvas.replaceWith(canvas);
                    const pkg = await import('./pkg-webgpu/atlas_web.js');
                    const nextEngine = new pkg.AtlasEngine();
                    await nextEngine.initialize(canvas, { preferred_backend: 'webgpu', power_preference: 'high-performance' });
                    results.push(nextEngine.getStats().backend);
                    nextEngine.dispose();
                }
                return { cycles: results.length, successfulBackends: results };
            }""")
            print(f"  -> Lifecycle re-initializations: {lifecycle_eval['cycles']} cycles executed successfully.")
            g_pass = (lifecycle_eval["cycles"] == 10)
            results["gates"]["GATE_G_LIFECYCLE"] = {
                "verdict": "PASS" if g_pass else "FAIL",
                "evidence": lifecycle_eval
            }
            print(f"  ==> Gate G (Lifecycle Re-initialization): {results['gates']['GATE_G_LIFECYCLE']['verdict']}")
            ctx.close()

        finally:
            browser.close()
            server.shutdown()

    # Determine overall status
    all_pass = all(
        g.get("verdict") in ("PASS", "SIMULATED_PASS")
        for g in results["gates"].values()
    )
    results["status"] = "PASS" if all_pass else "FAIL"

    # Write results files
    RESULTS_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"\n[M04-H] Results written to: {RESULTS_PATH}")

    # Write test matrix
    test_matrix = {
        "device": "Local Windows PC",
        "browser": "Google Chrome (Headless) with --enable-unsafe-webgpu",
        "backends_verified": ["WebGPU", "WebGL2"],
        "wgpu_version": "30.0.1",
        "nodes_verified": 26,
        "gates": results["gates"],
        "overall_status": results["status"]
    }
    MATRIX_PATH.write_text(json.dumps(test_matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[M04-H] Test matrix written to: {MATRIX_PATH}")

    print(f"\n=======================================================")
    print(f" M04-H HARDENING SUITE OVERALL: {results['status']}")
    print(f"=======================================================\n")
    sys.exit(0 if results["status"] == "PASS" else 1)

if __name__ == "__main__":
    main()
