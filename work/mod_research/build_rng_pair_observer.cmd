@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\observe_rng_pairs.exe /Fo:work\mod_research\observe_rng_pairs.obj work\mod_research\observe_rng_pairs.cpp
if errorlevel 1 exit /b 1
ml64 /nologo /c /Fo work\mod_research\rng_pair_bridges.obj work\mod_research\rng_route_fixture_bridges.asm
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\rng_pair_target_fixture.exe /Fo:work\mod_research\rng_pair_target_fixture.obj work\mod_research\rng_pair_target_fixture.cpp work\mod_research\rng_pair_bridges.obj
if errorlevel 1 exit /b 1
cl /nologo /W4 /WX /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\rng_pair_payload_fixture.exe /Fo:work\mod_research\rng_pair_payload_fixture.obj work\mod_research\rng_pair_payload_fixture.cpp
