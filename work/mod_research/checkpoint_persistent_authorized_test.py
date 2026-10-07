"""Actual native routing/ABI tests; provider/session/queue are explicit doubles."""
import datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
CASES=('default-closed','unowned-forward','two-generations','nested-cutover','native-seh','native-cpp','nested-seh','exception-then-next-generation','stop-during-original','active-cutover','late-root','concurrent','invalid-admission-refuses','wrong-generation-route','recursive-forward-target','finally-observer-seh','duplicate-wrapper-native','submit-before','mismatched-binding-generation')
SOURCES=('checkpoint_persistent_authorized_controller.h','checkpoint_persistent_authorized_controller.cpp','checkpoint_persistent_authorized_bridge.asm','checkpoint_persistent_authorized_fixture.cpp','checkpoint_persistent_authorized_fixture.asm','checkpoint_persistent_authorized_build.cmd','checkpoint_persistent_authorized_test.py','checkpoint_persistent_route_core.h','checkpoint_persistent_route_core.cpp','checkpoint_persistent_route_worker_adapter.h','checkpoint_persistent_route_worker_adapter.cpp','checkpoint_persistent_route_six_adapter.h','checkpoint_persistent_route_six_adapter.cpp','checkpoint_persistent_logical_adapter.h','checkpoint_persistent_logical_adapter.cpp','checkpoint_persistent_bridge.h','checkpoint_persistent_bridge.cpp','checkpoint_persistent_bridge.asm','checkpoint_bound_input_pending_adapter.h','checkpoint_bound_input_pending_adapter.cpp','checkpoint_native_input_pending_adapter.h','checkpoint_native_input_pending_adapter.cpp','checkpoint_native_input_core.h','checkpoint_native_input_core.cpp','checkpoint_native_input_hwbp.h','checkpoint_load_worker_bridge.h','checkpoint_push_bridge.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'checkpoint_persistent_authorized_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    before={n:sha(ROOT/n) for n in SOURCES}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_persistent_authorized_build.cmd')],cwd=ROOT,capture_output=True,timeout=90)
    (out/'build.log').write_bytes(build.stdout+build.stderr);cases=[]
    if build.returncode==0:
        jobs=[('checkpoint_persistent_authorized_fixture.exe',n) for n in CASES]+[('checkpoint_persistent_authorized_production_fixture.exe','production-activation-closed')]
        for exe,name in jobs:
            run=subprocess.run([str(ROOT/exe),name],cwd=ROOT,capture_output=True,timeout=20)
            try:e=json.loads(run.stdout)
            except ValueError:e={}
            cases.append(dict(case=name,passed=run.returncode==0 and e.get('passed') is True,returncode=run.returncode,evidence=e,stderr=run.stderr.decode('utf-8','replace')))
    after={n:sha(ROOT/n) for n in SOURCES};passed=build.returncode==0 and len(cases)==len(CASES)+1 and all(c['passed'] for c in cases) and before==after
    result=dict(schema='san14.persistent-authorized-routing.offline.v1',passed=passed,cases=cases,source_sha256=after,sources_unchanged=before==after,game_access=False,steam_access=False,native_scheduler_fence=False,production_admission=False,hardware_provider='explicit refusing double; no hardware success claimed',session='callback-port double; no complete Session receipt claimed',queue='refusing/counting double; no successful native queue tested',native_route='actual six-slot physical bridge, immutable lease router, logical adapter, new TLS controller wrapper and MASM original',production_obj_sha256=sha(ROOT/'checkpoint_persistent_authorized_production.obj') if build.returncode==0 else None)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(passed=passed,result=str(out/'result.json'))));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
