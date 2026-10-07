@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /Fe:work\mod_research\reward_container_probe.dll /Fo:work\mod_research\reward_container_probe.obj work\mod_research\reward_container_probe.cpp /link /IMPLIB:work\mod_research\reward_container_probe.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /LD /D REWARD_FIXTURE /Fe:work\mod_research\reward_container_fixture.dll /Fo:work\mod_research\reward_container_fixture_dll.obj work\mod_research\reward_container_probe.cpp /link /IMPLIB:work\mod_research\reward_container_fixture.lib
if errorlevel 1 exit /b 1
cl /nologo /W4 /EHsc /std:c++17 /O2 /MT /Fe:work\mod_research\reward_container_fixture.exe /Fo:work\mod_research\reward_container_fixture.obj work\mod_research\reward_container_fixture.cpp
