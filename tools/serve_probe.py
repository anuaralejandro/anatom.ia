#!/usr/bin/env python3
"""
tools/serve_probe.py
Servidor HTTP local reproducible para ejecutar apps/probe-web de anatom.ia (M00–M02).
"""
import http.server
import os
import socketserver
import sys

PORT = 8080
DIRECTORY = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "probe-web"))

class DualWasmHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        # Headers para soportar WebAssembly y aislamiento
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

def run():
    port = PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass

    os.chdir(DIRECTORY)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), DualWasmHandler) as httpd:
        print("=" * 70)
        print(" anatom.ia — Servidor Local de Diagnóstico M00–M02")
        print("=" * 70)
        print(f" Raíz servida: {DIRECTORY}")
        print(f" URL Base:     http://localhost:{port}/index.html")
        print("\n Enlaces de prueba directa:")
        print(f" -> Auto (WebGPU -> WebGL2): http://localhost:{port}/index.html?backend=auto")
        print(f" -> WebGPU Forzado:          http://localhost:{port}/index.html?backend=webgpu")
        print(f" -> WebGL2 Forzado:          http://localhost:{port}/index.html?backend=webgl2")
        print(f" -> Cubo Sintético (M01):    http://localhost:{port}/index.html?backend=auto&scene=cube")
        print(f" -> Pelvis Real (M02):       http://localhost:{port}/index.html?backend=auto&scene=pelvis")
        print("=" * 70)
        print("Presiona Ctrl+C para detener el servidor.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor detenido por el usuario.")

if __name__ == "__main__":
    run()
