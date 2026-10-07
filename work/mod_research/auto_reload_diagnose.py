"""Offline diagnosis of the preserved failed live observer; never opens a process."""
from pathlib import Path
from datetime import datetime
import hashlib,json,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'python_deps'))
import capstone
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text(encoding='utf-8'))
archive=ROOT/'auto_reload_diagnostics/before-fix-20261006-163437-750178'
manifest=load(archive/'manifest.json')
live=load(ROOT/'auto_reload_live_result.json')
trace=Path(live['directory'])/'trace.jsonl'
preserved={}
for name in ('auto_reload_live_once.json','auto_reload_live_result.json','auto_reload_dry_result.json'):
    assert sha(ROOT/name)==manifest[name],f'Historical artifact changed: {name}'
    preserved[name]=manifest[name]
assert sha(trace)==manifest['live_trace.jsonl']
preserved[str(trace)]=manifest['live_trace.jsonl']
tests=load(ROOT/'auto_reload_test_results.json')
assert tests['result']=='PASS' and len(tests['cases'])==18
assert tests['cleanup']['result']=='PASS' and tests['cleanup']['cases']==6
assert tests['binary_sha256']==sha(ROOT/'observe_auto_reload.exe')
image=(ROOT/'game-runtime-image.bin').read_bytes()
assert hashlib.sha256(image).hexdigest()=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64)
anchors=[]
for rva,mnemonic,operand,meaning in (
 (0x2EE647,'call','0x2f76c0','Calls native world deserializer.'),
 (0x2EE64C,'mov','esi, eax','Observer stops here before native post-load rebuilding.'),
 (0x2EE69D,'call','0x2f3410','Successful branch invokes native post-load rebuilding later.'),
 (0x2F3B93,'mov','qword ptr [rdi + rax*8 + 0x148], rdx','Rebuilds the person-ID pointer map from deserialized person records.'),
 (0x508BC2,'mov','dword ptr [rip + 0x1b16040], ebx','Worker result publication point after its native load call returns.'),
):
    insn=next(md.disasm(image[rva:rva+16],rva))
    # RIP-relative spelling is verified below but recorded even if this image's
    # exact displacement differs from a prior hand annotation.
    assert insn.mnemonic==mnemonic,(hex(rva),insn.mnemonic,insn.op_str)
    if rva!=0x508BC2:assert insn.op_str==operand,(hex(rva),insn.op_str)
    anchors.append({'rva':hex(rva),'instruction':insn.mnemonic+' '+insn.op_str,'bytes_hex':insn.bytes.hex(),'meaning':meaning})
result={
 'schema':'san14.auto-reload-live-diagnostic.v1',
 'created':datetime.now().astimezone().isoformat(),
 'result':'OBSERVER_STAGE_CONTRACT_FIXED_AND_TESTED_OFFLINE',
 'original_live_result':live['result'],
 'original_live_binary_sha256':live['binary_sha256'],
 'original_live_trace_complete':False,
 'request_submissions_in_original_trace':sum(r['event']=='reload_request_written' for r in live['trace']),
 'new_live_attempts':0,'retry_issued':False,'old_once_journal_preserved':True,
 'original_failure':{
   'message':'ReadProcessMemory error=299',
   'last_successful_stage':'native_target_bound',
   'failed_address_recorded':False,'failed_instruction_recorded':False,
   'exact_cause_uniquely_proven':False,
   'candidate_cause':'The original observer called worldCheck at 0x2EE64C and dereferenced root+0x148 person-ID mappings before native 0x2F3410 rebuilt them. Static ordering supports this candidate, but the old log lacks failing read address/registers, so it cannot uniquely attribute error 299.',
   'independent_late_outcome_file':str(ROOT/'auto_reload_late_outcome.json'),
   'late_outcome_is_not_complete_observer_trace':True,
 },
 'static_anchors':anchors,
 'fix':{
   'deserialize_boundary':'Read only CWorld pointer/type and saved date/subday; do not dereference force or person semantic indices.',
   'worker_boundary':'Require native worker success and then verify rebuilt force/person identity plus world header and mode.',
   'final_boundary':'Retain full identity, phase-2 planning stack, pending-slot reset and immutable checkpoint hash checks.',
   'diagnostic_reads':'Future read failures include address, requested/read byte counts, observer epoch and last observation RVA.',
   'cleanup':'A failed SuspendThread on a live or unqueryable thread now makes registers_restored false. Confirmed exited threads are logged separately with registers_restored false for that thread. Restore/resume failures cannot report success.',
 },
 'validation':{
   'binary_sha256':tests['binary_sha256'],'debugger_fixture_cases':18,'cleanup_real_thread_cases':6,
   'tests_file':str(ROOT/'auto_reload_test_results.json'),'fixture_directory':tests['directory'],
   'regressions':{r['case']:r for r in tests['cases'] if r['case'] in ('deserialize_id_map_unavailable','worker_id_map_unavailable','deserialize_wrong_date')},
   'cleanup':tests['cleanup'],
   'scope':'Real Windows debugger/hardware-breakpoint lifecycle in a separate native fixture; copied native request-consumer branch but synthetic later load stages. Cleanup tests use actual owned Windows threads/handles, including permission-denied suspension. No full native SAN14 load was executed for this fix.',
 },
 'preserved_historical_artifact_sha256':preserved,
 'archive':str(archive),
 'remaining_limits':['The fixed observer has not been rerun against SAN14.','The original once journal forbids retry; it has not been deleted or reset.','The old full trace remains incomplete; root records late live outcome separately.','No full-world equality, B identity transfer, room epoch integration or repeated end-of-turn reload is proven by these fixtures.'],
}
path=ROOT/'auto_reload_live_diagnostic.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'result':result['result'],'path':str(path),'historical_artifacts_unchanged':True,'game_access':False,'debugger_tests':18,'cleanup_tests':6}))
