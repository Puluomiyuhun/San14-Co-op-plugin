"""Owned debugger publication transactions; never discovers or opens a game."""
from pathlib import Path
from datetime import datetime
import hashlib,json,subprocess,sys
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=P.parents[2]/'mod_research'/'a_save_runtime_publish_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    sources={p.name:sha(p) for p in [P/'a_save_runtime_publish.cpp',P/'a_save_runtime_publish_fixture.cpp',P/'a_save_runtime_publish_test.py',P/'a_save_runtime_exports.h']}
    vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
    flags=f'cl /nologo /std:c++17 /W4 /WX /EHsc /MT /I"{P}" '
    cmd=run/'build.cmd';cmd.write_text('@echo off\ncall "'+vc+'" >nul\n'+''.join(x+'\nif errorlevel 1 exit /b 1\n' for x in [flags+f'"{P / "a_save_runtime_publish.cpp"}" /Fo:publisher.obj /Fe:publisher.exe',flags+f'/DA_SAVE_RUNTIME_PUBLISH_FIXTURE "{P / "a_save_runtime_publish.cpp"}" /Fo:publisher_fixture.obj /Fe:publisher_fixture.exe',flags+f'/DOWN_STAGE /LD "{P / "a_save_runtime_publish_fixture.cpp"}" /Fo:stage.obj /Fe:stage.dll',flags+f'"{P / "a_save_runtime_publish_fixture.cpp"}" /Fo:target.obj /Fe:target.exe']))
    result={'result':'FAIL','game_access':False,'sources':sources,'cases':[]};children=[]
    try:
        b=subprocess.run(['cmd','/c',str(cmd)],cwd=run,capture_output=True,text=True,errors='replace',timeout=60);(run/'build.log').write_text(b.stdout+b.stderr,encoding='utf-8');assert b.returncode==0,'compile'
        for case in ['install-restore','owner-only','rollback','active','host-lease']:
            folder=run/case;folder.mkdir();child=subprocess.Popen([str(run/'target.exe'),str(run/'stage.dll')],cwd=folder,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);children.append(child)
            line=child.stdout.readline();(folder/'target-start.txt').write_text(line);identity=json.loads(line)
            def command(s):child.stdin.write(s+'\n');child.stdin.flush();assert child.stdout.readline().strip()=='OK'
            def publish(op,expected,production=False):
                args=[str(run/('publisher.exe' if production else 'publisher_fixture.exe')),op]+[str(identity[k]) for k in ['pid','birth','base','module']]+[str(run/'stage.dll'),sha(run/'stage.dll'),str(folder/'plans.bin'),str(folder/'snapshot.bin')]
                # A retained debugger is never killed. Poll and preserve its identity on timeout.
                process=subprocess.Popen(args,cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);children.append(process)
                try:out,err=process.communicate(timeout=15)
                except subprocess.TimeoutExpired:raise RuntimeError(f'publisher retained or timed out pid={process.pid}; do not kill')
                (folder/(op+('-production' if production else '')+'.log')).write_text(out+err);v=json.loads(out);assert v['status']==expected,v;assert not v['uncertain'];return v
            publish('inspect','REJECTED_PREFLIGHT',True)
            records=[]
            if case=='install-restore':records.append(publish('install','INSTALLED'));command('check-installed');command('stop');records.append(publish('restore','RESTORED'));command('check-restored')
            elif case=='owner-only':command('stop');records.append(publish('restore','RESTORED'));command('check-restored')
            elif case=='rollback':records.append(publish('rollback-1','CLEAN_ROLLBACK'));command('check-original');assert records[-1]['written_mask']==records[-1]['rolled_mask']==3
            elif case=='active':command('active');records.append(publish('install','REJECTED_HELD_NO_WRITES'));command('inactive');command('check-original')
            else:command('lease');records.append(publish('restore','REJECTED_PREFLIGHT'));command('check-original')
            command_exit='exit\n';child.stdin.write(command_exit);child.stdin.flush();assert child.wait(timeout=10)==0
            result['cases'].append({'case':case,'records':records,'owned_child_exited':True})
        assert all(sha(P/n)==h for n,h in sources.items()),'source drift';result['result']='PASS'
    except Exception as e:result['error']=repr(e)
    result['surviving_owned_pids']=[p.pid for p in children if p.poll() is None]
    result['binaries']={p.name:sha(p) for p in run.iterdir() if p.suffix in ('.exe','.dll','.obj')};result['generated']={'build.cmd':sha(cmd)}
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'result':result['result'],'path':str(run/'result.json')}));return 0 if result['result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
