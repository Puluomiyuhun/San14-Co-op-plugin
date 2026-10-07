"""Actual own-process concurrent threads; no Steam/game/window access."""
from datetime import datetime
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
CASES=('success','concurrent-success','recursive-valid','recursive-open',
       'stop-active-and-waiter','stop-before-open','native-body-unlocked',
       'generation-invalidated','explicit-invalidate','repeated-open','owner-fault')
SOURCES=tuple('checkpoint_serialized_storage_gate'+s for s in ('.h','.cpp','_fixture.cpp','_build.cmd','_test.py'))+(
    'checkpoint_live_storage_binding.h','checkpoint_live_storage_binding.cpp',
    'checkpoint_live_storage_binding_fixture.cpp','checkpoint_live_storage_binding_fixture.asm',
    'native_storage_read_core.h','native_storage_read_core.cpp')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    folder=P/'checkpoint_serialized_storage_gate_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');folder.mkdir(parents=True)
    source={n:sha(P/n) for n in SOURCES}
    build=subprocess.run(['cmd','/c',str(P/'checkpoint_serialized_storage_gate_build.cmd')],cwd=P,capture_output=True)
    (folder/'build.log').write_bytes(build.stdout+build.stderr)
    if build.returncode:print(build.stdout.decode(errors='replace'));raise SystemExit(build.returncode)
    exe=P/'checkpoint_serialized_storage_gate_fixture.exe';binary=sha(exe);rows=[]
    for case in CASES:
        run=subprocess.run([str(exe),case,binary],cwd=P,capture_output=True,timeout=15)
        (folder/(case+'.stdout.txt')).write_bytes(run.stdout);(folder/(case+'.stderr.txt')).write_bytes(run.stderr)
        lines=[x for x in run.stdout.decode(errors='replace').splitlines() if x.startswith('{')]
        row=json.loads(lines[-1]) if lines else {'case':case,'passed':False};row['exit_code']=run.returncode
        row['passed']=bool(row['passed'] and not run.returncode);rows.append(row)
    stable=source=={n:sha(P/n) for n in SOURCES}
    report={'schema':'san14.serialized-storage-gate-fixtures.v1','result':'PASS' if stable and all(x['passed'] for x in rows) else 'FAIL',
        'cases':rows,'source_sha256':source,'source_unchanged_during_build_and_run':stable,
        'fixture_binary_sha256':binary,'production_object_sha256':sha(P/'checkpoint_serialized_storage_gate_production.obj'),
        'binding_production_object_sha256':sha(P/'checkpoint_serialized_storage_gate_binding_production.obj'),
        'game_access':False,'steam_access':False,'fixture_uses_actual_os_threads':True,'frozen_binding_context_reused':True,
        'gate_fixture_code_override':False,'native_body_is_owned_stub':True,'input_hold':False,'world_ready':False}
    (folder/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'result':report['result'],'cases':len(rows),'failed':[x['case'] for x in rows if not x['passed']],'path':str(folder/'result.json')}))
    raise SystemExit(0 if report['result']=='PASS' else 1)
if __name__=='__main__':main()
