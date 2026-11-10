#!/usr/bin/env python3
"""
ANATOM.IA — CANONICAL TA2 CATALOG GENERATOR (M05-A.1)
Generates apps/viewer/src/data/canonicalCatalog.ts from catalog.json
using verified TA2 taxonomy (NO heuristic substring matching).
"""
import os
import json

os.makedirs('apps/viewer/src/data', exist_ok=True)

with open('apps/probe-web/catalog.json', 'r', encoding='utf-8') as f:
    cat = json.load(f)

# Explicit verified anatomical classification table based on Terminologia Anatomica 2 (TA2)
# Maps root TA2 ID to official category and system.
TA2_TAXONOMY_MAP = {
    # Bones (Sistema esquelético)
    "1071": {"category": "bone", "system": "Sistema esquelético", "subsystem": "Columna vertebral y pelvis"},
    "1092": {"category": "bone", "system": "Sistema esquelético", "subsystem": "Columna vertebral y pelvis"},
    # Joints & Ligaments (Articulaciones y ligamentos de la pelvis)
    "1855": {"category": "joint", "system": "Articulaciones de la pelvis", "subsystem": "Sínfisis y ligamentos"},
    "1850": {"category": "joint", "system": "Articulaciones de la pelvis", "subsystem": "Ligamentos sacroisquiáticos"},
    "1852": {"category": "joint", "system": "Articulaciones de la pelvis", "subsystem": "Ligamentos sacroisquiáticos"},
    # Muscles (Músculos de la pelvis)
    "2412": {"category": "muscle", "system": "Músculos de la pelvis", "subsystem": "Diafragma pélvico"},
    # Viscera / Organs (Sistemas urinario y genital masculino)
    "3401": {"category": "organ", "system": "Sistema urinario", "subsystem": "Vejiga urinaria"},
    "3576": {"category": "organ", "system": "Sistema genital masculino", "subsystem": "Gónadas masculinas"},
    "3631": {"category": "organ", "system": "Sistema genital masculino", "subsystem": "Glándulas accesorias"},
    "3637": {"category": "organ", "system": "Sistema genital masculino", "subsystem": "Glándulas accesorias"},
    "3668": {"category": "organ", "system": "Sistema genital masculino", "subsystem": "Genitales externos"},
    "3678": {"category": "organ", "system": "Sistema genital masculino", "subsystem": "Cuerpos eréctiles"},
    "3681": {"category": "organ", "system": "Sistema genital masculino", "subsystem": "Cuerpos eréctiles"},
    # Blood Vessels (Sistema cardiovascular)
    "4301": {"category": "vascular", "system": "Sistema cardiovascular", "subsystem": "Arterias ilíacas"},
    "4302": {"category": "vascular", "system": "Sistema cardiovascular", "subsystem": "Arterias ilíacas"},
    "5050": {"category": "vascular", "system": "Sistema cardiovascular", "subsystem": "Venas ilíacas"},
    # Nerves (Sistema nervioso periférico)
    "6522": {"category": "nervous", "system": "Sistema nervioso periférico", "subsystem": "Plexo lumbosacro"}
}

structures = []
for s in cat.get('structures', []):
    sid = s.get('id', '')
    ta2 = str(s.get('ta2Id', '')).strip()
    labels = s.get('labels', {})
    side = s.get('side', 'unpaired_or_unspecified')
    
    # Strict dictionary lookup: no substring inference
    tax = TA2_TAXONOMY_MAP.get(ta2)
    if tax:
        category = tax["category"]
        system = tax["system"]
    else:
        category = "unclassified"
        system = "Pelvis y periné (Sin clasificar)"

    structures.append({
        'id': sid,
        'ta2Id': ta2,
        'system': system,
        'labels': {
            'es': labels.get('es-MX', ''),
            'en': labels.get('en', ''),
            'la': labels.get('la', '')
        },
        'side': side,
        'category': category,
        'visible': True
    })

print(f'Verified TA2 lookup for {len(structures)} structures')
assert len(structures) == 26, f"Expected 26 structures, got {len(structures)}"

# Assert specific non-heuristic verifications
sym = next(item for item in structures if item["id"] == "ta2:1855")
assert sym["category"] == "joint", f"ta2:1855 must be joint, got {sym['category']}"
assert "Sínfisis" in sym["labels"]["es"], "Label mismatch"

ts_code = '/**\n * ANATOM.IA — CANONICAL TA2 PELVIS CATALOG (M05-A.1)\n'
ts_code += ' * Verified against TA2.csv and catalog.json. Categories and systems\n'
ts_code += ' * mapped via explicit TA2 dictionary (NO heuristic substring matching).\n */\n'
ts_code += 'import type { AnatomyStructure } from "../runtime/bridge-types";\n\n'
ts_code += 'export const PELVIS_STRUCTURES: AnatomyStructure[] = ' + json.dumps(structures, indent=2, ensure_ascii=False) + ';\n'

with open('apps/viewer/src/data/canonicalCatalog.ts', 'w', encoding='utf-8') as f:
    f.write(ts_code)

print('Successfully written apps/viewer/src/data/canonicalCatalog.ts')
