@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_dynamic_file_profile.obj checkpoint_dynamic_file_profile.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_dynamic_load_request_commit.obj checkpoint_dynamic_load_request_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_dynamic_cc_load_observer.obj checkpoint_dynamic_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_dynamic_cc_load_lifecycle.obj checkpoint_dynamic_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_load_input_boundary.obj checkpoint_load_input_boundary.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_native_storage_read_core.obj native_storage_read_core.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_load_worker_bridge.obj checkpoint_load_worker_bridge.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_checkpoint_push_bridge.obj checkpoint_push_bridge.cpp
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo dynamic_files_checkpoint_load_worker_bridge_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo dynamic_files_checkpoint_cc_load_observer_fixture_asm.obj checkpoint_cc_load_observer_fixture.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo dynamic_files_checkpoint_push_bridge_asm.obj checkpoint_push_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo dynamic_files_checkpoint_cc_load_lifecycle_fixture_asm.obj checkpoint_cc_load_lifecycle_fixture.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_DYNAMIC_CC_LOAD_OBSERVER_FIXTURE /c /Fo:dynamic_files_bytes_fixture_core.obj checkpoint_dynamic_cc_load_observer.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /DCHECKPOINT_DYNAMIC_CC_LOAD_LIFECYCLE_FIXTURE /c /Fo:dynamic_files_lifecycle_fixture_core.obj checkpoint_dynamic_cc_load_lifecycle.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_load_request_commit_fixture.obj checkpoint_dynamic_load_request_commit_fixture.cpp
if errorlevel 1 exit /b 1
link /nologo /incremental:no /out:checkpoint_dynamic_load_request_commit_fixture.exe dynamic_files_checkpoint_dynamic_file_profile.obj dynamic_files_native_storage_read_core.obj dynamic_files_checkpoint_dynamic_load_request_commit.obj dynamic_files_checkpoint_load_input_boundary.obj dynamic_files_load_request_commit_fixture.obj kernel32.lib bcrypt.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_cc_load_observer_fixture.obj checkpoint_dynamic_cc_load_observer_fixture.cpp
if errorlevel 1 exit /b 1
link /nologo /incremental:no /out:checkpoint_dynamic_cc_load_observer_fixture.exe dynamic_files_checkpoint_dynamic_file_profile.obj dynamic_files_native_storage_read_core.obj dynamic_files_bytes_fixture_core.obj dynamic_files_checkpoint_load_worker_bridge.obj dynamic_files_checkpoint_load_worker_bridge_asm.obj dynamic_files_checkpoint_cc_load_observer_fixture_asm.obj dynamic_files_cc_load_observer_fixture.obj kernel32.lib bcrypt.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT  /c /Fo:dynamic_files_cc_load_lifecycle_fixture.obj checkpoint_dynamic_cc_load_lifecycle_fixture.cpp
if errorlevel 1 exit /b 1
link /nologo /incremental:no /out:checkpoint_dynamic_cc_load_lifecycle_fixture.exe dynamic_files_checkpoint_dynamic_file_profile.obj dynamic_files_native_storage_read_core.obj dynamic_files_lifecycle_fixture_core.obj dynamic_files_checkpoint_dynamic_cc_load_observer.obj dynamic_files_checkpoint_load_worker_bridge.obj dynamic_files_checkpoint_load_worker_bridge_asm.obj dynamic_files_checkpoint_push_bridge.obj dynamic_files_checkpoint_push_bridge_asm.obj dynamic_files_checkpoint_cc_load_lifecycle_fixture_asm.obj dynamic_files_cc_load_lifecycle_fixture.obj kernel32.lib bcrypt.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_dynamic_file_profile_fixture.exe /Fo:dynamic_files_profile_fixture.obj checkpoint_dynamic_file_profile_fixture.cpp dynamic_files_checkpoint_dynamic_file_profile.obj /link /incremental:no
exit /b %errorlevel%
