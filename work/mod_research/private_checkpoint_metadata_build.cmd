@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /c /Fo:work\mod_research\private_checkpoint_metadata_core.obj work\mod_research\private_checkpoint_metadata_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\private_checkpoint_metadata_fixture.exe /Fo:work\mod_research\private_checkpoint_metadata_fixture.obj work\mod_research\private_checkpoint_metadata_fixture.cpp work\mod_research\private_checkpoint_metadata_core.obj
