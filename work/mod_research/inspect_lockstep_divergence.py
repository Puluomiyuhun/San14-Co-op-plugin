"""Localize the first differing native combat batch without changing any data."""
from pathlib import Path
import json
from collections import Counter
from analyze_lockstep import rows, normalize, first_difference

ROOT=Path(__file__).resolve().parent/"lockstep-traces"
report={}
for name in ("run-a","run-b"):
    data=rows(ROOT/name/"trace.jsonl")
    stages=[r for r in data if r["event"]=="stage"]
    # First observed state difference at stage sample 168 (13 in sixth 31-stage cycle).
    start,end=stages[167]["seq"],stages[168]["seq"]
    events=[normalize(r) for r in data if r.get("seq",0)>start and r.get("seq",0)<end]
    troop_changes=[]
    old,new=dict(stages[167]["armies"]),dict(stages[168]["armies"])
    for identity in sorted(old.keys()|new.keys()):
        if identity not in old or identity not in new:continue
        a,b=bytes.fromhex(old[identity]),bytes.fromhex(new[identity])
        va=int.from_bytes(a[6:8],"little");vb=int.from_bytes(b[6:8],"little")
        if va!=vb:
            troop_changes.append({"id":identity,"officer":int.from_bytes(a[2:4],"little"),"before":va,"after":vb,"lost":va-vb})
    report[name]={"stage_entry_index":167,"date":stages[167]["date"],"stage_before":stages[167]["stage"],
                  "stage_after":stages[168]["stage"],"events":events,"troop_changes":troop_changes,
                  "global_rng_before":stages[167]["global_rng"],"global_rng_after":stages[168]["global_rng"]}
    counts=Counter();current=None;index=-1
    for row in data:
        if row["event"]=="stage":current=row;index+=1
        elif row["event"]=="casualty_request":
            counts[(current["date"][2],current["stage"],index//31%12)]+=1
    report[name]["casualty_batches"]=[{"day":key[0],"stage":key[1],"cycle":key[2],"count":value}
                                     for key,value in counts.items()]
    print(name,json.dumps(report[name]["casualty_batches"]))
a=rows(ROOT/"run-a"/"trace.jsonl");b=rows(ROOT/"run-b"/"trace.jsonl")
report["first_casualty_difference"]=first_difference(
    [normalize(r) for r in a if r["event"]=="casualty_request"],
    [normalize(r) for r in b if r["event"]=="casualty_request"])
report["first_movement_difference"]=first_difference(
    [normalize(r) for r in a if r["event"]=="move_write"],
    [normalize(r) for r in b if r["event"]=="move_write"])
(ROOT/"first-divergence-detail.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in report.items() if k not in ("run-a","run-b")},ensure_ascii=True))
