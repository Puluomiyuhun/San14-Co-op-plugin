@echo off
chcp 65001 >nul
cd /d "%~dp0"
python sortie_reader.py --output "最近一次出征草稿.json"
pause
