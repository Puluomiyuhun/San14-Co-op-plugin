@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
if not exist checkpoint_dynamic_runtime_guards_obj mkdir checkpoint_dynamic_runtime_guards_obj
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_dynamic_runtime_guards_production.obj checkpoint_dynamic_runtime_guards.cpp
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_dynamic_runtime_guards_bridgeasm.obj checkpoint_persistent_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_dynamic_runtime_guards_fixtureasm.obj checkpoint_dynamic_runtime_guards_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_DYNAMIC_RUNTIME_GUARDS_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /Fo:checkpoint_dynamic_runtime_guards_obj\ /Fe:checkpoint_dynamic_runtime_guards_fixture.exe checkpoint_dynamic_runtime_guards_fixture.cpp checkpoint_dynamic_runtime_guards.cpp checkpoint_native_queue_adapter_core.cpp checkpoint_bound_input_pending_adapter.cpp checkpoint_dynamic_file_profile.cpp checkpoint_persistent_bridge.cpp checkpoint_persistent_logical_adapter.cpp checkpoint_dynamic_runtime_guards_bridgeasm.obj checkpoint_dynamic_runtime_guards_fixtureasm.obj
set result=%errorlevel%
popd
exit /b %result%
