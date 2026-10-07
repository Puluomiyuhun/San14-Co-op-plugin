@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /c checkpoint_task_attribution_core.cpp /Fo:checkpoint_task_attribution_core.obj
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /c checkpoint_task_attribution_adapter.cpp /Fo:checkpoint_task_attribution_adapter.obj
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /c checkpoint_persistent_route_core.cpp /Fo:checkpoint_task_attribution_route.obj
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /c checkpoint_persistent_route_worker_adapter.cpp /Fo:checkpoint_task_attribution_worker.obj
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /c checkpoint_persistent_route_six_adapter.cpp /Fo:checkpoint_task_attribution_six.obj
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /c checkpoint_persistent_bridge.cpp /Fo:checkpoint_task_attribution_bridge.obj
if errorlevel 1 exit /b %errorlevel%
ml64 /nologo /c /Fo checkpoint_task_attribution_bridge_asm.obj checkpoint_persistent_bridge.asm
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX checkpoint_task_attribution_fixture.cpp checkpoint_task_attribution_core.obj checkpoint_task_attribution_adapter.obj checkpoint_task_attribution_route.obj checkpoint_task_attribution_worker.obj checkpoint_task_attribution_six.obj checkpoint_task_attribution_bridge.obj checkpoint_task_attribution_bridge_asm.obj /Fe:checkpoint_task_attribution_fixture.exe /Fo:checkpoint_task_attribution_fixture.obj /link /INCREMENTAL:NO
