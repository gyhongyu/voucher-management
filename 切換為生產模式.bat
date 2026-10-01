@echo off
chcp 65001 >nul
py .agent_profiles/switch_mode.py prod
pause
