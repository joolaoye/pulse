@echo off

where py >nul 2>nul

if %ERRORLEVEL% EQU 0 (
    py -3 "%~dp0bootstrap.py"
    exit /b %ERRORLEVEL%
)

where python >nul 2>nul

if %ERRORLEVEL% EQU 0 (
    python "%~dp0bootstrap.py"
    exit /b %ERRORLEVEL%
)

echo Python is required to bootstrap Pulse.
exit /b 1
