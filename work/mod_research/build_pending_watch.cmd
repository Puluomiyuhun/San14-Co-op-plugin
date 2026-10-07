@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\observe_pending_writes.exe /Fo:work\mod_research\observe_pending_writes.obj work\mod_research\observe_pending_writes.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\pending_watch_fixture.exe /Fo:work\mod_research\pending_watch_fixture.obj work\mod_research\pending_watch_fixture.cpp
