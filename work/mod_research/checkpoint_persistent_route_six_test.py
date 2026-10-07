"""Real six-entry MASM/native bridge plus immutable routing leases, own process."""
import datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CASES=('all-six-normal','all-six-exceptions','nested-cross-six-cutover','nested-worker-read-owner','active-cutover','late-root')
SOURCES=('checkpoint_persistent_route_core.h','checkpoint_persistent_route_core.cpp','checkpoint_persistent_route_worker_adapter.h','checkpoint_persistent_route_worker_adapter.cpp','checkpoint_persistent_route_six_adapter.h','checkpoint_persistent_route_six_adapter.cpp','checkpoint_persistent_route_six_fixture.cpp','checkpoint_persistent_route_six_build.cmd','checkpoint_persistent_route_six_test.py','checkpoint_persistent_bridge.h','checkpoint_persistent_bridge.cpp','checkpoint_persistent_bridge.asm','checkpoint_load_worker_bridge.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'checkpoint_persistent_route_six_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    before={n:sha(ROOT/n) for n in SOURCES}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_persistent_route_six_build.cmd')],cwd=ROOT,capture_output=True,timeout=90)
    (out/'build.log').write_bytes(build.stdout+build.stderr);cases=[]
    if build.returncode==0:
        for name in CASES:
            run=subprocess.run([str(ROOT/'checkpoint_persistent_route_six_fixture.exe'),name],cwd=ROOT,capture_output=True,timeout=20)
            try:e=json.loads(run.stdout)
            except ValueError:e={}
            cases.append(dict(case=name,passed=run.returncode==0 and e.get('passed') is True,returncode=run.returncode,evidence=e,stderr=run.stderr.decode('utf-8','replace')))
    after={n:sha(ROOT/n) for n in SOURCES};passed=build.returncode==0 and len(cases)==len(CASES) and all(c['passed'] for c in cases) and before==after
    result=dict(schema='san14.persistent-route-six.offline.v1',passed=passed,cases=cases,source_sha256=after,sources_unchanged=before==after,game_access=False,steam_access=False,native_scheduler_fence=False,production_admission=False,production_code_tested_without_fixture_macros=True,frozen_session_integrated=False,fixture_exe_sha256=sha(ROOT/'checkpoint_persistent_route_six_fixture.exe') if build.returncode==0 else None)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(passed=passed,result=str(out/'result.json'))));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
