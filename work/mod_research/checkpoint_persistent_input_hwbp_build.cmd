@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_persistent_input_hwbp_site.obj checkpoint_native_input_hwbp_fixture.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_persistent_input_hwbp_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c checkpoint_persistent_input_hwbp.cpp /Focheckpoint_persistent_input_hwbp_production.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_PERSISTENT_INPUT_HWBP_FIXTURE /c checkpoint_persistent_input_hwbp.cpp /Focheckpoint_persistent_input_hwbp_core.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c checkpoint_load_dispatch_bridge.cpp /Focheckpoint_persistent_input_hwbp_dispatch.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c checkpoint_native_input_pending_adapter.cpp /Focheckpoint_persistent_input_hwbp_pending.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_PERSISTENT_INPUT_HWBP_FIXTURE /Fe:checkpoint_persistent_input_hwbp_fixture.exe /Fo:checkpoint_persistent_input_hwbp_fixture.obj checkpoint_persistent_input_hwbp_fixture.cpp checkpoint_persistent_input_hwbp_core.obj checkpoint_persistent_input_hwbp_dispatch.obj checkpoint_persistent_input_hwbp_dispatch_asm.obj checkpoint_persistent_input_hwbp_pending.obj checkpoint_persistent_input_hwbp_site.obj /link /INCREMENTAL:NO
exit /b %errorlevel%
