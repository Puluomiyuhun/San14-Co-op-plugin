@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_persistent_authorized_asm.obj checkpoint_persistent_authorized_bridge.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_persistent_authorized_fixture_asm.obj checkpoint_persistent_authorized_fixture.asm
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo checkpoint_persistent_authorized_physical_asm.obj checkpoint_persistent_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /c checkpoint_persistent_authorized_controller.cpp /Focheckpoint_persistent_authorized_production.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /DCHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE /c checkpoint_persistent_authorized_controller.cpp /Focheckpoint_persistent_authorized_fixture_controller.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /DCHECKPOINT_PERSISTENT_AUTHORIZED_FIXTURE /c checkpoint_persistent_authorized_fixture.cpp /Focheckpoint_persistent_authorized_fixture.obj
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /c checkpoint_persistent_authorized_fixture.cpp /Focheckpoint_persistent_authorized_production_fixture.obj
if errorlevel 1 exit /b 1
for %%f in (checkpoint_persistent_bridge checkpoint_persistent_route_core checkpoint_persistent_route_worker_adapter checkpoint_persistent_route_six_adapter checkpoint_persistent_logical_adapter checkpoint_bound_input_pending_adapter checkpoint_native_input_pending_adapter checkpoint_native_input_core) do (
 cl /nologo /std:c++17 /EHa /W4 /WX /O2 /c %%f.cpp /Focheckpoint_persistent_authorized_%%f.obj
 if errorlevel 1 exit /b 1
)
set SHARED=checkpoint_persistent_authorized_asm.obj checkpoint_persistent_authorized_fixture_asm.obj checkpoint_persistent_authorized_physical_asm.obj checkpoint_persistent_authorized_checkpoint_persistent_bridge.obj checkpoint_persistent_authorized_checkpoint_persistent_route_core.obj checkpoint_persistent_authorized_checkpoint_persistent_route_worker_adapter.obj checkpoint_persistent_authorized_checkpoint_persistent_route_six_adapter.obj checkpoint_persistent_authorized_checkpoint_persistent_logical_adapter.obj checkpoint_persistent_authorized_checkpoint_bound_input_pending_adapter.obj checkpoint_persistent_authorized_checkpoint_native_input_pending_adapter.obj checkpoint_persistent_authorized_checkpoint_native_input_core.obj
link /nologo /OUT:checkpoint_persistent_authorized_fixture.exe checkpoint_persistent_authorized_fixture.obj checkpoint_persistent_authorized_fixture_controller.obj %SHARED%
if errorlevel 1 exit /b 1
link /nologo /OUT:checkpoint_persistent_authorized_production_fixture.exe checkpoint_persistent_authorized_production_fixture.obj checkpoint_persistent_authorized_production.obj %SHARED%
exit /b %errorlevel%
