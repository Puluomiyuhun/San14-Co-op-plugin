@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /Fe:work\mod_research\auto_cache_pilot.dll /Fo:work\mod_research\auto_cache_pilot.obj work\mod_research\auto_cache_pilot.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /DAUTO_CACHE_FIXTURE /Fe:work\mod_research\auto_cache_fixture.dll /Fo:work\mod_research\auto_cache_fixture_dll.obj work\mod_research\auto_cache_pilot.cpp
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\auto_cache_fixture.exe /Fo:work\mod_research\auto_cache_fixture.obj work\mod_research\auto_cache_fixture.cpp
