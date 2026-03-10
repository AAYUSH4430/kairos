@echo off
cd /d "%~dp0"
python export_prompts.py >> kairos.log 2>&1
