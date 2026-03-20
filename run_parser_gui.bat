@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "SCRIPT=%ROOT_DIR%scripts\launch_parser_gui.py"

if exist "%ROOT_DIR%.venv\Scripts\pythonw.exe" (
    start "" "%ROOT_DIR%.venv\Scripts\pythonw.exe" "%SCRIPT%"
    goto :eof
)

if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    start "" "%ROOT_DIR%.venv\Scripts\python.exe" "%SCRIPT%"
    goto :eof
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw "%SCRIPT%"
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    start "" python "%SCRIPT%"
    goto :eof
)

echo Python not found. Install Python or create .venv first.
pause
