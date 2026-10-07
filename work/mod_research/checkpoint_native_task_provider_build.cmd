@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars64.bat" >nul
cl /nologo /W4 /WX /EHa /std:c++17 /O2 /MT /c /Fowork\mod_research\checkpoint_native_task_provider.obj work\mod_research\checkpoint_native_task_provider.cpp
