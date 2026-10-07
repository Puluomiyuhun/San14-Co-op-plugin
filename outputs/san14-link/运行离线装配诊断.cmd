@echo off
chcp 65001 >nul
setlocal
title 三国志14联机 - 离线装配诊断
set "SAN14_DIAG_SCRIPT=%~dp0..\..\work\mod_research\checkpoint_offline_prototype.py"
if not exist "%SAN14_DIAG_SCRIPT%" goto missing
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%SAN14_DIAG_SCRIPT%"
set "SAN14_DIAG_EXIT=%errorlevel%"
goto finished
:python_fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%SAN14_DIAG_SCRIPT%"
set "SAN14_DIAG_EXIT=%errorlevel%"
goto finished
:missing
echo 没找到本工作区的诊断程序。请不要单独移动这个入口文件。
set "SAN14_DIAG_EXIT=2"
goto finished
:missing_python
echo 没找到 Python 3。请保留此窗口中的信息。
set "SAN14_DIAG_EXIT=2"
:finished
echo.
echo 这个入口不连接游戏，也不是可游玩的联机版。
echo 按任意键关闭窗口。
pause >nul
exit /b %SAN14_DIAG_EXIT%
