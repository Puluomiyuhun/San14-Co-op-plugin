@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /Fe:work\mod_research\private_checkpoint_save_pilot.dll /Fo:work\mod_research\private_checkpoint_save_pilot.obj work\mod_research\private_checkpoint_save_pilot.cpp /link /IMPLIB:work\mod_research\private_checkpoint_save_pilot.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /D PRIVATE_CHECKPOINT_SAVE_FIXTURE /Fe:work\mod_research\private_checkpoint_save_fixture.dll /Fo:work\mod_research\private_checkpoint_save_fixture_dll.obj work\mod_research\private_checkpoint_save_pilot.cpp /link /IMPLIB:work\mod_research\private_checkpoint_save_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\private_checkpoint_save_fixture.exe /Fo:work\mod_research\private_checkpoint_save_fixture.obj work\mod_research\private_checkpoint_save_fixture.cpp
