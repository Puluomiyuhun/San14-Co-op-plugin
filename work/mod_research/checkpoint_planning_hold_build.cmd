@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
if not exist checkpoint_planning_hold_objects mkdir checkpoint_planning_hold_objects
cl /Fo:checkpoint_planning_hold_objects\ /nologo /std:c++17 /EHa /W4 /WX /wd4324 /LD checkpoint_planning_hold_adapter.cpp checkpoint_native_input_core.cpp checkpoint_native_input_consumer_bridge.cpp checkpoint_native_input_pending_adapter.cpp /Fe:checkpoint_planning_hold.dll /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 checkpoint_planning_hold_fixture.cpp checkpoint_planning_hold.lib /Fe:checkpoint_planning_hold_fixture.exe /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /c checkpoint_planning_hold_user_dry.cpp /Fo:checkpoint_planning_hold_objects\user_dry_production.obj
if errorlevel 1 exit /b %errorlevel%
ml64 /nologo /c /Fo checkpoint_planning_hold_objects\persistent_bridge_asm.obj checkpoint_persistent_bridge.asm
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /DCHECKPOINT_PLANNING_HOLD_OWNED_DRY /Fo:checkpoint_planning_hold_objects\ checkpoint_planning_hold_fixture.cpp checkpoint_planning_hold_user_dry.cpp checkpoint_persistent_bridge.cpp checkpoint_planning_hold_objects\persistent_bridge_asm.obj checkpoint_planning_hold.lib /Fe:checkpoint_planning_hold_user_dry_fixture.exe /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHa /W4 /WX /wd4324 /Fo:checkpoint_planning_hold_objects\ checkpoint_planning_hold_user_production_fixture.cpp checkpoint_planning_hold_objects\user_dry_production.obj checkpoint_planning_hold.lib /Fe:checkpoint_planning_hold_user_production_fixture.exe /link /INCREMENTAL:NO
