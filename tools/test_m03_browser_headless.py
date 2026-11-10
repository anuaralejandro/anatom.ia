#!/usr/bin/env python3
"""
tools/test_m03_browser_headless.py
Ejecuta pruebas en navegador headless para verificar los artefactos de M03 (LOD0 y LOD1)
renderizados por atlas-core / atlas-web.
"""
import http.server
import json
import os
import re
import socketserver
import subprocess
import sys
import threading
import time

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

PORT = 8087
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

def run_test(browser_path, url, screenshot_path, time_budget_ms=16000):
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
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
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

    os.makedirs("reports/implementation/M03", exist_ok=True)
    results = {}

    # Test 1: M03 Pelvis Base LOD0 (Auto backend)
    sc1 = os.path.abspath("reports/implementation/M03/probe-pelvis-base-lod0.png")
    code1, dom1, err1 = run_test(
        browser,
        f"http://localhost:{PORT}/index.html?backend=auto&scene=pelvis",
        sc1,
        time_budget_ms=16000
    )
    has_26_1 = "26 / 26" in dom1 or "ta2:1071" in dom1
    ready1 = 'data-atlas-probe-status="ready"' in dom1
    backend1 = re.search(r'data-atlas-backend="([^"]+)"', dom1)
    results["m03_pelvis_base_lod0"] = {
        "verified_ready": bool(code1 == 0 and ready1 and has_26_1),
        "backend": backend1.group(1) if backend1 else None,
        "exit_code": code1,
        "screenshot_exists": os.path.exists(sc1),
        "screenshot_size": os.path.getsize(sc1) if os.path.exists(sc1) else 0,
        "dom_has_structures": has_26_1,
        "package": "pelvis-base-lod0.glb",
    }

    # Test 2: M03 Pelvis LOD1 (WebGL2 forzado)
    sc2 = os.path.abspath("reports/implementation/M03/probe-pelvis-lod1.png")
    code2, dom2, err2 = run_test(
        browser,
        f"http://localhost:{PORT}/index.html?backend=webgl2&scene=pelvis-lod1",
        sc2,
        time_budget_ms=8000
    )
    has_26_2 = "26 / 26" in dom2 or "ta2:1071" in dom2
    ready2 = 'data-atlas-probe-status="ready"' in dom2
    backend2 = re.search(r'data-atlas-backend="([^"]+)"', dom2)
    results["m03_pelvis_lod1_webgl2"] = {
        "verified_ready": bool(code2 == 0 and ready2 and has_26_2),
        "backend": backend2.group(1) if backend2 else None,
        "exit_code": code2,
        "screenshot_exists": os.path.exists(sc2),
        "screenshot_size": os.path.getsize(sc2) if os.path.exists(sc2) else 0,
        "dom_has_structures": has_26_2,
        "package": "pelvis-lod1.glb",
    }

    report_path = "reports/implementation/M03/browser-headless-audit.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"[+] Reporte guardado en: {report_path}")

    all_passed = True
    for k, v in results.items():
        print(f" -> {k}: ready={v['verified_ready']}, backend={v['backend']}, code={v['exit_code']}, screenshot={v['screenshot_exists']} ({v['screenshot_size']} bytes)")
        if not v["verified_ready"]:
            all_passed = False

    httpd.shutdown()
    if not all_passed:
        print("[!] Alguna prueba falló.")
        sys.exit(2)
    else:
        print("[+] Todas las pruebas de navegador headless para M03 pasaron exitosamente.")

if __name__ == "__main__":
    main()
