@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
pushd "%~dp0"
cl /nologo /std:c++17 /EHa /W4 /WX /MT /O2 /Fe:checkpoint_complete_live_abi_verify.exe /Fo:checkpoint_complete_live_abi_verify.obj checkpoint_complete_live_abi_verify.cpp
set taskExit=%errorlevel%
popd
exit /b %taskExit%
