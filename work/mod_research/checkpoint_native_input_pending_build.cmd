@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
python checkpoint_native_input_pending_audit.py
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_native_input_pending_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /c checkpoint_load_dispatch_bridge.cpp /Fo:checkpoint_native_input_pending_dispatch_cpp.obj
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 checkpoint_native_input_pending_adapter.cpp checkpoint_native_input_pending_fixture.cpp checkpoint_native_input_pending_dispatch_asm.obj checkpoint_native_input_pending_dispatch_cpp.obj /Fe:checkpoint_native_input_pending_fixture.exe /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
checkpoint_native_input_pending_fixture.exe checkpoint_native_input_pending_fixture.json
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
