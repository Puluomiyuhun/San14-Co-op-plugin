"""Own fixture only. Builds production DLL but never loads it into a game."""
from pathlib import Path
import datetime,hashlib,json,secrets,subprocess
from checkpoint_live_prefetch_contract import Config,Report,config_bytes,decode_report,PREFIX
P=Path(__file__).resolve().parent
CASES=('success','exception','wrong-thread','bad-birth','pending','bad-path','foreign-slot','two-threads','thread-overflow','active-stop','install-stop-race','stop-before-install','idle-current-zero','idle-current-other','callback-wrong-current','bad-mode')
SOURCES=('checkpoint_live_prefetch_core.h','checkpoint_live_prefetch_core.cpp','checkpoint_live_prefetch_profile.h',
 'checkpoint_live_prefetch_fixture.cpp','checkpoint_live_prefetch_fixture.asm','checkpoint_live_prefetch_build.cmd',
 'checkpoint_live_prefetch_contract.py','checkpoint_live_prefetch_test.py','checkpoint_live_prefetch_runtime.inc','checkpoint_live_prefetch_bridge.asm','checkpoint_native_input_hwbp.h','checkpoint_native_input_hwbp.cpp','checkpoint_bound_input_pending_adapter.h','checkpoint_bound_input_pending_adapter.cpp','checkpoint_native_input_pending_adapter.h','checkpoint_native_input_core.h','checkpoint_native_input_prefetch_archived.inc','checkpoint_push_bridge.h','checkpoint_push_bridge.cpp',
 'checkpoint_push_bridge.asm','checkpoint_load_hook_set.h','checkpoint_load_hook_set.cpp','checkpoint_load_input_boundary_fixture_layout.h',
 'checkpoint_load_input_boundary.h')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
before={n:sha(P/n) for n in SOURCES}
run=P/'checkpoint_live_prefetch_runs'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
build=subprocess.run(['cmd','/c',str(P/'checkpoint_live_prefetch_build.cmd')],cwd=P,capture_output=True)
(run/'build.log').write_bytes(build.stdout+build.stderr)
if build.returncode:raise SystemExit(build.returncode)
rows=[]
for case in CASES:
    journal=P/('checkpoint_live_prefetch_fixture_'+secrets.token_hex(8)+'.jsonl')
    proc=subprocess.run([str(P/'checkpoint_live_prefetch_fixture.exe'),case,str(journal)],cwd=P,capture_output=True,timeout=30)
    (run/(case+'.stdout.txt')).write_bytes(proc.stdout);(run/(case+'.stderr.txt')).write_bytes(proc.stderr)
    lines=[line for line in proc.stdout.decode(errors='replace').splitlines() if line.startswith('{')]
    objects=[json.loads(line) for line in lines]
    row=next((x for x in objects if 'case' in x),dict(case=case,passed=False))
    abi=next((x for x in objects if x.get('abi')),None)
    if abi:
        assert abi['config_bytes']==1272 and abi['report_bytes']==7400 and abi['pending_bytes']==72 and abi['hardware_bytes']==696
        assert abi['pending_before_offset']==Report.pendingBefore.offset and abi['pending_after_offset']==Report.pendingAfter.offset and abi['hardware_offset']==Report.hardware.offset and abi['admission_started_offset']==Report.admissionStarted.offset
    row['abi_verified']=bool(abi)
    row['exit_code']=proc.returncode;row['passed']=bool(row['passed'] and not proc.returncode)
    row['journal']=str(journal) if journal.exists() else None
    if journal.exists():
        events=[json.loads(line) for line in journal.read_text().splitlines()];row['events']=events
        assert all(not x['queue_calls'] and not x['request_cas'] and x['load_requested'] is False for x in events)
    rows.append(row)
packed=config_bytes(pid=1,birth=2,base=3,attempt=4,attachment_hex='ab'*32,root=5,world=6,states=[7,8,9,10,11],toolbar=12,panel=13,journal=PREFIX+'abi.jsonl',cache=14,stack=15,stack_capacity=16,queue=0,queue_capacity=0,expected_mode=0,helper_deadline_ms=1000,generation=1)
assert len(packed)==1272 and Config.from_buffer_copy(packed).states[4]==11
r=Report();r.size=7400;r.version=3;assert decode_report(bytes(r))['completeSessionInstalled']==0
raw_report=Path(rows[0]['journal']+'.report.bin').read_bytes();decoded=decode_report(raw_report)
assert decoded['hardware']['capture_kind']==1 and decoded['hardware']['restored']==1 and decoded['hardware']['pending']['pending_admission_candidate']
assert decoded['admission_started']==decoded['admission_finished']==decoded['admission_closed']==1 and not decoded['admission_errors']
assert decoded['hardware']['binding']==dict(attempt_hex='73'*16,attachment_hex='73'*16,owner_generation=1)
after={n:sha(P/n) for n in SOURCES};unchanged=before==after
result=dict(schema='san14.live-prefetch-observer-owned-fixtures.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',
 cases=rows,source_sha256=after,source_unchanged_during_build_and_tests=unchanged,dll_sha256=sha(P/'checkpoint_live_prefetch_core.dll'),
 fixture_sha256=sha(P/'checkpoint_live_prefetch_fixture.exe'),config_bytes=1272,report_bytes=7400,game_access=False,
 real_game_install_attempted=False,observe_only=True,complete_session_installed=False,midpatch_installed=False)
(run/'result.json').write_text(json.dumps(result,indent=2)+'\n');(P/'checkpoint_live_prefetch_result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'result':result['result'],'cases':len(rows),'path':str(run/'result.json')}))
raise SystemExit(0 if result['result']=='PASS' else 1)
