"""Offline native owned-process routing tests. No game/Steam/remote access."""
import datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CASES=('baseline','default-closed','nested-inherits','active-cutover','late-root','race','native-seh','native-cpp','before-seh','after-seh','finally-seh','nested-overflow','foreign-double-release','compare-and-stale-parent')
SOURCES=('checkpoint_persistent_route_core.h','checkpoint_persistent_route_core.cpp','checkpoint_persistent_route_worker_adapter.h','checkpoint_persistent_route_worker_adapter.cpp','checkpoint_persistent_route_fixture.cpp','checkpoint_persistent_route_build.cmd','checkpoint_persistent_route_test.py','checkpoint_load_worker_bridge.h','checkpoint_load_worker_bridge.cpp','checkpoint_load_worker_bridge.asm')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'checkpoint_persistent_route_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    before={n:sha(ROOT/n) for n in SOURCES}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_persistent_route_build.cmd')],cwd=ROOT,capture_output=True,timeout=90)
    (out/'build.log').write_bytes(build.stdout+build.stderr)
    cases=[]
    if build.returncode==0:
        for name in CASES:
            run=subprocess.run([str(ROOT/'checkpoint_persistent_route_fixture.exe'),name],cwd=ROOT,capture_output=True,timeout=20)
            try:e=json.loads(run.stdout)
            except ValueError:e={}
            cases.append(dict(case=name,passed=run.returncode==0 and e.get('passed') is True,returncode=run.returncode,evidence=e,stderr=run.stderr.decode('utf-8','replace')))
    after={n:sha(ROOT/n) for n in SOURCES}
    passed=build.returncode==0 and len(cases)==len(CASES) and all(c['passed'] for c in cases) and before==after
    result=dict(schema='san14.persistent-route.offline.v1',passed=passed,cases=cases,source_sha256=after,sources_unchanged=before==after,game_access=False,steam_access=False,native_scheduler_fence=False,production_admission=False,production_code_tested_without_fixture_macros=True,dispatch_bridge_integrated=False)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(dict(passed=passed,result=str(out/'result.json'))));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
