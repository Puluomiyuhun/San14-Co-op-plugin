@echo off
chcp 65001 >nul
cd /d "%~dp0"
python live_draft_demo.py --output "最近一次草稿传输结果.json"
pause
