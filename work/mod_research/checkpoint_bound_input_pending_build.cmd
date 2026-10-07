@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
ml64 /nologo /c /Fo checkpoint_bound_input_pending_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c checkpoint_load_dispatch_bridge.cpp /Fo:checkpoint_bound_input_pending_dispatch_cpp.obj
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c checkpoint_bound_input_pending_adapter.cpp /Fo:checkpoint_bound_input_pending_adapter.obj
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT checkpoint_bound_input_pending_fixture.cpp /Fo:checkpoint_bound_input_pending_fixture.obj checkpoint_bound_input_pending_adapter.obj checkpoint_bound_input_pending_dispatch_asm.obj checkpoint_bound_input_pending_dispatch_cpp.obj /Fe:checkpoint_bound_input_pending_fixture.exe /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
