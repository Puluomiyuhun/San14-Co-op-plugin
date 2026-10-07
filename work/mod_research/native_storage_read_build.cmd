@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cd /d "%~dp0"
cl /nologo /std:c++17 /EHsc /W4 /O2 /Fo:native_storage_read_core.obj /c native_storage_read_core.cpp
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /O2 /Fo:native_storage_read_fixture.obj /Fe:native_storage_read_fixture.exe native_storage_read_fixture.cpp native_storage_read_core.obj /link bcrypt.lib
exit /b %errorlevel%
