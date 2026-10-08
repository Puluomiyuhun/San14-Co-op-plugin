"""Owned child-client named pipes plus mailbox; no native game or TLS claim."""
from pathlib import Path
from datetime import datetime
import difflib,hashlib,json,re,subprocess
from checkpoint_fresh_save_packet import decode_packet
P=Path(__file__).resolve().parent
CASES=('normal','queued-disconnect','claimed-disconnect','queued-shutdown','claimed-shutdown')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def text(v):return v.decode('utf-8',errors='replace') if isinstance(v,bytes) else v or ''
def main():
    units=['a_save_dispatch_ipc.cpp','a_save_dispatch_mailbox.cpp','checkpoint_fresh_save_packet.cpp','native_storage_read_core.cpp','a_save_dispatch_ipc_fixture.cpp']
    todo=units+['a_save_dispatch_ipc_test.py','a_save_held_ipc.cpp','a_save_held_ipc.h','checkpoint_fresh_save_packet.py','a_save_ipc_client.py'];names=set()
    while todo:
        n=todo.pop()
        if n in names:continue
        p=P/n
        if not p.is_file():raise SystemExit('Missing '+n)
        names.add(n)
        if p.suffix in ('.h','.cpp'):todo.extend(re.findall(r'^\s*#include "([^"]+)"',p.read_text(encoding='utf-8-sig'),re.M))
    pins={n:sha(P/n) for n in sorted(names)}
    run=P/'a_save_dispatch_ipc_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    for suffix in ('.cpp','.h'):
        old=(P/('a_save_held_ipc'+suffix)).read_text(encoding='utf-8').splitlines(True)
        new=(P/('a_save_dispatch_ipc'+suffix)).read_text(encoding='utf-8').replace('a_save_dispatch_ipc','a_save_held_ipc').splitlines(True)
        (run/('server-delta'+suffix+'.diff')).write_text(''.join(difflib.unified_diff(old,new,fromfile='frozen',tofile='successor')),encoding='utf-8')
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags=f'/nologo /W4 /WX /wd4324 /O2 /MT /EHa /std:c++17 /I"{P}"'
    commands=[f'cl {flags} /c "{P/u}" /Fo:{Path(u).stem}.obj' for u in units]
    commands+=['lib /nologo /OUT:dispatch_ipc.lib a_save_dispatch_ipc.obj a_save_dispatch_mailbox.obj checkpoint_fresh_save_packet.obj native_storage_read_core.obj', 'link /nologo /OUT:fixture.exe '+' '.join(Path(u).stem+'.obj' for u in units)+' advapi32.lib bcrypt.lib']
    (run/'build.cmd').write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
    try:
        r=subprocess.run(['cmd','/c',str(run/'build.cmd')],cwd=run,capture_output=True,text=True,errors='replace',timeout=120);code=r.returncode;output=r.stdout+r.stderr
    except (subprocess.TimeoutExpired,OSError) as e:code=-1;output=text(getattr(e,'stdout',None))+text(getattr(e,'stderr',None))+repr(e)
    (run/'build.log').write_text(output,encoding='utf-8');rows=[];decoded=[]
    if not code:
        for case in CASES:
            try:
                r=subprocess.run([str(run/'fixture.exe'),case],cwd=run,capture_output=True,text=True,errors='replace',timeout=20)
                output=r.stdout+r.stderr;records=[json.loads(s) for s in r.stdout.splitlines() if s.startswith('{')]
                row=dict(case=case,passed=r.returncode==0 and len(records)==1 and records[0].get('passed') is True,exit=r.returncode,records=records)
                if row['passed'] and case=='normal':
                    for gen in (1,2):
                        a=decode_packet((run/f'normal-{gen}.packet').read_bytes())
                        assert a.request['generation']==a.request['period']==gen and a.data==bytes((gen,2,3,4))
                        assert a.request['day']==(11 if gen==1 else 21) and a.report['executor_thread']>0
                        decoded.append(dict(generation=gen,packet_sha256=sha(run/f'normal-{gen}.packet'),payload_sha256=a.sha256))
            except (subprocess.TimeoutExpired,OSError,ValueError,AssertionError) as e:
                output=text(getattr(e,'stdout',None))+text(getattr(e,'stderr',None))+repr(e);row=dict(case=case,passed=False,exit=-1,error=repr(e))
            (run/(case+'.log')).write_text(output,encoding='utf-8');rows.append(row)
    same=all(sha(P/n)==v for n,v in pins.items())
    passed=not code and same and len(rows)==len(CASES) and len(decoded)==2 and all(r['passed'] for r in rows)
    result=dict(result='PASS' if passed else 'FAIL',build_exit=code,cases=rows,decoded_packets=decoded,sources=pins,sources_unchanged=same,binaries={n:sha(run/n) for n in ('fixture.exe','dispatch_ipc.lib','a_save_dispatch_ipc.obj') if (run/n).is_file()},actual_named_pipe=passed,actual_mailbox=passed,owner_business_double=True,native_save=False,actual_controller=False,actual_root_boundary=False,tls=False,game_access=False)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(result=result['result'],cases=len(rows),path=str(run/'result.json'))));raise SystemExit(0 if passed else 1)
if __name__=='__main__':main()
