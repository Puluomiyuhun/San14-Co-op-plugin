@echo off
chcp 65001 >nul
cd /d "%~dp0"
python reward_preflight.py --output "最近一次赏赐预检.json"
pause
