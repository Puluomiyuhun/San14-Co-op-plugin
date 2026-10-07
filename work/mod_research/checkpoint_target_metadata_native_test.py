"""Standalone own-process leaf adapter fixtures; never accesses the game."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
CASES='''success wrong_bytes ctor_exception parser_exception parser_header_mismatch parser_error parser_cursor parser_owner_write parser_heap_string parser_source_write parser_false parse_dtor_exception bad_prepared_header allocation_null allocation_exception allocation_guard_drift copy_exception copy_reentrant copy_mismatch copy_wrong_return published release_dtor_exception release_free_exception release_free_return_unknown production_bind_reject_fixture_exe'''.split()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    frozen=ROOT/'checkpoint_target_metadata_fixtures/20261006-220746-446551/result.json';e=json.loads(frozen.read_text());old={name:sha(ROOT/name) for name in e['source_sha256']};assert old==e['source_sha256']
    out=ROOT/'checkpoint_target_metadata_native_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    build=subprocess.run(['cmd','/c',str(ROOT/'checkpoint_target_metadata_native_build.cmd')],capture_output=True,text=True,encoding='utf8',errors='replace');(out/'build.txt').write_text(build.stdout+build.stderr,encoding='utf8');assert build.returncode==0,build.stdout+build.stderr
    archive=ROOT/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14';assert sha(archive)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    cases=[]
    for name in CASES:
        p=subprocess.run([str(ROOT/'checkpoint_target_metadata_native_fixture.exe'),name,str(archive)],capture_output=True,text=True,timeout=15)
        (out/(name+'.stdout.txt')).write_text(p.stdout);(out/(name+'.stderr.txt')).write_text(p.stderr)
        row={'case':name,'passed':p.returncode==0,'exit_code':p.returncode}
        if not p.returncode:row.update(json.loads(p.stdout))
        else:row['failure']=p.stderr
        cases.append(row)
    assert old=={name:sha(ROOT/name) for name in old}
    files=['checkpoint_target_metadata_native.h','checkpoint_target_metadata_native.cpp','checkpoint_target_metadata_native_anchors.inc','checkpoint_target_metadata_native_profile.json','checkpoint_target_metadata_native_shadow.py','checkpoint_target_metadata_native_fixture.cpp','checkpoint_target_metadata_native_build.cmd','checkpoint_target_metadata_native_test.py']
    report={'schema':'san14.checkpoint-target-metadata-native-fixtures.v1','result':'PASS' if all(c['passed'] for c in cases) else 'FAIL','cases':cases,'source_sha256':{name:sha(ROOT/name) for name in files},'production_object_sha256':sha(ROOT/'checkpoint_target_metadata_native.obj'),'fixture_binary_sha256':sha(ROOT/'checkpoint_target_metadata_native_fixture.exe'),'fixture_object_sha256':sha(ROOT/'checkpoint_target_metadata_native_fixture_core.obj'),'frozen_core_result_sha256':sha(frozen),'frozen_core_sources_unchanged':old,'game_access':False,'production_adapter_live_verified':False,'scope':'Leaf adapter logic with own-process native-function stubs. Captured native machine-code proof is separate. No mode/fence/cache registration/load calls.'}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':report['result'],'cases':len(cases),'failed':[x for x in cases if not x['passed']],'path':str(out/'result.json')}));return report['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
