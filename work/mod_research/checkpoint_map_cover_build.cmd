@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /I "C:\Program Files (x86)\Windows Kits\10\Include\10.0.19041.0\cppwinrt" /c /Fo:checkpoint_map_cover_capture.obj checkpoint_map_cover_capture.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /I "C:\Program Files (x86)\Windows Kits\10\Include\10.0.19041.0\cppwinrt" /Fe:checkpoint_map_cover_fixture.exe /Fo:checkpoint_map_cover_fixture.obj checkpoint_map_cover_fixture.cpp checkpoint_map_cover_capture.obj native_storage_read_core.obj /link /incremental:no
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /I "C:\Program Files (x86)\Windows Kits\10\Include\10.0.19041.0\cppwinrt" /Fe:checkpoint_map_cover_probe.exe /Fo:checkpoint_map_cover_probe.obj checkpoint_map_cover_probe.cpp checkpoint_map_cover_capture.obj native_storage_read_core.obj /link /incremental:no
exit /b %errorlevel%
