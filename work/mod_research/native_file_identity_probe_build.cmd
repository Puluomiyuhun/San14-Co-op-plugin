@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo native_file_identity_probe_bridge.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:native_file_identity_probe_bridge_core.obj checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:native_file_identity_probe_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /Fe:native_file_identity_probe.dll /Fo:native_file_identity_probe.obj native_file_identity_probe.cpp native_file_identity_probe_bridge.obj native_file_identity_probe_bridge_core.obj native_file_identity_probe_storage.obj /link /incremental:no /IMPLIB:native_file_identity_probe.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /D NATIVE_FILE_IDENTITY_FIXTURE /Fe:native_file_identity_probe_fixture.dll /Fo:native_file_identity_probe_fixture_dll.obj native_file_identity_probe.cpp native_file_identity_probe_bridge.obj native_file_identity_probe_bridge_core.obj native_file_identity_probe_storage.obj /link /incremental:no /IMPLIB:native_file_identity_probe_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /Fe:native_file_identity_probe_fixture.exe /Fo:native_file_identity_probe_fixture.obj native_file_identity_probe_fixture.cpp native_file_identity_probe_storage.obj /link /incremental:no
exit /b %errorlevel%
