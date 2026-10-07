@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
ml64 /nologo /c /Fo checkpoint_native_input_hwbp_site.obj checkpoint_native_input_hwbp_fixture.asm
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_native_input_hwbp_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_native_input_hwbp_core.obj checkpoint_native_input_hwbp.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE /c /Fo:checkpoint_native_input_hwbp_fixture_core.obj checkpoint_native_input_hwbp.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_native_input_hwbp_dispatch.obj checkpoint_load_dispatch_bridge.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_native_input_hwbp_pending.obj checkpoint_native_input_pending_adapter.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_NATIVE_INPUT_HWBP_FIXTURE /Fe:checkpoint_native_input_hwbp_fixture.exe /Fo:checkpoint_native_input_hwbp_fixture.obj checkpoint_native_input_hwbp_fixture.cpp checkpoint_native_input_hwbp_fixture_core.obj checkpoint_native_input_hwbp_dispatch.obj checkpoint_native_input_hwbp_dispatch_asm.obj checkpoint_native_input_hwbp_pending.obj checkpoint_native_input_hwbp_site.obj /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
