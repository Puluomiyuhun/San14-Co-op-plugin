@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /WX checkpoint_title_join_live.cpp /Fe:checkpoint_title_join_live.exe /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /WX /DCHECKPOINT_TITLE_JOIN_OBSERVER_FIXTURE checkpoint_title_join_live.cpp /Fe:checkpoint_title_join_live_fixture.exe /link /INCREMENTAL:NO
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /W4 /WX checkpoint_title_join_live_semantic_fixture.cpp /Fe:checkpoint_title_join_live_semantic_fixture.exe /link /INCREMENTAL:NO
