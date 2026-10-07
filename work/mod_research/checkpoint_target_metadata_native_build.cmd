@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_target_metadata_native.obj checkpoint_target_metadata_native.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /D CHECKPOINT_TARGET_METADATA_NATIVE_FIXTURE /c /Fo:checkpoint_target_metadata_native_fixture_core.obj checkpoint_target_metadata_native.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHa /std:c++17 /O2 /MT /D CHECKPOINT_TARGET_METADATA_NATIVE_FIXTURE /Fe:checkpoint_target_metadata_native_fixture.exe /Fo:checkpoint_target_metadata_native_fixture.obj checkpoint_target_metadata_native_fixture.cpp checkpoint_target_metadata_native_fixture_core.obj checkpoint_target_metadata_core.obj checkpoint_target_metadata_storage.obj /link /incremental:no
exit /b %errorlevel%
