@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_push_bridge_fixture_bridge.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_push_bridge_fixture_probe.obj checkpoint_push_bridge_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /O2 /EHa /Zi /Fd:checkpoint_push_bridge_fixture_compiler.pdb /Fo:checkpoint_push_bridge_fixture_core.obj /c checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /O2 /EHa /Zi /Fd:checkpoint_push_bridge_fixture_compiler.pdb /Fo:checkpoint_push_bridge_fixture_test.obj /c checkpoint_push_bridge_fixture.cpp
if errorlevel 1 exit /b 1
link /nologo /debug /incremental:no /out:checkpoint_push_bridge_fixture.exe /pdb:checkpoint_push_bridge_fixture.pdb checkpoint_push_bridge_fixture_bridge.obj checkpoint_push_bridge_fixture_probe.obj checkpoint_push_bridge_fixture_core.obj checkpoint_push_bridge_fixture_test.obj kernel32.lib
exit /b %errorlevel%
