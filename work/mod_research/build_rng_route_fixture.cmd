@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MD /LD /Fe:work\mod_research\rng_route_fixture.dll /Fo:work\mod_research\rng_route_fixture_dll.obj work\mod_research\rng_route_fixture_dll.cpp /link /IMPLIB:work\mod_research\rng_route_fixture.lib
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo work\mod_research\rng_route_fixture_bridges.obj work\mod_research\rng_route_fixture_bridges.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MD /Fe:work\mod_research\rng_route_dll_fixture.exe /Fo:work\mod_research\rng_route_dll_fixture.obj work\mod_research\rng_route_dll_fixture.cpp work\mod_research\rng_route_fixture_bridges.obj
