"""Build read-only early-report guard and test only self-owned process layouts."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import re
import subprocess

P=Path(__file__).resolve().parent
CASES=('quiet','flag','queue','shape','phase','world','user','source','writable','noaccess','binding','retired','drift','retire-during')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    out=P/'a_save_early_guard_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    todo=['a_save_early_guard.cpp','a_save_early_guard_fixture.cpp','a_save_early_guard_test.py'];sources={}
    while todo:
        n=todo.pop()
        if n in sources:continue
        p=P/n;sources[n]=sha(p);todo+=re.findall(r'^\s*#include\s+"([^"]+)"',p.read_text(encoding='utf-8-sig'),re.M)
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags='/nologo /std:c++17 /EHa /W4 /WX /wd4324 /O2 /MT'
    commands=[f'cl {flags} /c "{P/"a_save_early_guard.cpp"}" /Fo:guard.obj',
              'lib /nologo /OUT:a_save_early_guard.lib guard.obj',
              f'cl {flags} /DA_SAVE_EARLY_FIXTURE /c "{P/"a_save_early_guard.cpp"}" /Fo:fixture_guard.obj',
              f'cl {flags} /DA_SAVE_EARLY_FIXTURE /c "{P/"a_save_early_guard_fixture.cpp"}" /Fo:fixture.obj',
              'link /nologo /OUT:fixture.exe fixture_guard.obj fixture.obj']
    script=out/'build.cmd';script.write_text('@echo off\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    built=subprocess.run(['cmd','/c',str(script)],cwd=out,capture_output=True,text=True,errors='replace');(out/'build.log').write_text(built.stdout+built.stderr,encoding='utf-8')
    if built.returncode:print(built.stdout+built.stderr);raise SystemExit(built.returncode)
    rows=[]
    for case in CASES:
        proc=subprocess.run([str(out/'fixture.exe'),case],cwd=out,capture_output=True,text=True,timeout=10)
        try:row=json.loads(proc.stdout)
        except ValueError:row=dict(case=case,result='FAIL',stdout=proc.stdout)
        row.update(exit=proc.returncode,stderr=proc.stderr);rows.append(row);print(case,row['result'],proc.stderr,flush=True)
    unchanged=all(sha(P/n)==h for n,h in sources.items())
    report=dict(schema='san14.a-save-early-report-guard.v1',result='PASS' if unchanged and all(r['result']=='PASS' and not r['exit'] for r in rows) else 'FAIL',cases=rows,
        sources=sources,sources_unchanged=unchanged,production_sha256=sha(out/'a_save_early_guard.lib'),fixture_sha256=sha(out/'fixture.exe'),
        game_access=False,steam_access=False,gameplay_writes=False,save_owner_composed=False,production_permit=False,
        scope='Native read-only guard executes on self-owned layouts with fixed source anchors. It rejects pending User+660/report queue, stale identity, source/protection drift and read failure. No game functions, source patches, save/native owner or full input exclusion are exercised by this fixture.')
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result=report['result'],path=str(out/'result.json'))));raise SystemExit(report['result']!='PASS')
if __name__=='__main__':main()
