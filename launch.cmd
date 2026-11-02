@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Run setup.ps1 first to create the Python environment.
 exit /b 1
)
".venv\Scripts\python.exe" main.py
