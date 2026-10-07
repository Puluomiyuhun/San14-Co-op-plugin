@echo off
chcp 65001 >nul
cd /d "%~dp0"
python domestic_reader.py --output "最近一次内政草稿.json"
pause
