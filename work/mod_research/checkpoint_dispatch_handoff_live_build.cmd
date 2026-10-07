@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /WX checkpoint_dispatch_handoff_live.cpp /Fe:checkpoint_dispatch_handoff_live.exe /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /WX /DCHECKPOINT_DISPATCH_HANDOFF_OBSERVER_FIXTURE checkpoint_dispatch_handoff_live.cpp /Fe:checkpoint_dispatch_handoff_live_fixture.exe /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /WX checkpoint_dispatch_handoff_live_native_fixture\submit_probe_fixture.cpp /Fe:checkpoint_dispatch_handoff_live_native_fixture\submit_probe_fixture.exe /link /INCREMENTAL:NO
