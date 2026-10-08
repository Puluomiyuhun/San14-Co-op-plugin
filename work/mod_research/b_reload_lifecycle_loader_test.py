"""New-process PE-entry loader exercise. Starts only freshly built owned files."""
from pathlib import Path
from datetime import datetime
import hashlib,json,os,subprocess
P=Path(__file__).resolve().parent
SOURCES=('b_reload_lifecycle_loader.cpp','b_reload_lifecycle_loader.h','b_reload_lifecycle_loader_fixture.cpp','b_reload_lifecycle_loader_test.py')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 before={f:sha(P/f) for f in SOURCES}
 run=P/'b_reload_lifecycle_loader_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
 vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
 flags='/DB_RELOAD_LIFECYCLE_LOADER_DIAGNOSTIC /nologo /std:c++17 /W4 /WX /O2 /MD /EHsc /DUNICODE /D_UNICODE /I"'+str(P)+'"'
 production_flags=flags.replace("/DB_RELOAD_LIFECYCLE_LOADER_DIAGNOSTIC ","")
 commands=[f'cl {production_flags} /c "{P/"b_reload_lifecycle_loader.cpp"}" /Fo:production_loader.obj',f'cl {flags} "{P/"b_reload_lifecycle_loader.cpp"}" /Fe:loader.exe',f'cl {flags} "{P/"b_reload_lifecycle_loader_fixture.cpp"}" /Fe:"owned host.exe"',f'cl {flags} /DB_RELOAD_LIFECYCLE_BOOTSTRAP_DLL /LD "{P/"b_reload_lifecycle_loader_fixture.cpp"}" /Fe:"owned bootstrap.dll"']
 build=run/'build.cmd';build.write_text('@echo off\nsetlocal\ncall "'+vc+'" >nul\nif errorlevel 1 exit /b 1\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
 proc=subprocess.run(['cmd','/c',str(build)],cwd=run,capture_output=True,text=True,encoding='mbcs',errors='replace');(run/'build.log').write_text(proc.stdout+proc.stderr,encoding='utf-8')
 if proc.returncode:raise SystemExit('Build failed '+str(run/'build.log'))
 rows=[]
 for case,reject in [('owned-pre-entry-bootstrap',False),('owned-bootstrap-refused',True)]:
  env=os.environ.copy();env.pop('B_RELOAD_LOADER_FIXTURE_REJECT',None)
  if reject:env['B_RELOAD_LOADER_FIXTURE_REJECT']='1'
  proc=subprocess.run([str(run/'loader.exe'),str(run/'owned host.exe'),str(run/'owned bootstrap.dll'),'--wait-exit'],cwd=run,env=env,capture_output=True,text=True,timeout=40)
  (run/(case+'.stdout.txt')).write_text(proc.stdout);(run/(case+'.stderr.txt')).write_text(proc.stderr)
  records=[json.loads(l) for l in proc.stdout.splitlines() if l.startswith('{')];last=records[-1] if records else {}
  passed=(proc.returncode==1 and last.get('passed') is False and last.get('stage')=='bootstrap') if reject else (proc.returncode==0 and last.get('passed') and last.get('pe_entry_stopped') and last.get('entry_byte_restored') and last.get('bootstrap_before_entry') and last.get('target_exit')==0)
  rows.append(dict(case=case,passed=bool(passed),exit=proc.returncode,records=records));print(case,'PASS' if passed else 'FAIL',flush=True)
 unchanged=all(sha(P/f)==h for f,h in before.items());result=dict(schema='san14.b-reload-startup-loader-owned.v1',result='PASS' if unchanged and all(x['passed'] for x in rows) else 'FAIL',cases=rows,sources=before,inputs_unchanged=unchanged,binaries={f:sha(run/f) for f in ('loader.exe','owned host.exe','owned bootstrap.dll','production_loader.obj')},created_owned_process_only=True,actual_pe_entry_stop=True,actual_remote_bootstrap=True,existing_process_attach=False,game_access=False,lifecycle_source_installed=False,game_launch_verified=False,room_ready=False)
 path=run/'result.json';path.write_text(json.dumps(result,indent=2)+'\n');print(path);raise SystemExit(0 if result['result']=='PASS' else 1)
if __name__=='__main__':main()
