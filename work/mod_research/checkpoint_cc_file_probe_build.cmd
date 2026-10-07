@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_cc_file_probe_bridge.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_file_probe_bridge_core.obj checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_file_probe_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /Fe:checkpoint_cc_file_probe.dll /Fo:checkpoint_cc_file_probe.obj checkpoint_cc_file_probe.cpp checkpoint_cc_file_probe_bridge.obj checkpoint_cc_file_probe_bridge_core.obj checkpoint_cc_file_probe_storage.obj /link /incremental:no /IMPLIB:checkpoint_cc_file_probe.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /LD /D CHECKPOINT_CC_FILE_FIXTURE /Fe:checkpoint_cc_file_probe_fixture.dll /Fo:checkpoint_cc_file_probe_fixture_dll.obj checkpoint_cc_file_probe.cpp checkpoint_cc_file_probe_bridge.obj checkpoint_cc_file_probe_bridge_core.obj checkpoint_cc_file_probe_storage.obj /link /incremental:no /IMPLIB:checkpoint_cc_file_probe_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /Fe:checkpoint_cc_file_probe_fixture.exe /Fo:checkpoint_cc_file_probe_fixture.obj checkpoint_cc_file_probe_fixture.cpp checkpoint_cc_file_probe_storage.obj /link /incremental:no
exit /b %errorlevel%
