import json
d = json.load(open("reports/pelvis-catalog-candidate.json"))
structs = d["structures"]
print(f"Total: {len(structs)}")
for s in structs:
    sid = s["id"]
    es = s["labels"]["es-MX"]
    en = s["labels"]["en"]
    side = s.get("side", "?")
    print(f"{sid} | {es} | {en} | {side}")
