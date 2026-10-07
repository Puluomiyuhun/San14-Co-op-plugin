@echo off
setlocal
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if not "%errorlevel%"=="0" exit /b 1
pushd "%~dp0"
ml64 /nologo /c /Fo checkpoint_serialized_storage_gate_fixture_asm.obj checkpoint_live_storage_binding_fixture.asm
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_serialized_storage_gate_production.obj checkpoint_serialized_storage_gate.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_serialized_storage_gate_binding_production.obj checkpoint_live_storage_binding.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /c /Fo:checkpoint_serialized_storage_gate_binding_fixture.obj checkpoint_live_storage_binding.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /c /Fo:checkpoint_serialized_storage_gate_read_core.obj native_storage_read_core.cpp
if not "%errorlevel%"=="0" goto failed
cl /nologo /std:c++17 /EHa /W4 /WX /O2 /MT /DCHECKPOINT_LIVE_STORAGE_BINDING_FIXTURE /Fe:checkpoint_serialized_storage_gate_fixture.exe /Fo:checkpoint_serialized_storage_gate_fixture.obj checkpoint_serialized_storage_gate_fixture.cpp checkpoint_serialized_storage_gate_production.obj checkpoint_serialized_storage_gate_binding_fixture.obj checkpoint_serialized_storage_gate_read_core.obj checkpoint_serialized_storage_gate_fixture_asm.obj /link /INCREMENTAL:NO
if not "%errorlevel%"=="0" goto failed
popd
exit /b 0
:failed
popd
exit /b 1
