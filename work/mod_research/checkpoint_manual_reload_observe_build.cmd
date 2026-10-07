@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:checkpoint_manual_reload_observe.exe /Fo:checkpoint_manual_reload_observe.obj checkpoint_manual_reload_observe.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:checkpoint_manual_reload_observe_fixture.exe /Fo:checkpoint_manual_reload_observe_fixture.obj checkpoint_manual_reload_observe_fixture.cpp
exit /b %errorlevel%
