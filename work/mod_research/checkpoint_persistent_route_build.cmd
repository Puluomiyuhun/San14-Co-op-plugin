@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
ml64 /nologo /c /Fo checkpoint_persistent_route_worker_asm.obj checkpoint_load_worker_bridge.asm
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /O2 /c checkpoint_persistent_route_core.cpp checkpoint_persistent_route_worker_adapter.cpp checkpoint_persistent_route_fixture.cpp /Fo.\
if errorlevel 1 exit /b 1
cl /nologo /std:c++17 /EHa /W4 /O2 /c checkpoint_load_worker_bridge.cpp /Focheckpoint_persistent_route_frozen_worker.obj
if errorlevel 1 exit /b 1
link /nologo /OUT:checkpoint_persistent_route_fixture.exe checkpoint_persistent_route_core.obj checkpoint_persistent_route_worker_adapter.obj checkpoint_persistent_route_fixture.obj checkpoint_persistent_route_frozen_worker.obj checkpoint_persistent_route_worker_asm.obj
exit /b %errorlevel%
