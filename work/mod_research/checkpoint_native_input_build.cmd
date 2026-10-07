@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 checkpoint_native_input_core.cpp checkpoint_native_input_fixture.cpp /Fe:checkpoint_native_input_fixture.exe /link /INCREMENTAL:NO
if errorlevel 1 (
    popd
    exit /b 1
)
checkpoint_native_input_fixture.exe checkpoint_native_input_fixture.json
set checkpoint_input_result=%errorlevel%
popd
exit /b %checkpoint_input_result%
