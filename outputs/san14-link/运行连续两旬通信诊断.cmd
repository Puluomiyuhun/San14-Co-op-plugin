@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
title 三国志14联机 - 连续两旬通信诊断
set "SAN14_CONNECTED_SCRIPT=%~dp0..\..\work\mod_research\checkpoint_room_lifecycle_test.py"
if not exist "%SAN14_CONNECTED_SCRIPT%" goto missing
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3 "%SAN14_CONNECTED_SCRIPT%"
set "SAN14_CONNECTED_EXIT=%errorlevel%"
goto finished
:python_fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%SAN14_CONNECTED_SCRIPT%"
set "SAN14_CONNECTED_EXIT=%errorlevel%"
goto finished
:missing
echo 找不到本工作区程序。请不要单独移动这个入口文件。
set "SAN14_CONNECTED_EXIT=2"
goto finished
:missing_python
echo 没找到 Python 3，请保留窗口中的信息。
set "SAN14_CONNECTED_EXIT=2"
:finished
echo.
echo 只运行本机测试房间和测试进程，不连接游戏，不修改游戏存档。
echo 这不是可游玩的联机版。按任意键关闭窗口。
pause >nul
exit /b %SAN14_CONNECTED_EXIT%
