@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\observe_battle_branches.exe /Fo:work\mod_research\observe_battle_branches.obj work\mod_research\observe_battle_branches.cpp
