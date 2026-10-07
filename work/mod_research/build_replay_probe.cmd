@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /Od /Zi /D SAN14_REPLAY /Fe:work\mod_research\replay_submit.exe /Fo:work\mod_research\replay_submit.obj /Fd:work\mod_research\replay_submit.pdb work\mod_research\observe_submit.cpp /link /DEBUG /PDB:work\mod_research\replay_submit_link.pdb
