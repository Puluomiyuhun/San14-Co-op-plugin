from pathlib import Path
import json
import subprocess
import sys
import time
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'outputs'/'san14-link'))
from game_reader import GameReader

root=Path(__file__).resolve().parent
run_directory=root/'native-traces'/datetime.now().strftime('%Y%m%d-%H%M%S-%f')
run_directory.mkdir(parents=True,exist_ok=False)
log_path=run_directory/'trace.jsonl'
r=GameReader()
try:
    snapshot=r.snapshot()
    if 'CUserStrategyState' not in snapshot['state_stack']:
        raise RuntimeError('Expected the player planning phase')
    rva=0x1D1940
    reference=(root/'game-runtime-image.bin').read_bytes()[rva:rva+32]
    if r.memory.read(r.memory.base+rva,32)!=reference:
        raise RuntimeError('Runtime code fingerprint changed')
    arguments=[str(root/'observe_submit.exe'),str(r.pid),hex(r.memory.base),hex(rva),'600',str(log_path)]
    metadata={'pid':r.pid,'base':hex(r.memory.base),'rva':hex(rva),'exe_sha256':r.sha256,
              'runtime_prefix':reference.hex(),'start_snapshot':snapshot,'trace_path':str(log_path)}
    (run_directory/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    (root/'game-submit-trace-metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
finally:r.close()

process=subprocess.Popen(arguments,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
deadline=time.monotonic()+12
armed=False
while time.monotonic()<deadline:
    try:
        rows=[json.loads(line) for line in log_path.read_text().splitlines()]
        if any(row['event']=='armed' for row in rows):armed=True;break
        if any(row['event']=='error' for row in rows):break
    except (FileNotFoundError,json.JSONDecodeError):pass
    if process.poll() is not None:break
    time.sleep(.05)
print(json.dumps({'armed':armed,'probe_pid':process.pid,'trace_path':str(log_path)}),flush=True)
out,err=process.communicate(timeout=620)
print(log_path.read_text(),flush=True)
if err:print(err.decode(errors='replace'))
raise SystemExit(process.returncode)
