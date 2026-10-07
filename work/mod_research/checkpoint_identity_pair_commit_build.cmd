@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fo:checkpoint_identity_pair_commit.obj checkpoint_identity_pair_commit.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /Fe:checkpoint_identity_pair_commit_fixture.exe /Fo:checkpoint_identity_pair_commit_fixture.obj checkpoint_identity_pair_commit_fixture.cpp checkpoint_identity_pair_commit.obj /link /incremental:no
exit /b %errorlevel%
