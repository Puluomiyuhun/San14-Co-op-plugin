"""Real hardware breakpoint generations in owned process; no game/Steam access."""
import datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
NEW=('two-contexts','native-exception-two-contexts','repeat-context-initialize','concurrent-initialize','copied-context-refused','restore-conflict-blocks-next','deadline-blocks-next','failed-context-terminal')
PRIOR=('success','player-request','late-ui','null-toolbar','missing-site','wrong-user','wrong-binding','wrong-bytes','occupied-dr','stop-before','stop-active','observer-fault','repeat-site','foreign-exception','restore-conflict','arm-deadline','foreign-finish','native-fault')
SOURCES=('checkpoint_persistent_input_hwbp.h','checkpoint_persistent_input_hwbp.cpp','checkpoint_persistent_input_hwbp_fixture.cpp','checkpoint_persistent_input_hwbp_build.cmd','checkpoint_persistent_input_hwbp_test.py','checkpoint_native_input_hwbp.h','checkpoint_native_input_hwbp.cpp','checkpoint_native_input_hwbp_fixture.cpp','checkpoint_native_input_hwbp_fixture.asm','checkpoint_native_input_prefetch_archived.inc','checkpoint_native_input_prefetch_bridge.h','checkpoint_native_input_pending_adapter.h','checkpoint_native_input_pending_adapter.cpp','checkpoint_native_input_core.h','checkpoint_load_input_boundary_fixture_layout.h','checkpoint_load_dispatch_bridge.h','checkpoint_load_dispatch_bridge.cpp','checkpoint_load_dispatch_bridge.asm','checkpoint_push_bridge.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'checkpoint_persistent_input_hwbp_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    before={n:sha(ROOT/n) for n in SOURCES}
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_persistent_input_hwbp_build.cmd')],cwd=ROOT,capture_output=True,timeout=90)
    (out/'build.log').write_bytes(build.stdout+build.stderr);cases=[]
    if build.returncode==0:
        for name in NEW+PRIOR:
            run=subprocess.run([str(ROOT/'checkpoint_persistent_input_hwbp_fixture.exe'),name],cwd=ROOT,capture_output=True,timeout=20)
            (out/(name+'.txt')).write_bytes(run.stdout+run.stderr)
            try:e=json.loads([x for x in run.stdout.decode('utf-8','replace').splitlines() if x.startswith('{')][-1])
            except (ValueError,IndexError):e={}
            cases.append(dict(case=name,passed=run.returncode==0 and e.get('passed') is True,returncode=run.returncode,evidence=e))
    after={n:sha(ROOT/n) for n in SOURCES};passed=build.returncode==0 and len(cases)==len(NEW+PRIOR) and all(c['passed'] for c in cases) and before==after
    result=dict(schema='san14.persistent-hwbp.offline.v1',passed=passed,cases=cases,source_sha256=after,sources_unchanged=before==after,game_access=False,steam_access=False,native_scheduler_fence=False,production_admission=False,real_hardware_context=True,real_unchanged_archived_instruction_block=True,old_fixture_readonly_reused=True,production_obj_sha256=sha(ROOT/'checkpoint_persistent_input_hwbp_production.obj') if build.returncode==0 else None)
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(dict(passed=passed,result=str(out/'result.json'),failed=[c['case'] for c in cases if not c['passed']])));return 0 if passed else 1
if __name__=='__main__':raise SystemExit(main())
