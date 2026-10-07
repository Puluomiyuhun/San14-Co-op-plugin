@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 authority_reward.py --forces 12 2 --output "双方赏赐预检.json"
pause
