@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_production.obj checkpoint_planning_return_observer.cpp
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_planning_return_observer_worker_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_planning_return_observer_dispatch_asm.obj checkpoint_load_dispatch_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_planning_return_observer_fixture_asm.obj checkpoint_planning_return_observer_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_worker.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_dispatch.obj checkpoint_load_dispatch_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_storage.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_bytes.obj checkpoint_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_lifecycle.obj checkpoint_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_identity.obj checkpoint_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_atomic.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_request.obj checkpoint_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_input.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_hooks.obj checkpoint_load_hook_set.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_planning_return_observer_session.obj checkpoint_guest_native_session.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_PLANNING_RETURN_OBSERVER_FIXTURE /c /Fo:checkpoint_planning_return_observer_core.obj checkpoint_planning_return_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_planning_return_observer_fixture.exe /Fo:checkpoint_planning_return_observer_fixture.obj checkpoint_planning_return_observer_fixture.cpp checkpoint_planning_return_observer_core.obj checkpoint_planning_return_observer_worker_asm.obj checkpoint_planning_return_observer_dispatch_asm.obj checkpoint_planning_return_observer_fixture_asm.obj checkpoint_planning_return_observer_worker.obj checkpoint_planning_return_observer_dispatch.obj checkpoint_planning_return_observer_storage.obj checkpoint_planning_return_observer_bytes.obj checkpoint_planning_return_observer_lifecycle.obj checkpoint_planning_return_observer_identity.obj checkpoint_planning_return_observer_atomic.obj checkpoint_planning_return_observer_request.obj checkpoint_planning_return_observer_input.obj checkpoint_planning_return_observer_hooks.obj checkpoint_planning_return_observer_session.obj /link /incremental:no
exit /b %errorlevel%
