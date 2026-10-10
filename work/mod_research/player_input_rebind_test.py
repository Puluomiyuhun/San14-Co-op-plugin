"""Compile real successor DLL and exercise its API in owned HWND processes only."""
from datetime import datetime
from pathlib import Path
import hashlib,json,re,subprocess,sys
P=Path(__file__).resolve().parent
PRIVATE=P.parents[2]/'mod_research'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    archive=PRIVATE/'game-runtime-image.bin'
    assert sha(archive)=='5a2ef730f2a075f23cd8880c5acb1f83c99c03810ea23c0663ae9f05b6c04268'
    run=PRIVATE/'player_input_rebind_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    inputs={str(archive):sha(archive)}
    units={'owner':'player_input_rebind_owner.cpp','exports':'player_input_rebind_exports.cpp','policy':'player_input_policy.cpp','classifier':'checkpoint_native_input_core.cpp','storage':'native_storage_read_core.cpp'}
    todo=list(units.values())+['player_input_rebind_fixture.cpp','player_input_rebind_test.py'];sources={}
    while todo:
        n=todo.pop()
        if n in sources or n=='player_input_rebind_profile.h':continue
        p=P/n;assert p.is_file(),p;sources[n]=sha(p)
        todo+=re.findall(r'^\s*#include\s+"([^"]+)"',p.read_text(encoding='utf-8-sig'),re.M)
    wnd=archive.read_bytes()[0x5122F0:0x512368]
    (run/'player_input_rebind_profile.h').write_text('#pragma once\nstatic const unsigned char BoundaryWndBytes[]={'+','.join(hex(x) for x in wnd)+'};\n')
    flags=f'/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT /I"{P}" /I"{run}"'
    commands=[f'cl {flags} /c "{P/s}" /Fo:{n}.obj' for n,s in units.items()]
    commands+=['link /nologo /DLL /OUT:player_input_rebind.dll owner.obj exports.obj policy.obj classifier.obj storage.obj user32.lib bcrypt.lib',f'cl {flags} /DPLAYER_INPUT_REBIND_FIXTURE /c "{P/units["owner"]}" /Fo:fixture_owner.obj',f'cl {flags} /c "{P/"player_input_rebind_fixture.cpp"}" /Fo:fixture.obj','link /nologo /OUT:fixture.exe fixture.obj fixture_owner.obj exports.obj policy.obj classifier.obj storage.obj user32.lib bcrypt.lib']
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    build=run/'build.cmd';build.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,errors='replace');(run/'build.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
    rows=[]
    if proc.returncode==0:
        for case in ('normal','pending','binding','unknown','wrong-thread','rebind','rebind-invalid','rebind-pending'):
            d=run/case;d.mkdir();q=subprocess.run([str(run/'fixture.exe'),case,str(d/'snapshot.bin')],cwd=run,capture_output=True,text=True,timeout=25)
            (d/'stdout.log').write_text(q.stdout);(d/'stderr.log').write_text(q.stderr)
            try: row=json.loads(q.stdout)
            except ValueError:row={'case':case,'result':'FAIL'}
            row['exit']=q.returncode;rows.append(row);print(case,row,flush=True)
    else: print(proc.stdout+proc.stderr)
    unchanged=all(sha(P/n)==v for n,v in sources.items()) and all(sha(Path(n))==v for n,v in inputs.items())
    result={'schema':'san14.player-input-lease-owned.v1','result':'PASS' if proc.returncode==0 and len(rows)==8 and all(r['result']=='PASS' and r['exit']==0 for r in rows) and unchanged else 'FAIL','cases':rows,'build_exit':proc.returncode,'sources':sources,'private':inputs,'inputs_unchanged':unchanged,'actual_owned_hwnd':True,'actual_archived_wndproc':True,'wndproc_body_business_double':True,'native_reward_executed':False,'production_game_bootstrap':False,'game_access':False,'steam_access':False,'all_input_coverage':False,'production_dll':str(run/'player_input_rebind.dll')}
    result['artifacts']={str(f.relative_to(run)):sha(f) for f in run.rglob('*') if f.is_file()};path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(path),'sha256':sha(path)}));return result['result']!='PASS'
if __name__=='__main__':sys.exit(main())
