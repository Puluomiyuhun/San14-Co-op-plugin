"""Owned buffer/archived RX checks only; never accesses a game process."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
SOURCES=('checkpoint_bound_input_pending_adapter.h','checkpoint_bound_input_pending_adapter.cpp','checkpoint_bound_input_pending_fixture.cpp','checkpoint_bound_input_pending_build.cmd','checkpoint_bound_input_pending_test.py','checkpoint_native_input_pending_adapter.h','checkpoint_native_input_pending_archived.h','checkpoint_native_input_core.h','checkpoint_load_dispatch_bridge.h','checkpoint_load_dispatch_bridge.cpp','checkpoint_load_dispatch_bridge.asm','checkpoint_push_bridge.h')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 before={n:sha(P/n) for n in SOURCES};run=P/'checkpoint_bound_input_pending_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 build=subprocess.run(['cmd','/c',str(P/'checkpoint_bound_input_pending_build.cmd')],cwd=P,capture_output=True)
 (run/'build.log').write_bytes(build.stdout+build.stderr)
 if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
 proc=subprocess.run([str(P/'checkpoint_bound_input_pending_fixture.exe'),str(run/'fixture.json')],cwd=P,capture_output=True,timeout=30)
 (run/'stdout.txt').write_bytes(proc.stdout);(run/'stderr.txt').write_bytes(proc.stderr)
 result=json.loads((run/'fixture.json').read_text());after={n:sha(P/n) for n in SOURCES}
 result.update(source_sha256=after,source_unchanged_during_build_and_run=before==after,exit_code=proc.returncode,fixture_binary_sha256=sha(P/'checkpoint_bound_input_pending_fixture.exe'),adapter_object_sha256=sha(P/'checkpoint_bound_input_pending_adapter.obj'))
 result['result']='PASS' if result['failed']==0 and proc.returncode==0 and before==after else 'FAIL'
 (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');(P/'checkpoint_bound_input_pending_result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(dict(result=result['result'],passed=result['passed'],failed=result['failed'],path=str(run/'result.json'))))
 if proc.returncode:print(proc.stderr.decode(errors='replace'))
 raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
