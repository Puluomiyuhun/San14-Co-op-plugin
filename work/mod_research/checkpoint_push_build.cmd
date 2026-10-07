@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo work\mod_research\checkpoint_push_native_bridge.obj work\mod_research\checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:work\mod_research\checkpoint_push_bridge_core.obj work\mod_research\checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /Fe:work\mod_research\checkpoint_push_pilot.dll /Fo:work\mod_research\checkpoint_push_pilot.obj work\mod_research\checkpoint_push_pilot.cpp work\mod_research\checkpoint_push_native_bridge.obj work\mod_research\checkpoint_push_bridge_core.obj /link /incremental:no /IMPLIB:work\mod_research\checkpoint_push_pilot.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /D CHECKPOINT_PUSH_FIXTURE /Fe:work\mod_research\checkpoint_push_fixture.dll /Fo:work\mod_research\checkpoint_push_fixture_dll.obj work\mod_research\checkpoint_push_pilot.cpp work\mod_research\checkpoint_push_native_bridge.obj work\mod_research\checkpoint_push_bridge_core.obj /link /incremental:no /IMPLIB:work\mod_research\checkpoint_push_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /Fe:work\mod_research\checkpoint_push_fixture.exe /Fo:work\mod_research\checkpoint_push_fixture.obj work\mod_research\checkpoint_push_fixture.cpp /link /incremental:no
