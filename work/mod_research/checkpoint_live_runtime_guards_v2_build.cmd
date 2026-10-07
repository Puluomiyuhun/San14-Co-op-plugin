@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_live_runtime_guards_v2_production.obj checkpoint_live_runtime_guards_v2.cpp
if not "%errorlevel%"=="0" exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_LIVE_RUNTIME_GUARDS_V2_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /Fe:checkpoint_live_runtime_guards_v2_fixture.exe checkpoint_live_runtime_guards_v2_fixture.cpp checkpoint_live_runtime_guards_v2.cpp checkpoint_native_queue_adapter_core.cpp checkpoint_bound_input_pending_adapter.cpp
set result=%errorlevel%
popd
exit /b %result%
