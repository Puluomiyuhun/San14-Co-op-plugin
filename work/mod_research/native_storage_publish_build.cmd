@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:native_storage_publish_core.obj native_storage_publish_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /Fe:native_storage_publish_fixture.exe /Fo:native_storage_publish_fixture.obj native_storage_publish_fixture.cpp native_storage_publish_core.obj native_storage_read_core.obj /link /incremental:no
exit /b %errorlevel%
