@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

set "NO_PAUSE=0"
set "FORCE_REBUILD_VENV=0"
set "INSTALL_ML=0"
for %%A in (%*) do (
    if /i "%%~A"=="--no-pause" set "NO_PAUSE=1"
    if /i "%%~A"=="--rebuild-venv" set "FORCE_REBUILD_VENV=1"
    if /i "%%~A"=="--with-ml" set "INSTALL_ML=1"
)

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\install_deps.log"
echo ===== install_deps started at %date% %time% ===== > "%LOG_FILE%"

set "PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple"
set "PIP_TRUSTED_HOST=pypi.tuna.tsinghua.edu.cn"

set "PY_VERSION=3.11.9"
set "PY_ARCH=amd64"
if /i "%PROCESSOR_ARCHITECTURE%"=="x86" if not defined PROCESSOR_ARCHITEW6432 set "PY_ARCH=win32"
set "PY_INSTALLER_NAME=python-%PY_VERSION%-%PY_ARCH%.exe"
set "PY_INSTALLER_MIN_SIZE=18000000"
if /i "%PY_ARCH%"=="amd64" set "PY_INSTALLER_MIN_SIZE=24000000"

set "PY_MIRROR_URL_1=https://mirrors.ustc.edu.cn/python/%PY_VERSION%/%PY_INSTALLER_NAME%"
set "PY_MIRROR_URL_2=https://mirrors.nju.edu.cn/python/%PY_VERSION%/%PY_INSTALLER_NAME%"
set "PY_MIRROR_URL_3=https://mirrors.aliyun.com/python-release/windows/%PY_INSTALLER_NAME%"

set "RUNTIME_DIR=%~dp0.runtime\python311-%PY_ARCH%"
set "RUNTIME_PY=%RUNTIME_DIR%\python.exe"
set "DOWNLOAD_DIR=%~dp0.runtime\downloads"
set "PY_INSTALLER=%DOWNLOAD_DIR%\%PY_INSTALLER_NAME%"

echo [1/7] Locating bootstrap Python...
echo INFO: Target Python version=%PY_VERSION%, arch=%PY_ARCH%>> "%LOG_FILE%"
set "BOOTSTRAP_PY="
set "BOOTSTRAP_ARGS="
call :LOCATE_BOOTSTRAP_PY

if not defined BOOTSTRAP_PY (
    echo No usable Python found. Installing local runtime Python...
    echo No usable Python found. Installing local runtime Python...>> "%LOG_FILE%"
    call :INSTALL_LOCAL_PYTHON
    if errorlevel 1 goto :FAIL
    set "BOOTSTRAP_PY=%RUNTIME_PY%"
)

echo Using bootstrap Python: %BOOTSTRAP_PY%
echo Using bootstrap Python: %BOOTSTRAP_PY% %BOOTSTRAP_ARGS%>> "%LOG_FILE%"

set "NEED_CREATE_VENV=0"
if "%FORCE_REBUILD_VENV%"=="1" set "NEED_CREATE_VENV=1"
if exist "venv\Scripts\python.exe" (
    call "venv\Scripts\python.exe" -V >nul 2>&1
    if errorlevel 1 (
        echo WARN: Existing venv is broken and will be rebuilt.
        echo WARN: Existing venv is broken and will be rebuilt.>> "%LOG_FILE%"
        set "NEED_CREATE_VENV=1"
    )
) else (
    set "NEED_CREATE_VENV=1"
)

if "%NEED_CREATE_VENV%"=="1" (
    if exist "venv" (
        echo INFO: Removing old venv...
        echo INFO: Removing old venv...>> "%LOG_FILE%"
        rmdir /s /q "venv" >> "%LOG_FILE%" 2>&1
    )
    echo [2/7] Creating virtual environment...
    call "%BOOTSTRAP_PY%" %BOOTSTRAP_ARGS% -m venv venv >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment.
        echo ERROR: Failed to create virtual environment.>> "%LOG_FILE%"
        goto :FAIL
    )
) else (
    echo [2/7] Virtual environment is healthy.
)

set "VENV_PY=venv\Scripts\python.exe"
if not exist "%VENV_PY%" (
    echo ERROR: venv Python was not found after setup.
    echo ERROR: venv Python was not found after setup.>> "%LOG_FILE%"
    goto :FAIL
)

echo [3/7] Ensuring pip inside virtual environment...
call "%VENV_PY%" -m ensurepip --upgrade >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ERROR: ensurepip failed in virtual environment.
    echo ERROR: ensurepip failed in virtual environment.>> "%LOG_FILE%"
    goto :FAIL
)

echo [4/7] Upgrading pip/setuptools/wheel via Tsinghua mirror...
call "%VENV_PY%" -m pip install --upgrade pip setuptools wheel -i "%PIP_INDEX_URL%" --trusted-host "%PIP_TRUSTED_HOST%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ERROR: Failed to upgrade pip/setuptools/wheel.
    echo ERROR: Failed to upgrade pip/setuptools/wheel.>> "%LOG_FILE%"
    goto :FAIL
)

if not exist "requirements.txt" (
    echo ERROR: requirements.txt was not found.
    echo ERROR: requirements.txt was not found.>> "%LOG_FILE%"
    goto :FAIL
)

echo [5/7] Installing dependencies in virtual environment...
call "%VENV_PY%" -m pip install -r requirements.txt -i "%PIP_INDEX_URL%" --trusted-host "%PIP_TRUSTED_HOST%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo ERROR: Failed to install dependencies.>> "%LOG_FILE%"
    goto :FAIL
)

if "%INSTALL_ML%"=="1" (
    if not exist "requirements-ml.txt" (
        echo ERROR: requirements-ml.txt was not found.
        echo ERROR: requirements-ml.txt was not found.>> "%LOG_FILE%"
        goto :FAIL
    )
    echo Installing optional ML dependencies...
    echo Installing optional ML dependencies...>> "%LOG_FILE%"
    call "%VENV_PY%" -m pip install -r requirements-ml.txt -i "%PIP_INDEX_URL%" --trusted-host "%PIP_TRUSTED_HOST%" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        echo ERROR: Failed to install optional ML dependencies.
        echo ERROR: Failed to install optional ML dependencies.>> "%LOG_FILE%"
        goto :FAIL
    )
)

echo [6/7] Running Django check...
call "%VENV_PY%" manage.py check >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    echo WARNING: Django check returned warnings or errors.
    echo WARNING: Django check returned warnings or errors.>> "%LOG_FILE%"
) else (
    echo Django check passed.
    echo Django check passed.>> "%LOG_FILE%"
)

echo [7/7] Completed.
echo Done. You can now run start_server.bat
echo Done. You can now run start_server.bat>> "%LOG_FILE%"
echo Log file: "%LOG_FILE%"
if "%NO_PAUSE%"=="0" pause
exit /b 0

:LOCATE_BOOTSTRAP_PY
if exist "%RUNTIME_PY%" (
    set "BOOTSTRAP_PY=%RUNTIME_PY%"
    exit /b 0
)
for %%P in ("%~dp0python\python.exe" "%~dp0runtime\python\python.exe" "%~dp0tools\python\python.exe") do (
    if exist "%%~fP" (
        set "BOOTSTRAP_PY=%%~fP"
        exit /b 0
    )
)
if exist "%SystemRoot%\py.exe" (
    set "BOOTSTRAP_PY=%SystemRoot%\py.exe"
    set "BOOTSTRAP_ARGS=-3"
    exit /b 0
)
if exist "%SystemRoot%\System32\py.exe" (
    set "BOOTSTRAP_PY=%SystemRoot%\System32\py.exe"
    set "BOOTSTRAP_ARGS=-3"
    exit /b 0
)
call :FIND_PYTHON_FROM_REGISTRY
exit /b 0

:FIND_PYTHON_FROM_REGISTRY
for %%K in (
    "HKCU\Software\Python\PythonCore"
    "HKLM\Software\Python\PythonCore"
    "HKLM\Software\WOW6432Node\Python\PythonCore"
) do (
    for /f "delims=" %%S in ('reg query %%~K 2^>nul ^| findstr /r "\\[0-9][0-9]*\\.[0-9]"') do (
        for /f "tokens=2,*" %%A in ('reg query "%%S\InstallPath" /ve 2^>nul ^| find "REG_SZ"') do (
            set "PY_DIR=%%B"
            if exist "!PY_DIR!python.exe" (
                set "BOOTSTRAP_PY=!PY_DIR!python.exe"
                exit /b 0
            )
        )
    )
)
exit /b 0

:INSTALL_LOCAL_PYTHON
echo Preparing local Python runtime folder...
if not exist "%RUNTIME_DIR%" mkdir "%RUNTIME_DIR%" >> "%LOG_FILE%" 2>&1
if not exist "%DOWNLOAD_DIR%" mkdir "%DOWNLOAD_DIR%" >> "%LOG_FILE%" 2>&1

if exist "%PY_INSTALLER%" (
    call :VALIDATE_INSTALLER
    if errorlevel 1 (
        echo WARN: Existing installer is invalid. Deleting and re-downloading...
        echo WARN: Existing installer is invalid. Deleting and re-downloading...>> "%LOG_FILE%"
        del /f /q "%PY_INSTALLER%" >nul 2>&1
    )
)

if not exist "%PY_INSTALLER%" (
    echo Downloading Python installer from domestic mirrors...
    echo Downloading Python installer from domestic mirrors...>> "%LOG_FILE%"
    set "DOWNLOADED=0"
    for %%U in ("%PY_MIRROR_URL_1%" "%PY_MIRROR_URL_2%" "%PY_MIRROR_URL_3%") do (
        if "!DOWNLOADED!"=="0" (
            call :DOWNLOAD_FROM_URL "%%~U"
            if not errorlevel 1 (
                call :VALIDATE_INSTALLER
                if not errorlevel 1 (
                    set "DOWNLOADED=1"
                ) else (
                    echo WARN: Invalid installer from current mirror, trying next.
                    echo WARN: Invalid installer from current mirror, trying next.>> "%LOG_FILE%"
                    if exist "%PY_INSTALLER%" del /f /q "%PY_INSTALLER%" >nul 2>&1
                )
            )
        )
    )
    if "!DOWNLOADED!"=="0" (
        echo ERROR: Failed to download Python installer from domestic mirrors.
        echo ERROR: Failed to download Python installer from domestic mirrors.>> "%LOG_FILE%"
        exit /b 1
    )
)

call :VALIDATE_INSTALLER
if errorlevel 1 (
    echo ERROR: Final installer validation failed.
    echo ERROR: Final installer validation failed.>> "%LOG_FILE%"
    exit /b 1
)

echo Installing local Python runtime to "%RUNTIME_DIR%"...
echo Installing local Python runtime to "%RUNTIME_DIR%"...>> "%LOG_FILE%"

set "INSTALL_EXIT=0"
call :TRY_INSTALL_TARGET "%RUNTIME_DIR%"
if not errorlevel 1 (
    echo Local Python runtime installed.
    echo Local Python runtime installed.>> "%LOG_FILE%"
    exit /b 0
)

echo WARN: Install to project runtime path failed.>> "%LOG_FILE%"
if "%INSTALL_EXIT%"=="112" (
    echo WARN: Installer exit code 112 indicates possible disk space issue.>> "%LOG_FILE%"
)
call :LOG_STORAGE_HINTS

set "ALT_RUNTIME_DIR=%LOCALAPPDATA%\amusement_stats_runtime\python311-%PY_ARCH%"
if /i not "%ALT_RUNTIME_DIR%"=="%RUNTIME_DIR%" (
    echo Retrying install to user runtime path: "%ALT_RUNTIME_DIR%"
    echo INFO: Retrying install to user runtime path: "%ALT_RUNTIME_DIR%">> "%LOG_FILE%"
    call :TRY_INSTALL_TARGET "%ALT_RUNTIME_DIR%"
    if not errorlevel 1 (
        echo Local Python runtime installed (fallback path).
        echo Local Python runtime installed (fallback path).>> "%LOG_FILE%"
        exit /b 0
    )
)

echo ERROR: Local runtime Python executable was not found after install.
echo ERROR: Local runtime Python executable was not found after install.>> "%LOG_FILE%"
if not "%INSTALL_EXIT%"=="0" echo ERROR: Last installer exit code=%INSTALL_EXIT%>> "%LOG_FILE%"
exit /b 1

:TRY_INSTALL_TARGET
set "TARGET_DIR=%~1"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%" >> "%LOG_FILE%" 2>&1

set "OLD_TEMP=%TEMP%"
set "OLD_TMP=%TMP%"
set "SETUP_TEMP=%LOCALAPPDATA%\Temp\amusement_stats_pyinstaller"
if not defined LOCALAPPDATA set "SETUP_TEMP=%~dp0.runtime\tmp"
if not exist "%SETUP_TEMP%" mkdir "%SETUP_TEMP%" >> "%LOG_FILE%" 2>&1
set "TEMP=%SETUP_TEMP%"
set "TMP=%SETUP_TEMP%"
echo INFO: Installer temp dir="%SETUP_TEMP%">> "%LOG_FILE%"

call "%PY_INSTALLER%" /quiet InstallAllUsers=0 Include_pip=1 Include_launcher=0 Include_test=0 AssociateFiles=0 Shortcuts=0 PrependPath=0 TargetDir="%TARGET_DIR%" >> "%LOG_FILE%" 2>&1
set "INSTALL_EXIT=%ERRORLEVEL%"
echo INFO: Silent install exit code=%INSTALL_EXIT% (target=%TARGET_DIR%)>> "%LOG_FILE%"

if not "%INSTALL_EXIT%"=="0" if not "%INSTALL_EXIT%"=="3010" (
    echo Silent install failed (code=%INSTALL_EXIT%). Trying passive installer UI...
    echo WARN: Silent install failed (code=%INSTALL_EXIT%). Trying passive installer UI...>> "%LOG_FILE%"
    call "%PY_INSTALLER%" /passive InstallAllUsers=0 Include_pip=1 Include_launcher=0 Include_test=0 AssociateFiles=0 Shortcuts=0 PrependPath=0 TargetDir="%TARGET_DIR%" >> "%LOG_FILE%" 2>&1
    set "INSTALL_EXIT=%ERRORLEVEL%"
    echo INFO: Passive install exit code=%INSTALL_EXIT% (target=%TARGET_DIR%)>> "%LOG_FILE%"
)

set "TEMP=%OLD_TEMP%"
set "TMP=%OLD_TMP%"

if exist "%TARGET_DIR%\python.exe" (
    set "RUNTIME_DIR=%TARGET_DIR%"
    set "RUNTIME_PY=%TARGET_DIR%\python.exe"
    exit /b 0
)
exit /b 1

:LOG_STORAGE_HINTS
for /f "usebackq delims=" %%L in (`powershell -NoProfile -Command "$p='%RUNTIME_DIR%'; $d=(Get-Item $p).PSDrive.Name; $drv=Get-PSDrive -Name $d; $sys=Get-PSDrive -Name $env:SystemDrive.TrimEnd(':'); Write-Output ('DRIVE_' + $d + '_FREE_MB=' + [math]::Round($drv.Free/1MB,1)); if($sys){Write-Output ('SYSTEM_FREE_MB=' + [math]::Round($sys.Free/1MB,1))}" 2^>nul`) do (
    echo INFO: %%L>> "%LOG_FILE%"
)
exit /b 0

:DOWNLOAD_FROM_URL
set "DL_URL=%~1"
echo Trying mirror: %DL_URL%
echo Trying mirror: %DL_URL%>> "%LOG_FILE%"

curl.exe --location --retry 2 --connect-timeout 12 --max-time 180 -o "%PY_INSTALLER%" "%DL_URL%" >> "%LOG_FILE%" 2>&1
if errorlevel 1 (
    if exist "%PY_INSTALLER%" del /f /q "%PY_INSTALLER%" >nul 2>&1
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '%DL_URL%' -OutFile '%PY_INSTALLER%' -UseBasicParsing" >> "%LOG_FILE%" 2>&1
    if errorlevel 1 (
        if exist "%PY_INSTALLER%" del /f /q "%PY_INSTALLER%" >nul 2>&1
        exit /b 1
    )
)
exit /b 0

:VALIDATE_INSTALLER
if not exist "%PY_INSTALLER%" exit /b 1
for %%A in ("%PY_INSTALLER%") do set "INSTALLER_SIZE=%%~zA"
if not defined INSTALLER_SIZE set "INSTALLER_SIZE=0"
echo INFO: Installer size=%INSTALLER_SIZE% bytes>> "%LOG_FILE%"
if %INSTALLER_SIZE% LSS %PY_INSTALLER_MIN_SIZE% (
    echo ERROR: Installer too small. Expect at least %PY_INSTALLER_MIN_SIZE% bytes.>> "%LOG_FILE%"
    exit /b 1
)

set "SIG_STATUS="
set "SIG_SUBJECT="
for /f "usebackq delims=" %%L in (`powershell -NoProfile -Command "$sig=Get-AuthenticodeSignature -FilePath '%PY_INSTALLER%'; Write-Output ('STATUS=' + $sig.Status); if($sig.SignerCertificate){Write-Output ('SUBJECT=' + $sig.SignerCertificate.Subject)}" 2^>nul`) do (
    set "LINE=%%L"
    if /i "!LINE:~0,7!"=="STATUS=" set "SIG_STATUS=!LINE:~7!"
    if /i "!LINE:~0,8!"=="SUBJECT=" set "SIG_SUBJECT=!LINE:~8!"
)
echo INFO: Installer signature status=!SIG_STATUS!>> "%LOG_FILE%"
echo INFO: Installer signature subject=!SIG_SUBJECT!>> "%LOG_FILE%"
if /i not "!SIG_STATUS!"=="Valid" exit /b 1
echo !SIG_SUBJECT! | find /i "Python Software Foundation" >nul
if errorlevel 1 exit /b 1
exit /b 0

:FAIL
echo.
echo Install failed. Please check the log:
echo "%LOG_FILE%"
if "%NO_PAUSE%"=="0" pause
exit /b 1
