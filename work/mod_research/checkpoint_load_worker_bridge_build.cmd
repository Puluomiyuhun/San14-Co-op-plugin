@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_load_worker_bridge.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_load_worker_bridge_fixture_asm.obj checkpoint_load_worker_bridge_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_load_worker_bridge_core.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_load_worker_bridge_fixture.exe /Fo:checkpoint_load_worker_bridge_fixture.obj checkpoint_load_worker_bridge_fixture.cpp checkpoint_load_worker_bridge.obj checkpoint_load_worker_bridge_core.obj checkpoint_load_worker_bridge_fixture_asm.obj /link /incremental:no
exit /b %errorlevel%
