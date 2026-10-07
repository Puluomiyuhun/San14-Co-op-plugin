"""Start a bounded observation-only logger; never advances or loads the game."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time
from lockstep_baseline import sample, BattleObserver
from test_submit_probe import wait_json

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument("name")
parser.add_argument("--seconds",type=int,default=600)
args=parser.parse_args()
if not args.name.replace("-","").isalnum() or not 2<=args.seconds<=900:
    raise SystemExit("Invalid name or duration")
fixtures=json.loads((ROOT/"lockstep-observer-fixtures.json").read_text())
if len(fixtures)!=3 or any(r["result"]!="PASS" for r in fixtures):
    raise RuntimeError("Observer infrastructure tests not passed")
run=ROOT/"lockstep-traces"/args.name
run.mkdir(exist_ok=False)
reader=BattleObserver()
try:
    before=sample(reader)
    expected=json.loads((ROOT/"lockstep-traces"/"after-load-a.json").read_text(encoding="utf-8"))
    if before["focused"]["critical_state"]!=expected["focused"]["critical_state"]:
        raise RuntimeError("Expected unchanged checkpoint34 planning state")
    if before["focused"]["state_stack"]!=["CRootState","CMotorGameState","CGameState","CStrategyState","CUserStrategyState"]:
        raise RuntimeError("Expected plain planning map")
    image=(ROOT/"game-runtime-image.bin").read_bytes()
    for rva in (0x3F9219,0x16AC60,0x2A9DA4,0x3F9B00,0x3AA390,0x3AA3A0,0x3AA3E0):
        if reader.memory.read(reader.memory.base+rva,32)!=image[rva:rva+32]:
            raise RuntimeError(f"Code fingerprint mismatch at {rva:x}")
    log=run/"trace.jsonl"
    arguments=[str(ROOT/"observe_lockstep.exe"),str(reader.pid),hex(reader.memory.base),"0x3f9219",str(args.seconds),str(log)]
    (run/"before.json").write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding="utf-8")
    metadata={"created":datetime.now().isoformat(), "pid":reader.pid, "base":hex(reader.memory.base),
              "exe_sha256":reader.sha256, "observer_sha256":hashlib.sha256((ROOT/"observe_lockstep.exe").read_bytes()).hexdigest(),
              "duration_seconds":args.seconds, "trace":str(log),
              "method":"hardware execution breakpoints; no game code/data writes, no DLL injection, no new game calls",
              "limitations":"Debugger pauses affect wall-clock timing; sampled state is not the complete logical world."}
    out=open(run/"stdout.log","wb");err=open(run/"stderr.log","wb")
    try:
        process=subprocess.Popen(arguments,stdout=out,stderr=err,creationflags=subprocess.CREATE_NO_WINDOW)
    finally:
        out.close();err.close()
    metadata["observer_pid"]=process.pid
    (run/"metadata.json").write_text(json.dumps(metadata,indent=2),encoding="utf-8")
    wait_json(log,"armed")
    print(json.dumps({"armed":True,"observer_pid":process.pid,"run":str(run),"duration_seconds":args.seconds}))
finally:
    reader.close()
