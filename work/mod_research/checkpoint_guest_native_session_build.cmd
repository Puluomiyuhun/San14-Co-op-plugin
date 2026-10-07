@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_guest_native_session_production.obj checkpoint_guest_native_session.cpp
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_guest_native_session_worker_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_guest_native_session_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_guest_native_session_fixture_asm.obj checkpoint_guest_native_session_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_worker.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_dispatch.obj checkpoint_load_dispatch_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_bytes.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_identity.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_atomic.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_request.obj checkpoint_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_input.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_hooks.obj checkpoint_load_hook_set.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /c /Fo:checkpoint_guest_native_session_session.obj checkpoint_guest_native_session.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /Fe:checkpoint_guest_native_session_fixture.exe /Fo:checkpoint_guest_native_session_fixture.obj checkpoint_guest_native_session_fixture.cpp checkpoint_guest_native_session_worker_asm.obj checkpoint_guest_native_session_dispatch_asm.obj checkpoint_guest_native_session_fixture_asm.obj checkpoint_guest_native_session_worker.obj checkpoint_guest_native_session_dispatch.obj checkpoint_guest_native_session_storage.obj checkpoint_guest_native_session_bytes.obj checkpoint_guest_native_session_lifecycle.obj checkpoint_guest_native_session_identity.obj checkpoint_guest_native_session_atomic.obj checkpoint_guest_native_session_request.obj checkpoint_guest_native_session_input.obj checkpoint_guest_native_session_hooks.obj checkpoint_guest_native_session_session.obj /link /incremental:no
exit /b %errorlevel%
