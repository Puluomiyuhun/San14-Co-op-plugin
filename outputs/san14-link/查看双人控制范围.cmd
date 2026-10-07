@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 human_control_reader.py --forces 12 2 --output "双人控制范围含编组预览.json"
pause
