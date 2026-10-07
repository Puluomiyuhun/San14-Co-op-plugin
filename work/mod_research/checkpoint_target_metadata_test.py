"""Own-process only: complete real archived bytes, synthetic native adapters."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
CASES='''empty slot109 existing_unindexed existing_indexed mode1 pending secondary slot_range slot_occupied local_occupied native_occupied native_unknown target_missing table_foreign group0 group2 cross_owned table_alias group_drift list_corrupt list_over_bound parser_wrong_buffer parser_reopens parser_bad_header parser_mutates_bytes parser_cache_drift parser_failure copy_bad_links copy_foreign copy_failure copy_exception cleanup_failure copy_guard_drift copy_native_occupied postcommit_guard_drift invalidate_clear invalidate_payload invalidate_attachment invalidate_generation invalidate_mode invalidate_native_presence existing_intent restart_intent bad_native_bytes'''.split()
CASES += ['head_is_node','real_shape_50_unindexed','all_groups','invalidate_observed_epoch','invalidate_adapter']
CASES += [f'commit_fault_{i}' for i in range(5)]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=ROOT/'checkpoint_target_metadata_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_target_metadata_build.cmd')],capture_output=True,text=True,encoding='utf8',errors='replace')
    (out/'build.txt').write_text(build.stdout+build.stderr,encoding='utf8');assert build.returncode==0,build.stdout+build.stderr
    source=ROOT/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14';assert digest(source)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    cases=[]
    for name in CASES:
        directory=out/name;directory.mkdir();(directory/'mppush01.s14').write_bytes(source.read_bytes())
        p=subprocess.run([str(ROOT/'checkpoint_target_metadata_fixture.exe'),name,str(directory)],capture_output=True,text=True,timeout=15)
        (directory/'stdout.txt').write_text(p.stdout);(directory/'stderr.txt').write_text(p.stderr)
        row={'case':name,'passed':p.returncode==0,'exit_code':p.returncode}
        if not p.returncode:row.update(json.loads(p.stdout))
        else:row['failure']=p.stderr
        cases.append(row)
    files=['checkpoint_target_metadata_core.h','checkpoint_target_metadata_core.cpp','checkpoint_target_metadata_profile.inc','checkpoint_target_metadata_fixture.cpp','checkpoint_target_metadata_build.cmd','checkpoint_target_metadata_test.py','native_storage_read_core.h','native_storage_read_core.cpp']
    # The production object is also compiled, WITHOUT the injection macro. The
    # fixture object has a deliberate import of RaiseException; production has
    # no such external reference or injected-fault function symbol.
    production=(ROOT/'checkpoint_target_metadata_core.obj').read_bytes()
    fixture=(ROOT/'checkpoint_target_metadata_core_fixture.obj').read_bytes()
    assert b'fixtureCommitFault' not in production and b'__imp_RaiseException' not in production
    assert b'fixtureCommitFault' in fixture and b'__imp_RaiseException' in fixture
    result={'schema':'san14.checkpoint-target-metadata-fixtures.v1','result':'PASS' if all(c['passed'] for c in cases) else 'FAIL','cases':cases,'source_sha256':{p:digest(ROOT/p) for p in files},'fixture_binary_sha256':digest(ROOT/'checkpoint_target_metadata_fixture.exe'),'production_core_object_sha256':digest(ROOT/'checkpoint_target_metadata_core.obj'),'fixture_core_object_sha256':digest(ROOT/'checkpoint_target_metadata_core_fixture.obj'),'production_fault_injection_present':False,'fixture_only_fault_injection':'CHECKPOINT_TARGET_METADATA_FIXTURE: RaiseException after 0..4 completed stores','archive_sha256':digest(source),'game_access':False,'native_adapter_implemented':False,'load_authorized':False,'scope':'Own Windows process with real archived mppush01 bytes and real native_storage_read core; all Steam, parser, allocator, serial-boundary and manager callbacks are synthetic. No game directory writes.'}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'cases':len(cases),'report':str(out/'result.json'),'failed':[c for c in cases if not c['passed']]}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
