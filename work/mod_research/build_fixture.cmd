@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /Od /Zi /Fe:work\mod_research\submit_probe_fixture.exe /Fo:work\mod_research\submit_probe_fixture.obj /Fd:work\mod_research\submit_probe_fixture.pdb work\mod_research\submit_probe_fixture.cpp /link /DEBUG /PDB:work\mod_research\submit_probe_fixture_link.pdb
