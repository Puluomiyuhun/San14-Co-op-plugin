@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "%~dp0"
cl /nologo /W4 /WX /EHa /std:c++17 /Gy /O2 /MT /c /Fo:checkpoint_dynamic_identity_profile_review_core.obj checkpoint_dynamic_title_identity_adapter.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /Gy /O2 /MT /Fo:checkpoint_dynamic_identity_profile_review.obj /Fe:checkpoint_dynamic_identity_profile_review_fixture.exe checkpoint_dynamic_identity_profile_review_fixture.cpp checkpoint_dynamic_identity_profile_review_core.obj /link /OPT:REF /incremental:no
exit /b %errorlevel%
