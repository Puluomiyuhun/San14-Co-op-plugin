@echo off
setlocal EnableDelayedExpansion
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
set objects=
set index=0
for %%F in (checkpoint_load_worker_bridge.cpp checkpoint_load_dispatch_bridge.cpp native_storage_read_core.cpp checkpoint_cc_load_observer.cpp checkpoint_cc_load_lifecycle.cpp checkpoint_title_identity_adapter.cpp checkpoint_identity_pair_commit.cpp checkpoint_load_request_commit.cpp checkpoint_load_input_boundary.cpp checkpoint_load_hook_set.cpp checkpoint_forward_native_session.cpp checkpoint_forward_planning_observer_v2.cpp checkpoint_bound_input_pending_adapter.cpp checkpoint_native_input_hwbp.cpp checkpoint_authorized_forward_admission_controller.cpp checkpoint_native_queue_adapter_core.cpp checkpoint_live_storage_binding.cpp checkpoint_serialized_storage_gate.cpp checkpoint_live_runtime_guards_v2.cpp checkpoint_complete_live_owner_v2.cpp) do (
  cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_complete_live_owner_v2_p!index!.obj %%F
  if errorlevel 1 goto failed
  set objects=!objects! checkpoint_complete_live_owner_v2_p!index!.obj
  set /a index+=1 >nul
)
set index=0
for %%F in (checkpoint_load_worker_bridge.asm checkpoint_load_dispatch_bridge.asm checkpoint_authorized_forward_admission_bridge.asm) do (
  ml64 /nologo /c /Fo checkpoint_complete_live_owner_v2_a!index!.obj %%F
  if errorlevel 1 goto failed
  set objects=!objects! checkpoint_complete_live_owner_v2_a!index!.obj
  set /a index+=1 >nul
)
link /nologo /DLL /INCREMENTAL:NO /OUT:checkpoint_complete_live_owner_v2.dll !objects! kernel32.lib bcrypt.lib
if errorlevel 1 goto failed
cl /nologo /std:c++17 /W4 /WX /O2 /MT /Fe:checkpoint_complete_live_owner_v2_abi.exe /Fo:checkpoint_complete_live_owner_v2_abi.obj checkpoint_complete_live_owner_abi.cpp
if errorlevel 1 goto failed
popd
exit /b 0
:failed
popd
exit /b 1
