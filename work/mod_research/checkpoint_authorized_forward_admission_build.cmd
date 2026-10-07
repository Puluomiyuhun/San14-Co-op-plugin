@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_authorized_forward_admission_session_production.obj checkpoint_forward_native_session.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_authorized_forward_admission_production.obj checkpoint_authorized_forward_admission_controller.cpp
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_authorized_forward_admission_asm0.obj checkpoint_load_worker_bridge.asm
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_authorized_forward_admission_asm1.obj checkpoint_load_dispatch_bridge.asm
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_authorized_forward_admission_asm2.obj checkpoint_guest_native_session_fixture.asm
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_authorized_forward_admission_asm4.obj checkpoint_native_input_hwbp_fixture.asm
if not "%errorlevel%"=="0" goto failed
ml64 /nologo /c /Fo checkpoint_authorized_forward_admission_asm5.obj checkpoint_authorized_forward_admission_bridge.asm
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp0.obj checkpoint_load_worker_bridge.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp1.obj checkpoint_load_dispatch_bridge.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp2.obj native_storage_read_core.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp3.obj checkpoint_cc_load_observer.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp4.obj checkpoint_cc_load_lifecycle.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp5.obj checkpoint_title_identity_adapter.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp6.obj checkpoint_identity_pair_commit.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp7.obj checkpoint_load_request_commit.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp8.obj checkpoint_load_input_boundary.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp9.obj checkpoint_load_hook_set.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp10.obj checkpoint_forward_native_session.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp11.obj checkpoint_forward_planning_observer.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp12.obj checkpoint_bound_input_pending_adapter.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp13.obj checkpoint_native_input_hwbp.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_cpp14.obj checkpoint_authorized_forward_admission_controller.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /c /Fo:checkpoint_authorized_forward_admission_queue.obj checkpoint_native_queue_adapter_core.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_NATIVE_QUEUE_ADAPTER_FIXTURE /DCHECKPOINT_CC_LOAD_OBSERVER_FIXTURE /DCHECKPOINT_CC_LOAD_LIFECYCLE_FIXTURE /DCHECKPOINT_TITLE_IDENTITY_ADAPTER_FIXTURE /DCHECKPOINT_FORWARD_NATIVE_SESSION_FIXTURE /DCHECKPOINT_FORWARD_PLANNING_OBSERVER_FIXTURE /Fe:checkpoint_authorized_forward_admission_fixture.exe /Fo:checkpoint_authorized_forward_admission_fixture.obj checkpoint_authorized_forward_admission_fixture.cpp checkpoint_authorized_forward_admission_asm0.obj checkpoint_authorized_forward_admission_asm1.obj checkpoint_authorized_forward_admission_asm2.obj checkpoint_authorized_forward_admission_asm4.obj checkpoint_authorized_forward_admission_asm5.obj checkpoint_authorized_forward_admission_cpp0.obj checkpoint_authorized_forward_admission_cpp1.obj checkpoint_authorized_forward_admission_cpp2.obj checkpoint_authorized_forward_admission_cpp3.obj checkpoint_authorized_forward_admission_cpp4.obj checkpoint_authorized_forward_admission_cpp5.obj checkpoint_authorized_forward_admission_cpp6.obj checkpoint_authorized_forward_admission_cpp7.obj checkpoint_authorized_forward_admission_cpp8.obj checkpoint_authorized_forward_admission_cpp9.obj checkpoint_authorized_forward_admission_cpp10.obj checkpoint_authorized_forward_admission_cpp11.obj checkpoint_authorized_forward_admission_cpp12.obj checkpoint_authorized_forward_admission_cpp13.obj checkpoint_authorized_forward_admission_cpp14.obj checkpoint_authorized_forward_admission_queue.obj /link /incremental:no
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
