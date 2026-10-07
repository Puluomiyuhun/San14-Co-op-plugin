@echo off
chcp 65001 >nul
setlocal
set "PYTHONUTF8=1"
title 三国志14联机 - 输入检查接入离线诊断
set "SAN14_ADMITTED_SCRIPT=%~dp0..\..\work\mod_research\checkpoint_admitted_connected_prototype.py"
if not exist "%SAN14_ADMITTED_SCRIPT%" goto missing
where py >nul 2>nul
if errorlevel 1 goto fallback
py -3 "%SAN14_ADMITTED_SCRIPT%"
set "SAN14_ADMITTED_EXIT=%errorlevel%"
goto finished
:fallback
where python >nul 2>nul
if errorlevel 1 goto missing_python
python "%SAN14_ADMITTED_SCRIPT%"
set "SAN14_ADMITTED_EXIT=%errorlevel%"
goto finished
:missing
echo 找不到本工作区程序，请不要单独移动此入口。
set "SAN14_ADMITTED_EXIT=2"
goto finished
:missing_python
echo 没找到 Python 3，请保留错误信息。
set "SAN14_ADMITTED_EXIT=2"
:finished
echo.
echo 本程序只运行本机房间和自建测试进程，不连接游戏，不修改游戏存档。
echo 成功后仍等待完整世界与真实游戏接入，不是可玩的联机版。
pause >nul
exit /b %SAN14_ADMITTED_EXIT%
