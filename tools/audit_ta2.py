#!/usr/bin/env python3
"""Conservative, non-destructive lexical crosswalk: Blender names -> TA2.csv.

Never assigns a TA2 ID from fuzzy similarity; ambiguous and missing matches stay unresolved.
"""
import csv
import json
import re
import unicodedata
from collections import defaultdict, Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/"sources"/"z-anatomy-upstream"/"TA2.csv"
FIXTURE=ROOT/"reports"/"pelvis-fixture-candidate.json"
OUT=ROOT/"reports"/"pelvis-ta2-crosswalk.json"

def normalize(s):
    s=unicodedata.normalize("NFKD",str(s))
    s="".join(c for c in s if not unicodedata.combining(c))
    s=s.casefold().strip().replace("’","'").replace("–","-")
    s=re.sub(r"[()'\"]","",s)
    s=re.sub(r"\s+"," ",s)
    return s

def main():
    with SOURCE.open(encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader((x.strip()[1:-1] if x.strip().startswith('"') and x.strip().endswith('"') else x for x in f if x.strip()),delimiter=";"))
    indexes=defaultdict(list)
    for row in rows:
        for key in ["English","Latin"]:
            value=row.get(key,"")
            if value:
                entry=(row.get("TA2ID",""),row.get("English",""),row.get("Latin",""),key)
                if entry not in indexes[normalize(value)]:
                    indexes[normalize(value)].append(entry)
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    result=[]
    for obj in fixture["objects"]:
        name=obj["source_object"]
        stem=re.sub(r"\.(l|r)$","",name)
        laterality={"l":"left","r":"right"}.get(name[-1:] if name.endswith((".l",".r")) else "",None)
        cands=indexes.get(normalize(stem),[])
        # Multiple entries with same TA2ID via English+Latin count only once.
        ids=sorted({c[0] for c in cands if c[0]})
        status="unique_exact" if len(ids)==1 else ("ambiguous_exact" if ids else "unmatched")
        ta2id=ids[0] if len(ids)==1 else None
        result.append({
           "source_object":name,"stem":stem,"laterality_suffix":laterality,
           "status":status,"ta2_id":ta2id,"candidates":[{"id":c[0],"English":c[1],"Latin":c[2],"matched_field":c[3]} for c in cands],
           "anatomy_id_proposal": ("ta2:"+ta2id+(":"+laterality if laterality else "")) if ta2id else None,
           "review_required":True,
           "comment":"TA2 is terminology, not proof of mesh identity or orientation; clinician review required."
        })
    counts=dict(Counter(v["status"] for v in result))
    OUT.write_text(json.dumps({
       "source":"Z-Anatomy TA2.csv", "total_ta2_rows":len(rows),
       "candidate_count":len(result),"status_counts":counts,
       "algorithm":"exact English or Latin normalized only; no fuzzy automatic matches",
       "notes":["A TA2 code identifies a term, not the correctness of the mesh.", "Side suffix .l/.r requires separate validation of patient-oriented coordinates.", "Unmatched and ambiguous terms remain intentionally unresolved."],
       "objects":result
    },indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("ROWS",len(rows),"MATCHES",counts)
    for o in result: print(o["status"],o["source_object"],"->",o["ta2_id"],o["laterality_suffix"])

if __name__=="__main__":main()
