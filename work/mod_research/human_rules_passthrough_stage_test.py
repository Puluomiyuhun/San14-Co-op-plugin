from datetime import datetime
import hashlib,json,subprocess
from pathlib import Path
P=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    run=P/'human_rules_passthrough_stage_runs'/datetime.now().strftime('%Y%m%d-%H%M%S-%f');run.mkdir(parents=True)
    files=['human_rules_passthrough_stage.h','human_rules_passthrough_stage.cpp','human_rules_passthrough_stage_fixture.cpp','human_rules_passthrough_stage_test.py','human_rules_passthrough_image.py','human_rules_hook_transport.h','human_rules_hook_transport.cpp','human_rules_hook_unwind.h','human_ai_runtime_profile.h','human_economy_runtime_profile.h','human_economy_runtime_fixture_memory.h','human_economy_runtime_fixture_unwind.h','human_ai_runtime_fixture_memory.h']
    fingerprints={f:sha(P/f) for f in files}
    from human_rules_passthrough_image import build
    build(P/'game-runtime-image.bin',run)
    cmd=run/'build.cmd';flags='/nologo /W4 /WX /EHa /std:c++17 /O2 /MT /I"'+str(P.parents[1]/'outputs/san14-link')+'" /I"'+str(run)+'"'
    lines=['@echo off','call "C:\\Program Files\\Microsoft Visual Studio\\2022\\Community\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul','if errorlevel 1 exit /b 1']
    for name,extra,sources in [('stage.dll','/LD',['human_rules_passthrough_stage.cpp','human_rules_hook_transport.cpp']),('stage_fixture.dll','/LD /DHUMAN_RULES_STAGE_FIXTURE',['human_rules_passthrough_stage.cpp','human_rules_hook_transport.cpp']),('stage_fixture.exe','',['human_rules_passthrough_stage_fixture.cpp'])]:
        lines.extend([f'cl {flags} {extra} '+ ' '.join('"'+str(P/f)+'"' for f in sources)+f' /Fe:"{run/name}"','if errorlevel 1 exit /b 1'])
    cmd.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    r=subprocess.run(['cmd','/d','/c',str(cmd)],cwd=run,capture_output=True);(run/'build.stdout.txt').write_bytes(r.stdout);(run/'build.stderr.txt').write_bytes(r.stderr)
    if r.returncode:raise RuntimeError(r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
    cases=[]
    for case in ['forward','seh','bad-profile','production-refuses-private']:
        binary=run/('stage.dll' if case.startswith('production') else 'stage_fixture.dll')
        r=subprocess.run([str(run/'stage_fixture.exe'),case,str(binary),str(P/'game-runtime-image.bin')],cwd=run,capture_output=True,timeout=20)
        (run/f'{case}.stdout.txt').write_bytes(r.stdout);(run/f'{case}.stderr.txt').write_bytes(r.stderr)
        if r.returncode:raise RuntimeError(f'{case}: {r.returncode} '+r.stdout.decode(errors='replace')+r.stderr.decode(errors='replace'))
        cases.append(json.loads(r.stdout.decode().splitlines()[-1]))
    assert fingerprints=={f:sha(P/f) for f in files}
    result=dict(result='PASS',cases=cases,source_sha256=fingerprints,production_dll_sha256=sha(run/'stage.dll'),fixture_dll_sha256=sha(run/'stage_fixture.dll'),game_access=False,policy_enabled=False,production_publisher_connected=False)
    (run/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(result='PASS',path=str(run/'result.json'))))
if __name__=='__main__':main()
