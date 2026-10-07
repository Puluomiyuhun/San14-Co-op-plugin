@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\identity_pair_fixture.exe /Fo:work\mod_research\identity_pair_fixture.obj work\mod_research\identity_pair_fixture.cpp
