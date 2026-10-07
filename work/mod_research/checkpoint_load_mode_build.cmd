@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_load_mode_bridge.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_load_mode_bridge_core.obj checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /Fe:checkpoint_load_mode_pilot.dll /Fo:checkpoint_load_mode_pilot.obj checkpoint_load_mode_pilot.cpp checkpoint_load_mode_bridge.obj checkpoint_load_mode_bridge_core.obj /link /incremental:no /IMPLIB:checkpoint_load_mode_pilot.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /D CHECKPOINT_LOAD_MODE_FIXTURE /Fe:checkpoint_load_mode_fixture.dll /Fo:checkpoint_load_mode_fixture_dll.obj checkpoint_load_mode_pilot.cpp checkpoint_load_mode_bridge.obj checkpoint_load_mode_bridge_core.obj /link /incremental:no /IMPLIB:checkpoint_load_mode_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /Fe:checkpoint_load_mode_fixture.exe checkpoint_load_mode_fixture.cpp
exit /b %errorlevel%
