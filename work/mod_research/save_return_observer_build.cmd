@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\save_return_observer.exe /Fo:work\mod_research\save_return_observer.obj work\mod_research\save_return_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\save_return_observer_fixture.exe /Fo:work\mod_research\save_return_observer_fixture.obj work\mod_research\save_return_observer_fixture.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\save_return_observer_cleanup_fixture.exe /Fo:work\mod_research\save_return_observer_cleanup_fixture.obj work\mod_research\auto_reload_cleanup_fixture.cpp
