import pathlib,subprocess
p=pathlib.Path(__file__).resolve().parent;b=p/'checkpoint_ready_input_build';b.mkdir(exist_ok=True)
vc=r'C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat'
common='cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 '
commands=[common+'/c checkpoint_ready_input_gate.cpp /Fo:checkpoint_ready_input_build\\gate.obj',
'lib /nologo /OUT:checkpoint_ready_input.lib checkpoint_ready_input_build\\gate.obj',
common+'/DCHECKPOINT_READY_INPUT_OWNED_FIXTURE /c checkpoint_ready_input_gate.cpp /Fo:checkpoint_ready_input_build\\gate_fixture.obj',
common+'/DCHECKPOINT_PLANNING_DISPATCHER_OWNED_FIXTURE /c checkpoint_planning_dispatcher.cpp /Fo:checkpoint_ready_input_build\\dispatcher_fixture.obj',
common+'/c checkpoint_native_input_pending_adapter.cpp checkpoint_persistent_bridge.cpp /Fo:checkpoint_ready_input_build\\',
'ml64 /nologo /c /Fo checkpoint_ready_input_build\\bridge_asm.obj checkpoint_persistent_bridge.asm',
'ml64 /nologo /c /Fo checkpoint_ready_input_build\\fixture_asm.obj checkpoint_ready_input_fixture.asm']
links=' checkpoint_ready_input_build\\dispatcher_fixture.obj checkpoint_ready_input_build\\checkpoint_native_input_pending_adapter.obj checkpoint_ready_input_build\\checkpoint_persistent_bridge.obj checkpoint_ready_input_build\\bridge_asm.obj checkpoint_ready_input_build\\fixture_asm.obj checkpoint_reward_owned_replay_fixture.lib checkpoint_planning_hold.lib'
commands += [common+'/wd4505 /DCHECKPOINT_READY_INPUT_OWNED_FIXTURE checkpoint_ready_input_fixture.cpp /Fo:checkpoint_ready_input_build\\fixture.obj /Fe:checkpoint_ready_input_fixture.exe /link checkpoint_ready_input_build\\gate_fixture.obj'+links,
common+'/wd4505 checkpoint_ready_input_fixture.cpp /Fo:checkpoint_ready_input_build\\production_fixture.obj /Fe:checkpoint_ready_input_production_fixture.exe /link checkpoint_ready_input_build\\gate.obj'+links]
s=b/'build.cmd';s.write_text('@echo off\ncall "'+vc+'"\n'+'\n'.join(c+'\nif errorlevel 1 exit /b 1' for c in commands)+'\n')
r=subprocess.run(['cmd','/c',str(s)],cwd=p,text=True,encoding='utf8',errors='replace',capture_output=True);(b/'build.log').write_text(r.stdout+r.stderr,encoding='utf8');print(r.stdout+r.stderr);raise SystemExit(r.returncode)
