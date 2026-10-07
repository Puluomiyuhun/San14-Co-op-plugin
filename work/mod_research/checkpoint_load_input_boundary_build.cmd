@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_load_input_boundary.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_load_input_boundary_fixture.exe /Fo:checkpoint_load_input_boundary_fixture.obj checkpoint_load_input_boundary_fixture.cpp checkpoint_load_input_boundary.obj /link /incremental:no
exit /b %errorlevel%
