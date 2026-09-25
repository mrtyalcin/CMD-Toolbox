@echo off
cd /d "%~dp0"
py cmd_toolbox.py
if errorlevel 1 pause
