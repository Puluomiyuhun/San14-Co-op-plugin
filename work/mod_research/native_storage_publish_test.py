"""Own-process fixed-CC03 publication tests, never touches game or Steam."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
CASES='''success wrong_basename wrong_hash wrong_identity owner_rejected context_rejected missing_owner_binding native_present native_present_second native_present_after_intent native_exists_exception absence_negative_size absence_positive_size existing_intent intent_missing_directory cancel_after_intent write_false write_exception write_clobber_source cancel_during_write readback_short readback_corrupt readback_size readback_missing readback_exception reentrant_publish concurrent_publish'''.split()
def main():
    frozen={name:sha(ROOT/name) for name in ('native_storage_read_core.h','native_storage_read_core.cpp','native_storage_read_core.obj')}
    out=ROOT/'native_storage_publish_fixtures'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    build=subprocess.run(['cmd','/c',str(ROOT/'native_storage_publish_build.cmd')],capture_output=True,text=True,encoding='utf8',errors='replace');(out/'build.txt').write_text(build.stdout+build.stderr,encoding='utf8');assert build.returncode==0,build.stdout+build.stderr
    source=ROOT/'checkpoint_push_archives/20261006-204306-581930/mppush01.s14';assert sha(source)=='88ddc39fd2fd76c0c4b130bd9a2dad12effa9cfd20a1cb333981d541e8761b8c'
    cases=[]
    for case in CASES:
        p=subprocess.run([str(ROOT/'native_storage_publish_fixture.exe'),case,str(source),str(out/case)],capture_output=True,text=True,timeout=20)
        (out/(case+'.stdout.txt')).write_text(p.stdout);(out/(case+'.stderr.txt')).write_text(p.stderr)
        row={'case':case,'passed':p.returncode==0,'exit_code':p.returncode}
        if p.returncode:row['error']=p.stderr
        else:row.update(json.loads(p.stdout))
        cases.append(row)
    assert frozen=={name:sha(ROOT/name) for name in frozen}
    sources=['native_storage_publish_core.h','native_storage_publish_core.cpp','native_storage_publish_fixture.cpp','native_storage_publish_build.cmd','native_storage_publish_test.py','native_storage_read_core.h','native_storage_read_core.cpp']
    report={'schema':'san14.native-storage-publish-fixtures.v1','result':'PASS' if all(r['passed'] for r in cases) else 'FAIL','cases':cases,'source_sha256':{name:sha(ROOT/name) for name in sources},'production_object_sha256':sha(ROOT/'native_storage_publish_core.obj'),'fixture_binary_sha256':sha(ROOT/'native_storage_publish_fixture.exe'),'read_core_unchanged':frozen,'game_access':False,'steam_api_called':False,'scope':'Actual durable filesystem intents and own fixture files, fake native methods. Does not prove native Steam publication or provide a game-thread fence.'}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'result':report['result'],'cases':len(cases),'failed':[r for r in cases if not r['passed']],'path':str(out/'result.json')}));return report['result']!='PASS'
if __name__=='__main__':raise SystemExit(main())
