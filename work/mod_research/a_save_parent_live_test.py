"""Compile production observer, test own-memory samples; never open game."""
from pathlib import Path
from datetime import datetime
import json,os,subprocess
import a_save_parent_live as live
old=live.old;P=live.P
def main():
    private=Path(os.environ.get('SAN14_PRIVATE_FIXTURE_ROOT',str(live.PRIVATE))).resolve()
    image=private/'game-runtime-image.bin'
    assert old.sha(image)=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
    raw=image.read_bytes();run=live.PRIVATE/'a_save_parent_live_test_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    sources={n:old.sha(P/n) for n in live.SOURCES};result=dict(schema='san14.a-save-parent-live.tests.v1',result='FAIL',sources=sources,cases=[],game_access=False,debugger_core_unchanged=True)
    try:
        precedent=P/'a_save_observation_status_test_runs/20261008-202814-533972/result.json'
        prior=json.loads(precedent.read_text());assert prior['result']=='PASS' and len(prior['cases'])==39
        assert all(old.sha(P/n)==h for n,h in prior['sources'].items()),'Prior debugger lifecycle source drift'
        result['debugger_lifecycle_precedent']=dict(path=str(precedent),sha256=old.sha(precedent),cases=39,sources=prior['sources'])
        anchors={str(a):raw[a:a+16].hex() for a in (0x13DC09,0x13DC0E,0x50B598,0x50B632)}
        (run/'parent_anchors.h').write_text('struct SaveObservationAnchor {uint64_t rva;unsigned char bytes[16];};\nstatic const SaveObservationAnchor saveObservationAnchors[]={\n'+''.join('{'+a+',{'+','.join('0x'+h[i:i+2] for i in range(0,32,2))+'}},\n' for a,h in anchors.items())+'};\n')
        core=(P/'a_save_observation_status.cpp').read_text().replace('"a_save_observation_payload.inc"','"a_save_parent_live_payload.inc"').replace('"a_save_observation_binding.inc"','"parent_binding.inc"')
        (run/'parent_generated.cpp').write_text(core)
        binding=(P/'a_save_observation_binding.inc').read_text().replace('"a_save_observation_anchors.h"','"parent_anchors.h"').replace('rva!=0x2F7C28','rva!=0x13DC09')
        (run/'parent_binding.inc').write_text(binding)
        flags='/nologo /std:c++17 /EHsc /W4 /WX /I"'+str(P)+'" /I"'+str(run)+'"'
        commands=[f'cl {flags} parent_generated.cpp /Fe:observer.exe /Fo:observer.obj /link /INCREMENTAL:NO',f'cl {flags} "{P/"a_save_parent_live_semantic.cpp"}" /Fe:semantic.exe /Fo:semantic.obj /link /INCREMENTAL:NO']
        (run/'build.cmd').write_text('@echo off\ncall "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul\n'+'\n'.join(x+'\nif errorlevel 1 exit /b 1' for x in commands)+'\n')
        r=subprocess.run(['cmd','/c',str(run/'build.cmd')],cwd=run,capture_output=True);(run/'build.log').write_bytes(r.stdout+r.stderr);assert r.returncode==0,'Compile failed'
        for mode in ('normal','wrong-rsp','wrong-thread','wrong-user'):
            r=subprocess.run([str(run/'semantic.exe'),str(run/(mode+'.jsonl')),mode],capture_output=True,timeout=10);(run/(mode+'.stdout')).write_bytes(r.stdout+r.stderr);v=json.loads(r.stdout);assert r.returncode==(0 if mode=='normal' else 1) and v['complete']==(mode=='normal');result['cases'].append(dict(case=mode,**v,passed=True))
        result.update(anchors=anchors,production_sha256=old.sha(run/'observer.exe'),generated={n:old.sha(run/n) for n in ('parent_generated.cpp','parent_binding.inc','parent_anchors.h','build.cmd')},binaries={n:old.sha(run/n) for n in ('observer.exe','observer.obj','semantic.exe','semantic.obj')},private_image_sha256=old.sha(image))
        assert all(old.sha(P/n)==h for n,h in sources.items());result.update(sources_unchanged=True,result='PASS')
    except Exception as e:result['error']=repr(e)
    finally:old.write(run/'result.json',result);print(json.dumps(dict(result=result['result'],path=str(run/'result.json'))))
    return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
