@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_session_generation_worker_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_session_generation_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_guest_native_session.obj checkpoint_guest_native_session.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_load_worker_bridge.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_load_dispatch_bridge.obj checkpoint_load_dispatch_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_native_storage_read_core.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_cc_load_observer.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_cc_load_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_title_identity_adapter.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_identity_pair_commit.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_load_request_commit.obj checkpoint_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_load_input_boundary.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_load_hook_set.obj checkpoint_load_hook_set.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:checkpoint_session_generation_production_checkpoint_session_generation_bank.obj checkpoint_session_generation_bank.cpp
if errorlevel 1 exit /b 1
link /nologo /DLL /incremental:no /OUT:checkpoint_session_generation_production_bank.dll checkpoint_session_generation_production_checkpoint_guest_native_session.obj checkpoint_session_generation_production_checkpoint_load_worker_bridge.obj checkpoint_session_generation_production_checkpoint_load_dispatch_bridge.obj checkpoint_session_generation_production_native_storage_read_core.obj checkpoint_session_generation_production_checkpoint_cc_load_observer.obj checkpoint_session_generation_production_checkpoint_cc_load_lifecycle.obj checkpoint_session_generation_production_checkpoint_title_identity_adapter.obj checkpoint_session_generation_production_checkpoint_identity_pair_commit.obj checkpoint_session_generation_production_checkpoint_load_request_commit.obj checkpoint_session_generation_production_checkpoint_load_input_boundary.obj checkpoint_session_generation_production_checkpoint_load_hook_set.obj checkpoint_session_generation_production_checkpoint_session_generation_bank.obj checkpoint_session_generation_worker_asm.obj checkpoint_session_generation_dispatch_asm.obj
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_guest_native_session.obj checkpoint_guest_native_session.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_load_worker_bridge.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_load_dispatch_bridge.obj checkpoint_load_dispatch_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_native_storage_read_core.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_cc_load_observer.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_cc_load_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_title_identity_adapter.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_identity_pair_commit.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_load_request_commit.obj checkpoint_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_load_input_boundary.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_load_hook_set.obj checkpoint_load_hook_set.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_fixture_checkpoint_session_generation_bank.obj checkpoint_session_generation_bank.cpp
if errorlevel 1 exit /b 1
link /nologo /DLL /incremental:no /OUT:checkpoint_session_generation_fixture_bank.dll checkpoint_session_generation_fixture_checkpoint_guest_native_session.obj checkpoint_session_generation_fixture_checkpoint_load_worker_bridge.obj checkpoint_session_generation_fixture_checkpoint_load_dispatch_bridge.obj checkpoint_session_generation_fixture_native_storage_read_core.obj checkpoint_session_generation_fixture_checkpoint_cc_load_observer.obj checkpoint_session_generation_fixture_checkpoint_cc_load_lifecycle.obj checkpoint_session_generation_fixture_checkpoint_title_identity_adapter.obj checkpoint_session_generation_fixture_checkpoint_identity_pair_commit.obj checkpoint_session_generation_fixture_checkpoint_load_request_commit.obj checkpoint_session_generation_fixture_checkpoint_load_input_boundary.obj checkpoint_session_generation_fixture_checkpoint_load_hook_set.obj checkpoint_session_generation_fixture_checkpoint_session_generation_bank.obj checkpoint_session_generation_worker_asm.obj checkpoint_session_generation_dispatch_asm.obj
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_session_generation_owner_production.obj checkpoint_session_generation_owner.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /c /Fo:checkpoint_session_generation_owner_fixture.obj checkpoint_session_generation_owner.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_GUEST_NATIVE_SESSION_FIXTURE /DCHECKPOINT_SESSION_GENERATION_FIXTURE /Fe:checkpoint_session_generation_fixture.exe /Fo:checkpoint_session_generation_fixture.obj checkpoint_session_generation_fixture.cpp checkpoint_session_generation_owner_fixture.obj /link /incremental:no
exit /b %errorlevel%
