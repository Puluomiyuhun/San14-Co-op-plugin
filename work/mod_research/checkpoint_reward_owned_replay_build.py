import subprocess,pathlib,json
p=pathlib.Path(__file__).resolve().parent
build=p/'checkpoint_reward_owned_replay_build';build.mkdir(exist_ok=True)
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
commands=[
'cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /LD checkpoint_reward_owned_replay.cpp /Fo:checkpoint_reward_owned_replay_build\\production.obj /Fe:checkpoint_reward_owned_replay.dll /link checkpoint_planning_hold.lib /IMPLIB:checkpoint_reward_owned_replay.lib',
'cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /DCHECKPOINT_REWARD_OWNED_FIXTURE /LD checkpoint_reward_owned_replay.cpp /Fo:checkpoint_reward_owned_replay_build\\fixture_dll.obj /Fe:checkpoint_reward_owned_replay_fixture.dll /link checkpoint_planning_hold.lib /IMPLIB:checkpoint_reward_owned_replay_fixture.lib',
'cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 checkpoint_reward_owned_replay_fixture.cpp /Fo:checkpoint_reward_owned_replay_build\\fixture.obj /Fe:checkpoint_reward_owned_replay_fixture.exe /link checkpoint_reward_owned_replay_fixture.lib checkpoint_planning_hold.lib']
script=build/'compile.cmd';script.write_text('@echo off\ncall "'+vc+'"\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
r=subprocess.run(['cmd','/c',str(script)],cwd=p,text=True,encoding="utf-8",errors="replace",capture_output=True);(build/'build.log').write_text(r.stdout+r.stderr,encoding="utf-8");print(r.stdout+r.stderr);raise SystemExit(r.returncode)

