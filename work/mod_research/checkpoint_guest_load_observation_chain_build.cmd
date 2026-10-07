@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_guest_load_observation_chain_worker_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_guest_load_observation_chain_push_asm.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_guest_load_observation_chain_fixture_asm.obj checkpoint_guest_load_observation_chain_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_worker.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_push.obj checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_bytes.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_identity.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /c /Fo:checkpoint_guest_load_observation_chain_atomic.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /Fe:checkpoint_guest_load_observation_chain_fixture.exe /Fo:checkpoint_guest_load_observation_chain_fixture.obj checkpoint_guest_load_observation_chain_fixture.cpp checkpoint_guest_load_observation_chain_worker_asm.obj checkpoint_guest_load_observation_chain_push_asm.obj checkpoint_guest_load_observation_chain_fixture_asm.obj checkpoint_guest_load_observation_chain_worker.obj checkpoint_guest_load_observation_chain_push.obj checkpoint_guest_load_observation_chain_storage.obj checkpoint_guest_load_observation_chain_bytes.obj checkpoint_guest_load_observation_chain_lifecycle.obj checkpoint_guest_load_observation_chain_identity.obj checkpoint_guest_load_observation_chain_atomic.obj /link /incremental:no
exit /b %errorlevel%
