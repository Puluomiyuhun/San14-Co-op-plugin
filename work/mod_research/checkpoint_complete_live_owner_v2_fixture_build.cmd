@echo off
setlocal EnableDelayedExpansion
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
set flags=/DCHECKPOINT_COMPLETE_LIVE_OWNER_FIXTURE /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /DCHECKPOINT_LIVE_RUNTIME_GUARDS_V2_FIXTURE /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE
set objects=
set index=0
for %%F in (checkpoint_load_worker_bridge.cpp checkpoint_load_dispatch_bridge.cpp native_storage_read_core.cpp checkpoint_cc_load_observer.cpp checkpoint_cc_load_lifecycle.cpp checkpoint_title_identity_adapter.cpp checkpoint_identity_pair_commit.cpp checkpoint_load_request_commit.cpp checkpoint_load_input_boundary.cpp checkpoint_load_hook_set.cpp checkpoint_forward_native_session.cpp checkpoint_forward_planning_observer_v2.cpp checkpoint_bound_input_pending_adapter.cpp checkpoint_native_input_hwbp.cpp checkpoint_authorized_forward_admission_controller.cpp checkpoint_native_queue_adapter_core.cpp checkpoint_live_storage_binding.cpp checkpoint_serialized_storage_gate.cpp checkpoint_live_runtime_guards_v2.cpp) do (
  cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT !flags! /c /Fo:checkpoint_complete_live_owner_v2_f!index!.obj %%F
  if errorlevel 1 goto failed
  set objects=!objects! checkpoint_complete_live_owner_v2_f!index!.obj
  set /a index+=1 >nul
)
set index=0
for %%F in (checkpoint_load_worker_bridge.asm checkpoint_load_dispatch_bridge.asm checkpoint_authorized_forward_admission_bridge.asm checkpoint_guest_native_session_fixture.asm checkpoint_native_input_hwbp_fixture.asm checkpoint_live_storage_binding_fixture.asm) do (
  ml64 /nologo /c /Fo checkpoint_complete_live_owner_v2_fa!index!.obj %%F
  if errorlevel 1 goto failed
  set objects=!objects! checkpoint_complete_live_owner_v2_fa!index!.obj
  set /a index+=1 >nul
)
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT !flags! /Fe:checkpoint_complete_live_owner_v2_fixture.exe /Fo:checkpoint_complete_live_owner_v2_fixture.obj checkpoint_complete_live_owner_v2_fixture.cpp !objects! /link /INCREMENTAL:NO
if errorlevel 1 goto failed
popd
exit /b 0
:failed
popd
exit /b 1
