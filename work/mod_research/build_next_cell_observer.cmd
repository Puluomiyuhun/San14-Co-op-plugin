@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b %errorlevel%
cd /d "%~dp0"
cl /nologo /std:c++17 /EHsc /O2 observe_next_cell.cpp /Fe:observe_next_cell.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /Od /Ob0 next_cell_fixture.cpp /Fe:next_cell_fixture.exe
if errorlevel 1 exit /b %errorlevel%
cl /nologo /std:c++17 /EHsc /O2 /D_CRT_SECURE_NO_WARNINGS next_cell_payload_fixture.cpp /Fe:next_cell_payload_fixture.exe
exit /b %errorlevel%
