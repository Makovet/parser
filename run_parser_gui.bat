@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "SCRIPT=%ROOT_DIR%scripts\launch_parser_gui.py"

if not exist "%SCRIPT%" (
    echo GUI launcher not found:
    echo %SCRIPT%
    pause
    exit /b 1
)

if exist "%ROOT_DIR%.venv\Scripts\pythonw.exe" (
    call :run_with "%ROOT_DIR%.venv\Scripts\pythonw.exe"
    goto :eof
)

if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    call :run_with "%ROOT_DIR%.venv\Scripts\python.exe"
    goto :eof
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    call :run_with pythonw
    goto :eof
)

where python >nul 2>nul
if %errorlevel%==0 (
    call :run_with python
    goto :eof
)

echo Python not found. Install Python or create .venv first.
pause
exit /b 1

:run_with
%~1 "%SCRIPT%"
if errorlevel 1 (
    echo Launcher exited with an error.
    pause
    exit /b 1
)
exit /b 0
