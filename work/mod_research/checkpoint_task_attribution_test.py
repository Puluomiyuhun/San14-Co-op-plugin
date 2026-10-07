"""Only builds workspace C++ and runs its dedicated owned-process fixtures."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
CASES=('late-old-root','all-state-kinds','unknown-root','pointer-reuse','active-cutover','resume-same-ticket','embedded-and-read','embedded-join-other-thread','read-without-worker','wrong-frame','wrong-serial','native-exception','before-exception','cross-thread','duplicate-creation','bounded-records')
SOURCES=('checkpoint_task_attribution_core.h','checkpoint_task_attribution_core.cpp','checkpoint_task_attribution_adapter.cpp','checkpoint_task_attribution_fixture.cpp','checkpoint_task_attribution_build.cmd','checkpoint_task_attribution_test.py','checkpoint_persistent_route_core.h','checkpoint_persistent_route_core.cpp','checkpoint_persistent_route_worker_adapter.h','checkpoint_persistent_route_worker_adapter.cpp','checkpoint_persistent_route_six_adapter.h','checkpoint_persistent_route_six_adapter.cpp','checkpoint_persistent_bridge.h','checkpoint_persistent_bridge.cpp','checkpoint_persistent_bridge.asm','checkpoint_load_worker_bridge.h')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 folder=ROOT/'checkpoint_task_attribution_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
 before={n:sha(ROOT/n) for n in SOURCES}
 build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_task_attribution_build.cmd')],cwd=ROOT,capture_output=True)
 (folder/'build.stdout').write_bytes(build.stdout);(folder/'build.stderr').write_bytes(build.stderr)
 rows=[]
 if build.returncode==0:
  for case in CASES:
   cp=subprocess.run([str(ROOT/'checkpoint_task_attribution_fixture.exe'),case],cwd=ROOT,capture_output=True,timeout=20)
   (folder/(case+'.stdout')).write_bytes(cp.stdout);(folder/(case+'.stderr')).write_bytes(cp.stderr)
   try:data=json.loads(cp.stdout)
   except Exception:data={}
   rows.append(dict(case=case,exit=cp.returncode,data=data,passed=cp.returncode==0 and data.get('passed') is True))
 after={n:sha(ROOT/n) for n in SOURCES}
 result=dict(schema='san14.task-attribution-fixtures.v1',result='PASS' if build.returncode==0 and len(rows)==len(CASES) and all(x['passed'] for x in rows) and before==after else 'FAIL',game_access=False,build_exit=build.returncode,source_unchanged=before==after,source_sha256=after,cases=rows,limitations=['Actual frozen six-slot assembly/finally bridge and frozen router publication execute in owned processes.','Native scheduler observation receipts and native original bodies are explicit fixture doubles.','No native provider/installer, production generation publication or global fence.'])
 if build.returncode==0:result['binary_sha256']=sha(ROOT/'checkpoint_task_attribution_fixture.exe')
 (folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(dict(folder=str(folder),result=result['result'],build_exit=build.returncode,failed=[x['case'] for x in rows if not x['passed']]),indent=2))
 return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
