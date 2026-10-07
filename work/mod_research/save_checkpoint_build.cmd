@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /Fe:work\mod_research\save_checkpoint_pilot.dll /Fo:work\mod_research\save_checkpoint_pilot.obj work\mod_research\save_checkpoint_pilot.cpp /link /IMPLIB:work\mod_research\save_checkpoint_pilot.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /D SAVE_CHECKPOINT_FIXTURE /Fe:work\mod_research\save_checkpoint_fixture.dll /Fo:work\mod_research\save_checkpoint_fixture_dll.obj work\mod_research\save_checkpoint_pilot.cpp /link /IMPLIB:work\mod_research\save_checkpoint_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\save_checkpoint_fixture.exe /Fo:work\mod_research\save_checkpoint_fixture.obj work\mod_research\save_checkpoint_fixture.cpp
