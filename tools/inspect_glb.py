#!/usr/bin/env python3
"""Read-only glTF/GLB metadata inventory. Does not copy, modify or decode geometry."""
import json
import struct
import sys
from pathlib import Path

def summarize(path: Path):
    with path.open("rb") as f:
        header = f.read(12)
        if len(header) != 12:
            raise ValueError("Too small for GLB header")
        magic, version, declared_len = struct.unpack("<4sII", header)
        if magic != b"glTF" or version != 2:
            raise ValueError(f"Not GLB 2.0 (magic={magic!r}, version={version})")
        if declared_len != path.stat().st_size:
            raise ValueError("GLB header length does not match file size")
        chunk_header = f.read(8)
        if len(chunk_header) != 8:
            raise ValueError("Missing JSON chunk header")
        json_len, chunk_type = struct.unpack("<II", chunk_header)
        if chunk_type != 0x4E4F534A or json_len > 250_000_000:
            raise ValueError("Invalid or excessively large JSON chunk")
        data = json.loads(f.read(json_len).decode("utf-8").rstrip(" \x00"))
    accessors = data.get("accessors", [])
    primitives = [p for mesh in data.get("meshes", []) for p in mesh.get("primitives", [])]
    triangles = 0
    for p in primitives:
        if p.get("mode", 4) != 4:
            continue
        idx = p.get("indices")
        if idx is not None and idx < len(accessors):
            triangles += accessors[idx].get("count", 0) // 3
        else:
            pos = p.get("attributes", {}).get("POSITION")
            if pos is not None and pos < len(accessors):
                triangles += accessors[pos].get("count", 0) // 3
    return {
        "path": str(path),
        "file_bytes": path.stat().st_size,
        "glb_version": version,
        "asset_generator": data.get("asset", {}).get("generator"),
        "asset_copyright": data.get("asset", {}).get("copyright"),
        "scenes": len(data.get("scenes", [])),
        "nodes": len(data.get("nodes", [])),
        "meshes": len(data.get("meshes", [])),
        "mesh_primitives": len(primitives),
        "triangles_nominal": triangles,
        "materials": len(data.get("materials", [])),
        "textures": len(data.get("textures", [])),
        "images": len(data.get("images", [])),
        "extensions_required": data.get("extensionsRequired", []),
        "extensions_used": data.get("extensionsUsed", []),
        "sample_node_names": [n.get("name", "") for n in data.get("nodes", [])[:12]],
        "sample_mesh_names": [m.get("name", "") for m in data.get("meshes", [])[:12]],
        "notes": "Triangle total is nominal sum of glTF primitive index counts, not measured GPU triangles. Provenance NOT established."
    }

def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/inspect_glb.py model.glb [other.glb ...]", file=sys.stderr)
        return 2
    report = {"files": [], "errors": []}
    for path_arg in sys.argv[1:]:
        path = Path(path_arg)
        try:
            report["files"].append(summarize(path))
        except Exception as exc:
            report["errors"].append({"path": str(path), "error": str(exc)})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
