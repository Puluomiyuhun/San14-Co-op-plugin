@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_title_identity_adapter_bridge.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_title_identity_adapter_fixture_asm.obj checkpoint_title_identity_adapter_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_title_identity_adapter_bridge_core.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_title_identity_adapter_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_title_identity_adapter_bytes.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_title_identity_adapter_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_title_identity_adapter_atomic.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_title_identity_adapter.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_title_identity_adapter_fixture_core.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_title_identity_adapter_fixture.exe /Fo:checkpoint_title_identity_adapter_fixture.obj checkpoint_title_identity_adapter_fixture.cpp checkpoint_title_identity_adapter_fixture_core.obj checkpoint_title_identity_adapter_bridge.obj checkpoint_title_identity_adapter_bridge_core.obj checkpoint_title_identity_adapter_fixture_asm.obj checkpoint_title_identity_adapter_bytes.obj checkpoint_title_identity_adapter_lifecycle.obj checkpoint_title_identity_adapter_atomic.obj checkpoint_title_identity_adapter_storage.obj /link /incremental:no
exit /b %errorlevel%
