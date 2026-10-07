@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_cc_load_lifecycle_bridge.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_cc_load_lifecycle_fixture_asm.obj checkpoint_cc_load_lifecycle_fixture.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_cc_load_lifecycle_worker_bridge.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_load_lifecycle_worker_core.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_load_lifecycle_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_load_lifecycle_bytes.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_load_lifecycle_bridge_core.obj checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_cc_load_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /c /Fo:checkpoint_cc_load_lifecycle_fixture_core.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_cc_load_lifecycle_fixture.exe /Fo:checkpoint_cc_load_lifecycle_fixture.obj checkpoint_cc_load_lifecycle_fixture.cpp checkpoint_cc_load_lifecycle_fixture_core.obj checkpoint_cc_load_lifecycle_bridge.obj checkpoint_cc_load_lifecycle_bridge_core.obj checkpoint_cc_load_lifecycle_fixture_asm.obj checkpoint_cc_load_lifecycle_bytes.obj checkpoint_cc_load_lifecycle_worker_bridge.obj checkpoint_cc_load_lifecycle_worker_core.obj checkpoint_cc_load_lifecycle_storage.obj /link /incremental:no
exit /b %errorlevel%
