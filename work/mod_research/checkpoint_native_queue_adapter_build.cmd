@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_native_queue_adapter_production.obj checkpoint_native_queue_adapter_core.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /c /Fo:checkpoint_native_queue_adapter_fixture_core.obj checkpoint_native_queue_adapter_core.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_native_queue_adapter_pending.obj checkpoint_bound_input_pending_adapter.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /Fe:checkpoint_native_queue_adapter_fixture.exe /Fo:checkpoint_native_queue_adapter_fixture.obj checkpoint_native_queue_adapter_fixture.cpp checkpoint_native_queue_adapter_fixture_core.obj checkpoint_native_queue_adapter_pending.obj /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
