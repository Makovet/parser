@echo off
setlocal

set "ROOT_DIR=%~dp0"
set "SCRIPT=%ROOT_DIR%scripts\launch_parser_gui.py"

if not exist "%SCRIPT%" (
    echo Launcher script not found: %SCRIPT%
    pause
    exit /b 1
)

if exist "%ROOT_DIR%.venv\Scripts\pythonw.exe" (
    "%ROOT_DIR%.venv\Scripts\pythonw.exe" "%SCRIPT%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :handle_exit
)

if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    "%ROOT_DIR%.venv\Scripts\python.exe" "%SCRIPT%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :handle_exit
)

where pythonw >nul 2>nul
if %errorlevel%==0 (
    pythonw "%SCRIPT%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :handle_exit
)

where python >nul 2>nul
if %errorlevel%==0 (
    python "%SCRIPT%"
    set "EXIT_CODE=%ERRORLEVEL%"
    goto :handle_exit
)

echo Python not found. Checked .venv\Scripts\pythonw.exe, .venv\Scripts\python.exe, pythonw, python.
pause
exit /b 1

:handle_exit
if not "%EXIT_CODE%"=="0" (
    echo Launcher exited with error code %EXIT_CODE%.
    pause
)
exit /b %EXIT_CODE%
