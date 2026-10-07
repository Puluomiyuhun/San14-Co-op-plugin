@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /Fe:work\mod_research\private_checkpoint_save_disabled.dll /Fo:work\mod_research\private_checkpoint_save_disabled.obj work\mod_research\private_checkpoint_save_pilot.cpp /link /IMPLIB:work\mod_research\private_checkpoint_save_disabled.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /Fe:work\mod_research\private_checkpoint_save_standard_disabled.dll /Fo:work\mod_research\private_checkpoint_save_standard_disabled.obj work\mod_research\save_checkpoint_pilot.cpp /link /IMPLIB:work\mod_research\private_checkpoint_save_standard_disabled.lib
