"""Compare observed native stage traces; never claims complete-world determinism."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def rows(path):
    data=path.read_text(encoding="utf-8").splitlines()
    result=[]
    for i,line in enumerate(data):
        try: result.append(json.loads(line))
        except json.JSONDecodeError:
            if i!=len(data)-1: raise
    return result

def normalize(row, omit_random=False):
    result={key:value for key,value in row.items() if key not in ("seq","thread")}
    if omit_random:
        result.pop("global_rng",None)
    return result

def canonical_stages(data, omit_random=False):
    result=[]
    for row in data:
        if row["event"]!="stage":continue
        clean=normalize(row,omit_random)
        if not result or result[-1]!=clean:result.append(clean)
    return result

def describe(data):
    counts=Counter(row["event"] for row in data)
    stages=[r for r in data if r["event"]=="stage"]
    return {"events":dict(counts),
            "distinct_dates":sorted({tuple(r["date"]) for r in stages}),
            "distinct_stage_indices":sorted({r["stage"] for r in stages}),
            "distinct_move_armies":len({r["army_id"] for r in data if r["event"]=="move_write"}),
            "casualty_source_target_pairs":sorted({
                (r["source_kind"],r["source_id"],r["target_kind"],r["target_id"])
                for r in data if r["event"]=="casualty_request"}),
            "consecutive_identical_stage_samples_removed":len(stages)-len(canonical_stages(data)),
            "cleanly_detached":bool(data and data[-1].get("event")=="detached" and data[-1].get("registers_restored")),
            "planning_return":next((r for r in data if r["event"]=="planning_return"),None),
            "errors":[r for r in data if r["event"] in ("error","error_cleanup","process_exit")]}

def first_difference(a,b):
    for i,(left,right) in enumerate(zip(a,b)):
        if left!=right:
            differing_fields=[k for k in sorted(left.keys()|right.keys()) if left.get(k)!=right.get(k)]
            result={"index":i,"fields":differing_fields}
            for key in ("date","stage","world_inputs","global_rng"):
                if key in left or key in right:result[key]={"a":left.get(key),"b":right.get(key)}
            for kind in ("armies","cities"):
                if kind in differing_fields:
                    left_objects=dict(left[kind]);right_objects=dict(right[kind])
                    changes=[]
                    for identity in sorted(left_objects.keys()|right_objects.keys()):
                        x=left_objects.get(identity);y=right_objects.get(identity)
                        if x==y:continue
                        row={"id":identity}
                        if x is None or y is None:row.update(a=x,b=y)
                        else:
                            xb,yb=bytes.fromhex(x),bytes.fromhex(y)
                            row["changed_bytes"]=[{"object_offset":hex(n+0x10),"a":u,"b":v}
                                                  for n,(u,v) in enumerate(zip(xb,yb)) if u!=v]
                        changes.append(row)
                    result[kind]=changes
            if any(k in differing_fields for k in ("source_id","target_id","amount","army_id","to")):
                result["a"]=left;result["b"]=right
            return result
    if len(a)!=len(b):return {"index":min(len(a),len(b)),"reason":"different_length","a_length":len(a),"b_length":len(b)}
    return None

def baseline_difference(a,b):
    record_changes=[];runtime_pointer_changes=[]
    for key in sorted(a["records"].keys()|b["records"].keys()):
        x=a["records"].get(key);y=b["records"].get(key)
        if x==y:continue
        if x is None or y is None:
            record_changes.append({"object":key,"reason":"membership"});continue
        diff=[n+0x10 for n,(u,v) in enumerate(zip(bytes.fromhex(x),bytes.fromhex(y))) if u!=v]
        if key.startswith("army:") and all(0x148<=offset<0x150 for offset in diff):
            runtime_pointer_changes.append(key)
        else:record_changes.append({"object":key,"offsets":[hex(n) for n in diff]})
    return {"sampled_record_changes_excluding_known_runtime_pointer":record_changes,
            "rebuilt_army_runtime_pointers":runtime_pointer_changes,
            "random_inputs_equal":a["random_inputs"]==b["random_inputs"],
            "random_inputs_a":a["random_inputs"],"random_inputs_b":b["random_inputs"],
            "focused_state_equal":a["focused"]==b["focused"],
            "person_task_sample_equal":a["eligibility"]==b["eligibility"],
            "scope":"Partial logical records; only known army+148 runtime pointer excluded. Pools/UI/full world not included."}

def compare(run_a,run_b):
    a=rows(run_a/"trace.jsonl");b=rows(run_b/"trace.jsonl")
    sa,sb=describe(a),describe(b)
    before=baseline_difference(load(run_a/"before.json"),load(run_b/"before.json"))
    stage_diff=first_difference(canonical_stages(a),canonical_stages(b))
    logical_diff=first_difference(canonical_stages(a,True),canonical_stages(b,True))
    battle_a=[normalize(r) for r in a if r["event"] in ("move_write","casualty_request")]
    battle_b=[normalize(r) for r in b if r["event"] in ("move_write","casualty_request")]
    events_diff=first_difference(battle_a,battle_b)
    complete=all(s["cleanly_detached"] and s["planning_return"] and not s["errors"] for s in (sa,sb))
    baseline_ok=(not before["sampled_record_changes_excluding_known_runtime_pointer"] and
                 before["random_inputs_equal"] and before["focused_state_equal"] and before["person_task_sample_equal"])
    return {"scope":"Single-process repeated native simulation; limited observed state and selected event entries",
            "run_a":str(run_a),"run_b":str(run_b),"a":sa,"b":sb,"baseline":before,
            "completed_both":bool(complete),"sampled_baselines_equal":baseline_ok,
            "first_stage_difference_with_rng":stage_diff,
            "first_stage_difference_without_global_rng":logical_diff,
            "first_move_or_casualty_request_difference":events_diff,
            "observed_repeatability_pass":bool(complete and baseline_ok and not stage_diff and not events_diff),
            "full_world_equality_proven":False,"two_process_determinism_proven":False,
            "notes":["A checksum or sampled equality can falsify divergence but cannot prove all hidden state is covered.",
                     "Debugger pauses change wall-clock scheduling; later runs without this instrumentation are required.",
                     "Casualty observations are requests at function entry, not a claim that all requested damage was applied.",
                     "Do not silently ignore RNG differences even when visible army records still agree."]}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("runs",nargs="+")
    args=parser.parse_args()
    runs=[ROOT/"lockstep-traces"/name for name in args.runs]
    if len(runs)==1:
        print(json.dumps(describe(rows(runs[0]/"trace.jsonl")),ensure_ascii=True,indent=2))
    elif len(runs)==2:
        report=compare(*runs)
        destination=ROOT/"lockstep-traces"/f"compare-{args.runs[0]}-{args.runs[1]}.json"
        destination.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(report,ensure_ascii=True,indent=2))
    else:raise SystemExit("Supply one or two runs")
