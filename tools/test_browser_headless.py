#!/usr/bin/env python3
"""
tools/test_browser_headless.py
Ejecuta pruebas reales en navegador headless (Chrome / Edge) contra apps/probe-web.
"""
import http.server
import json
import re
import os
import socketserver
import subprocess
import sys
import threading
import time

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

PORT = 8085
DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "probe-web"))

class DualWasmHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def guess_type(self, path):
        if path.endswith(".wasm"):
            return "application/wasm"
        if path.endswith(".js"):
            return "application/javascript"
        if path.endswith(".glb"):
            return "model/gltf-binary"
        return super().guess_type(path)

    def log_message(self, format, *args):
        # Silenciar logs normales de HTTP para no ensuciar stdout
        pass

def start_server():
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", PORT), DualWasmHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    return httpd

def find_browser():
    for p in CHROME_PATHS:
        if os.path.exists(p):
            return p
    return None

def run_test(browser_path, url, screenshot_path, time_budget_ms=6000):
    cmd = [
        browser_path,
        "--headless=new",
        "--enable-unsafe-webgpu",
        "--enable-features=Vulkan,WebGPU",
        "--use-angle=d3d11",
        "--disable-gpu-sandbox",
        "--window-size=1280,800",
        f"--virtual-time-budget={time_budget_ms}",
        f"--screenshot={screenshot_path}",
        "--dump-dom",
        url,
    ]
    print(f"[*] Ejecutando: {url}")
    print(f"[*] Captura destino: {screenshot_path}")
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        return proc.returncode, proc.stdout, proc.stderr
    except Exception as e:
        return -1, "", str(e)

def main():
    browser = find_browser()
    if not browser:
        print("[!] No se encontró Chrome ni Edge en rutas estándar.")
        sys.exit(1)

    print(f"[*] Navegador detectado: {browser}")
    httpd = start_server()
    print(f"[*] Servidor HTTP iniciado en puerto {PORT} (directorio: {DIRECTORY})")
    time.sleep(1)

    results = {}

    # Test 1: Auto (Pelvis real M02)
    sc1 = os.path.abspath("reports/implementation/M02/probe-auto-audit.png")
    code1, dom1, err1 = run_test(
        browser,
        f"http://localhost:{PORT}/index.html?backend=auto&scene=pelvis",
        sc1,
        time_budget_ms=16000
    )
    has_26 = "26 / 26" in dom1 or "ta2:1071" in dom1
    ready1 = 'data-atlas-probe-status="ready"' in dom1
    backend1 = re.search(r'data-atlas-backend="([^"]+)"', dom1)
    scene1 = 'data-atlas-scene="pelvis"' in dom1
    results["auto_pelvis"] = {
        "verified_ready": bool(code1 == 0 and ready1 and backend1 and scene1 and has_26),
        "backend": backend1.group(1) if backend1 else None,
        "exit_code": code1,
        "screenshot_exists": os.path.exists(sc1),
        "screenshot_size": os.path.getsize(sc1) if os.path.exists(sc1) else 0,
        "dom_has_structures": has_26,
        "dom_sample": dom1[:500] if dom1 else "",
        "stderr": err1[:500] if err1 else ""
    }

    # Test 2: WebGL2 forzado (Pelvis real M02)
    sc2 = os.path.abspath("reports/implementation/M01/probe-webgl2-audit.png")
    code2, dom2, err2 = run_test(
        browser,
        f"http://localhost:{PORT}/index.html?backend=webgl2&scene=pelvis",
        sc2,
        time_budget_ms=7000
    )
    ready2 = 'data-atlas-probe-status="ready"' in dom2
    backend2 = 'data-atlas-backend="webgl2"' in dom2
    scene2 = 'data-atlas-scene="pelvis"' in dom2
    results["webgl2_pelvis"] = {
        "verified_ready": bool(code2 == 0 and ready2 and backend2 and scene2 and "ta2:1071" in dom2),
        "backend": "webgl2" if backend2 else None,
        "exit_code": code2,
        "screenshot_exists": os.path.exists(sc2),
        "screenshot_size": os.path.getsize(sc2) if os.path.exists(sc2) else 0,
        "dom_has_structures": ("ta2:1071" in dom2),
        "stderr": err2[:500] if err2 else ""
    }

    # Test 3: Cubo Sintético (M01)
    sc3 = os.path.abspath("reports/implementation/M01/probe-cube-audit.png")
    code3, dom3, err3 = run_test(
        browser,
        f"http://localhost:{PORT}/index.html?backend=auto&scene=cube",
        sc3,
        time_budget_ms=16000
    )
    ready3 = 'data-atlas-probe-status="ready"' in dom3 and 'data-atlas-scene="cube"' in dom3
    results["synthetic_cube"] = {
        "verified_ready": bool(code3 == 0 and ready3),
        "exit_code": code3,
        "screenshot_exists": os.path.exists(sc3),
        "screenshot_size": os.path.getsize(sc3) if os.path.exists(sc3) else 0,
        "stderr": err3[:500] if err3 else ""
    }

    report_path = "reports/implementation/M02/browser-headless-audit.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[+] Resultados guardados en: {report_path}")

    for k, v in results.items():
        print(f" -> {k}: ready={v['verified_ready']}, code={v['exit_code']}, screenshot={v['screenshot_exists']} ({v['screenshot_size']} bytes)")

    httpd.shutdown()
    if not all(item["verified_ready"] for item in results.values()):
        sys.exit(2)

if __name__ == "__main__":
    main()
