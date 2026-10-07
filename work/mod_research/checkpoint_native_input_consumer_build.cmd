@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
python checkpoint_native_input_consumer_audit.py
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 /c checkpoint_native_input_core.cpp /Fo:checkpoint_native_input_consumer_base.obj
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHsc /W4 /WX /O2 checkpoint_native_input_consumer_bridge.cpp checkpoint_native_input_consumer_fixture.cpp checkpoint_native_input_consumer_base.obj /Fe:checkpoint_native_input_consumer_fixture.exe /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
checkpoint_native_input_consumer_fixture.exe checkpoint_native_input_consumer_fixture.json
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
