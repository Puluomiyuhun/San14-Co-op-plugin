@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /std:c++17 /W4 /WX /O2 /EHa /Fo:checkpoint_load_request_commit.obj /c checkpoint_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /EHa /Fo:checkpoint_load_request_boundary.obj /c checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /EHa /Fo:checkpoint_load_request_storage.obj /c native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /W4 /WX /O2 /EHa /Fo:checkpoint_load_request_commit_fixture.obj /c checkpoint_load_request_commit_fixture.cpp
if errorlevel 1 exit /b 1
link /nologo /incremental:no /out:checkpoint_load_request_commit_fixture.exe checkpoint_load_request_commit.obj checkpoint_load_request_boundary.obj checkpoint_load_request_storage.obj checkpoint_load_request_commit_fixture.obj kernel32.lib bcrypt.lib
exit /b %errorlevel%
