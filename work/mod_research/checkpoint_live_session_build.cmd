@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
ml64 /nologo /c /Fo checkpoint_live_session_bridge_asm.obj checkpoint_push_bridge.asm
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_live_session_fixture_asm.obj checkpoint_live_session_fixture.asm
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_live_session_bridge.obj checkpoint_push_bridge.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_live_session_hooks.obj checkpoint_load_hook_set.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /LD /Fe:checkpoint_live_session_core.dll /Fo:checkpoint_live_session_core.obj checkpoint_live_session_core.cpp checkpoint_live_session_bridge.obj checkpoint_live_session_bridge_asm.obj checkpoint_live_session_hooks.obj /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_LIVE_SESSION_FIXTURE /c /Fo:checkpoint_live_session_fixture_core.obj checkpoint_live_session_core.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_LIVE_SESSION_FIXTURE /Fe:checkpoint_live_session_fixture.exe /Fo:checkpoint_live_session_fixture.obj checkpoint_live_session_fixture.cpp checkpoint_live_session_fixture_core.obj checkpoint_live_session_fixture_asm.obj checkpoint_live_session_bridge.obj checkpoint_live_session_bridge_asm.obj checkpoint_live_session_hooks.obj /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
