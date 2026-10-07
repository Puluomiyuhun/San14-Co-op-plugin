@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /std:c++17 /O2 /W4 /WX /EHa /Fo:checkpoint_load_hook_set.obj /c checkpoint_load_hook_set.cpp
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /O2 /W4 /WX /EHa /Fo:checkpoint_load_hook_set_fixture.obj /c checkpoint_load_hook_set_fixture.cpp
if errorlevel 1 exit /b 1
link /nologo /incremental:no /out:checkpoint_load_hook_set_fixture.exe checkpoint_load_hook_set.obj checkpoint_load_hook_set_fixture.obj kernel32.lib
exit /b %errorlevel%
