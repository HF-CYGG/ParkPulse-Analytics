@echo off
setlocal
cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\start_server.log"
echo ===== start_server started at %date% %time% ===== > "%LOG_FILE%"

if not exist "venv\Scripts\python.exe" (
    echo Virtual environment not found. Running install_deps.bat...
    echo INFO: Virtual environment not found. Running install_deps.bat...>> "%LOG_FILE%"
    call "%~dp0install_deps.bat" --no-pause
    if errorlevel 1 (
        echo ERROR: install_deps.bat failed.
        echo ERROR: install_deps.bat failed.>> "%LOG_FILE%"
        goto :FAIL
    )
)

set "VENV_PY=venv\Scripts\python.exe"
call "%VENV_PY%" -V >nul 2>&1
if errorlevel 1 (
    echo WARN: venv is broken. Rebuilding...
    echo WARN: venv is broken. Rebuilding...>> "%LOG_FILE%"
    call "%~dp0install_deps.bat" --no-pause --rebuild-venv
    if errorlevel 1 (
        echo ERROR: install_deps.bat rebuild failed.
        echo ERROR: install_deps.bat rebuild failed.>> "%LOG_FILE%"
        goto :FAIL
    )
)

echo Running database migrations...
call "%VENV_PY%" manage.py migrate >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ERROR: Migration failed.
    echo ERROR: Migration failed.>> "%LOG_FILE%"
    goto :FAIL
)

echo Starting Django server at http://127.0.0.1:8000/
echo INFO: Starting Django server at http://127.0.0.1:8000/>> "%LOG_FILE%"
call "%VENV_PY%" manage.py runserver 127.0.0.1:8000 >> "%LOG_FILE%" 2>&1

endlocal
exit /b 0

:FAIL
echo.
echo Start failed. Please check the log:
echo "%LOG_FILE%"
pause
exit /b 1
