"""Only self-owned executables; no process discovery or game/Steam access."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
P=Path(__file__).resolve().parent
CASES=('success','player-request','late-ui','wrong-binding','native-fault','observer-fault','missing-site','stop-before','stop-active','repeat-site','wrong-bytes','occupied-dr','foreign-exception','restore-conflict','null-toolbar','wrong-user','arm-deadline','foreign-finish')
SOURCES=('checkpoint_native_input_hwbp.h','checkpoint_native_input_hwbp.cpp','checkpoint_native_input_hwbp_fixture.cpp','checkpoint_native_input_hwbp_fixture.asm','checkpoint_native_input_hwbp_build.cmd','checkpoint_native_input_hwbp_test.py','checkpoint_native_input_prefetch_archived.inc','checkpoint_native_input_prefetch_bridge.h','checkpoint_native_input_pending_adapter.h','checkpoint_native_input_pending_adapter.cpp','checkpoint_native_input_core.h','checkpoint_load_dispatch_bridge.h','checkpoint_load_dispatch_bridge.cpp','checkpoint_load_dispatch_bridge.asm','checkpoint_push_bridge.h','checkpoint_load_input_boundary_fixture_layout.h','checkpoint_load_input_boundary.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    source={n:sha(P/n) for n in SOURCES}
    run=P/'checkpoint_native_input_hwbp_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    b=subprocess.run(['cmd','/c',str(P/'checkpoint_native_input_hwbp_build.cmd')],cwd=P,capture_output=True)
    (run/'build.log').write_bytes(b.stdout+b.stderr)
    if b.returncode:raise SystemExit(b.returncode)
    rows=[]
    for case in CASES:
        r=subprocess.run([str(P/'checkpoint_native_input_hwbp_fixture.exe'),case],capture_output=True,timeout=12)
        (run/(case+'.stdout.txt')).write_bytes(r.stdout);(run/(case+'.stderr.txt')).write_bytes(r.stderr)
        lines=[x for x in r.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
        row=json.loads(lines[-1]) if lines else {'case':case,'passed':False}
        row['exit_code']=r.returncode;row['passed']=bool(row['passed'] and not r.returncode);rows.append(row)
    unchanged=source=={n:sha(P/n) for n in SOURCES}
    result=dict(schema='san14.native-input-hardware-prefetch-fixtures.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',cases=rows,source_sha256=source,source_unchanged_during_build_and_run=unchanged,production_object_sha256=sha(P/'checkpoint_native_input_hwbp_core.obj'),fixture_core_sha256=sha(P/'checkpoint_native_input_hwbp_fixture_core.obj'),fixture_exe_sha256=sha(P/'checkpoint_native_input_hwbp_fixture.exe'),capture_kind='hardware_execute_context',native_block_hex='488b86780400004183ceff4885c07411448bb088000000c78088000000ffffffff',native_rva='0x3F9DAF',native_block_bytes=33,original_code_writes=0,real_windows_debug_registers_and_vectored_exception=True,game_access=False,steam_access=False,queue_authorized=False,full_input_hold=False,scope='Owned OS-loaded PE executes unchanged archived 33-byte block; real execution breakpoint, VEH CONTEXT, independent helper Suspend/Get/Set/Resume, actual dispatch/pending pair. Remaining native User/world and caller layout are synthetic. Production object omits fixture-only delay. Deadline test waits for cleanup join beyond refusal deadline and never grants admission after timeout.')
    for path in (run/'result.json',P/'checkpoint_native_input_hwbp_result.json'):path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(run/'result.json'),'failed':[x['case'] for x in rows if not x['passed']]}))
    raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
