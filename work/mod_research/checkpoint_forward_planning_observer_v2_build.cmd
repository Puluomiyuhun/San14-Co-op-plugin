@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_production.obj checkpoint_forward_planning_observer_v2.cpp
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_forward_planning_observer_v2_worker_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_forward_planning_observer_v2_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_forward_planning_observer_v2_fixture_asm.obj checkpoint_forward_planning_observer_v2_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_worker.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_dispatch.obj checkpoint_load_dispatch_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_bytes.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_identity.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_atomic.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_request.obj checkpoint_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_input.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_hooks.obj checkpoint_load_hook_set.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_forward_planning_observer_v2_session.obj checkpoint_forward_native_session.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_forward_planning_observer_v2_core.obj checkpoint_forward_planning_observer_v2.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_forward_planning_observer_v2_fixture.exe /Fo:checkpoint_forward_planning_observer_v2_fixture.obj checkpoint_forward_planning_observer_v2_fixture.cpp checkpoint_forward_planning_observer_v2_core.obj checkpoint_forward_planning_observer_v2_worker_asm.obj checkpoint_forward_planning_observer_v2_dispatch_asm.obj checkpoint_forward_planning_observer_v2_fixture_asm.obj checkpoint_forward_planning_observer_v2_worker.obj checkpoint_forward_planning_observer_v2_dispatch.obj checkpoint_forward_planning_observer_v2_storage.obj checkpoint_forward_planning_observer_v2_bytes.obj checkpoint_forward_planning_observer_v2_lifecycle.obj checkpoint_forward_planning_observer_v2_identity.obj checkpoint_forward_planning_observer_v2_atomic.obj checkpoint_forward_planning_observer_v2_request.obj checkpoint_forward_planning_observer_v2_input.obj checkpoint_forward_planning_observer_v2_hooks.obj checkpoint_forward_planning_observer_v2_session.obj /link /incremental:no
exit /b %errorlevel%
