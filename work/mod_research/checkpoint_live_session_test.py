"""Own fixture only. Builds production DLL but never loads it into a game."""
from pathlib import Path
import datetime,hashlib,json,secrets,subprocess
from checkpoint_live_session_contract import Config,Report,config_bytes,decode_report,PREFIX
P=Path(__file__).resolve().parent
CASES=('success','exception','wrong-thread','bad-birth','pending','bad-path','foreign-slot')
SOURCES=('checkpoint_live_session_core.h','checkpoint_live_session_core.cpp','checkpoint_live_session_profile.h',
 'checkpoint_live_session_fixture.cpp','checkpoint_live_session_fixture.asm','checkpoint_live_session_build.cmd',
 'checkpoint_live_session_contract.py','checkpoint_live_session_test.py','checkpoint_push_bridge.h','checkpoint_push_bridge.cpp',
 'checkpoint_push_bridge.asm','checkpoint_load_hook_set.h','checkpoint_load_hook_set.cpp','checkpoint_load_input_boundary_fixture_layout.h',
 'checkpoint_load_input_boundary.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={n:sha(P/n) for n in SOURCES}
run=P/'checkpoint_live_session_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
build=subprocess.run(['cmd','/c',str(P/'checkpoint_live_session_build.cmd')],cwd=P,capture_output=True)
(run/'build.log').write_bytes(build.stdout+build.stderr)
if build.returncode:raise SystemExit(build.returncode)
rows=[]
for case in CASES:
    journal=P/('checkpoint_live_session_fixture_'+secrets.token_hex(8)+'.jsonl')
    proc=subprocess.run([str(P/'checkpoint_live_session_fixture.exe'),case,str(journal)],cwd=P,capture_output=True,timeout=10)
    (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
    lines=[line for line in proc.stdout.decode(errors='replace').splitlines() if line.startswith('{')]
    row=json.loads(lines[-1]) if lines else dict(case=case,passed=False)
    row['exit_code']=proc.returncode;row['passed']=bool(row['passed'] and not proc.returncode)
    row['journal']=str(journal) if journal.exists() else None
    if journal.exists():
        events=[json.loads(line) for line in journal.read_text().splitlines()];row['events']=events
        assert all(not x['queue_calls'] and not x['request_cas'] and x['load_requested'] is False for x in events)
    rows.append(row)
packed=config_bytes(pid=1,birth=2,base=3,attempt=4,attachment_hex='ab'*32,root=5,world=6,states=[7,8,9,10,11],toolbar=12,panel=13,journal=PREFIX+'abi.jsonl')
assert len(packed)==1216 and Config.from_buffer_copy(packed).states[4]==11
r=Report();r.size=312;r.version=1;assert decode_report(bytes(r))['completeSessionInstalled']==0
after={n:sha(P/n) for n in SOURCES};unchanged=before==after
result=dict(schema='san14.live-session-observer-owned-fixtures.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',
 cases=rows,source_sha256=after,source_unchanged_during_build_and_tests=unchanged,dll_sha256=sha(P/'checkpoint_live_session_core.dll'),
 fixture_sha256=sha(P/'checkpoint_live_session_fixture.exe'),config_bytes=1216,report_bytes=312,game_access=False,
 real_game_install_attempted=False,observe_only=True,complete_session_installed=False,midpatch_installed=False)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n');(P/'checkpoint_live_session_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(run/'result.json')}))
raise SystemExit(0 if result['result']=='PASS' else 1)
