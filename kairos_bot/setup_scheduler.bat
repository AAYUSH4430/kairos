@echo off
:: Run this once as Administrator to set up the daily 9AM task
schtasks /create /tn "KAIROS Daily Prompts" /tr "%~dp0run_daily.bat" /sc daily /st 09:00 /f
echo.
echo KAIROS scheduler created — runs every day at 9:00 AM
echo Prompts will be saved to prompts_today.json
echo.
pause
