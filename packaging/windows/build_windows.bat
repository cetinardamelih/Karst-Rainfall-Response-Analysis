@echo off
setlocal EnableExtensions

cd /d "%~dp0\..\.."

set "APP_NAME=Karst Rainfall-Response Analysis"
set "ENTRY=packaging\windows\launcher.py"
set "DIST_DIR=dist\%APP_NAME%"
set "EXE_PATH=%DIST_DIR%\%APP_NAME%.exe"
set "INTERNAL_DIR=%DIST_DIR%\_internal"
set "BASE_LIBRARY=%INTERNAL_DIR%\base_library.zip"
set "INSTALLER_PATH=dist\installer\setup.exe"
set "PYTHON_EXE=.venv\Scripts\python.exe"

echo ============================================================
echo Windows build for %APP_NAME%
echo ============================================================
echo Project root: %CD%
echo.

if not exist "app\streamlit_app.py" (
  echo ERROR: app\streamlit_app.py was not found.
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo Creating local build virtual environment...
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    where python >nul 2>nul
    if errorlevel 1 (
      echo ERROR: Python was not found on PATH.
      exit /b 1
    )
    python -m venv .venv
  )
  if errorlevel 1 (
    echo ERROR: Could not create .venv.
    exit /b 1
  )
)

if not exist "%PYTHON_EXE%" (
  echo ERROR: %PYTHON_EXE% was not found.
  exit /b 1
)

echo Installing build requirements...
"%PYTHON_EXE%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  echo ERROR: pip bootstrap failed.
  exit /b 1
)

"%PYTHON_EXE%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo ERROR: pip install failed.
  exit /b 1
)

"%PYTHON_EXE%" -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
  echo ERROR: PyInstaller was not found after installing requirements.
  exit /b 1
)

echo Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
for /d /r %%D in (__pycache__) do (
  if exist "%%D" rmdir /s /q "%%D"
)

echo Running PyInstaller onedir build...
"%PYTHON_EXE%" -m PyInstaller ^
  --name "%APP_NAME%" ^
  --onedir ^
  --noconsole ^
  --clean ^
  --distpath "dist" ^
  --workpath "build\pyinstaller" ^
  --specpath "build\spec" ^
  --add-data "%CD%\app;app" ^
  --add-data "%CD%\config;config" ^
  --add-data "%CD%\src;src" ^
  --add-data "%CD%\data\sample;data\sample" ^
  --collect-all yaml ^
  --collect-all streamlit ^
  --collect-all altair ^
  --collect-all pyarrow ^
  --collect-all pandas ^
  --collect-all numpy ^
  --collect-all scipy ^
  --collect-all matplotlib ^
  --collect-all plotly ^
  --collect-all watchdog ^
  --collect-all blinker ^
  --collect-all cachetools ^
  --collect-all click ^
  --collect-all packaging ^
  --collect-all protobuf ^
  --collect-all requests ^
  --collect-all pydeck ^
  --collect-all jinja2 ^
  --collect-all jsonschema ^
  --collect-all starlette ^
  --collect-all uvicorn ^
  --collect-all tenacity ^
  --collect-all typing_extensions ^
  --collect-all setuptools ^
  --copy-metadata streamlit ^
  --copy-metadata altair ^
  --copy-metadata pyarrow ^
  --copy-metadata pandas ^
  --copy-metadata numpy ^
  --copy-metadata scipy ^
  --copy-metadata matplotlib ^
  --copy-metadata plotly ^
  --copy-metadata watchdog ^
  --copy-metadata blinker ^
  --copy-metadata cachetools ^
  --copy-metadata click ^
  --copy-metadata packaging ^
  --copy-metadata protobuf ^
  --copy-metadata requests ^
  --copy-metadata pydeck ^
  --copy-metadata jinja2 ^
  --copy-metadata jsonschema ^
  --copy-metadata starlette ^
  --copy-metadata uvicorn ^
  --copy-metadata tenacity ^
  --copy-metadata typing_extensions ^
  --hidden-import streamlit.web.bootstrap ^
  --hidden-import streamlit.web.cli ^
  --hidden-import streamlit.runtime.scriptrunner ^
  --hidden-import watchdog.observers ^
  "%ENTRY%"

if errorlevel 1 (
  echo ERROR: PyInstaller build failed.
  exit /b 1
)

if not exist "%EXE_PATH%" (
  echo ERROR: Expected exe was not created:
  echo %EXE_PATH%
  exit /b 1
)

if not exist "%INTERNAL_DIR%\python*.dll" (
  echo ERROR: Embedded Python DLL was not found:
  echo %INTERNAL_DIR%\python*.dll
  exit /b 1
)

if not exist "%BASE_LIBRARY%" (
  echo ERROR: base_library.zip was not found:
  echo %BASE_LIBRARY%
  exit /b 1
)

if /I "%SKIP_INNO%"=="1" (
  echo.
  echo SKIP_INNO=1 was set; setup.exe compilation skipped.
  goto build_done
)

set "ISCC_EXE="
for /f "delims=" %%P in ('where iscc 2^>nul') do (
  if not defined ISCC_EXE set "ISCC_EXE=%%P"
)
if not defined ISCC_EXE if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_EXE if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_EXE=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC_EXE (
  echo ERROR: Inno Setup Compiler was not found.
  echo Install Inno Setup 6, then run this file again:
  echo https://jrsoftware.org/isinfo.php
  exit /b 1
)

echo Compiling setup.exe with Inno Setup...
"%ISCC_EXE%" "packaging\windows\installer.iss"
if errorlevel 1 (
  echo ERROR: Inno Setup compilation failed.
  exit /b 1
)

if not exist "%INSTALLER_PATH%" (
  echo ERROR: Expected installer was not created:
  echo %INSTALLER_PATH%
  exit /b 1
)

:build_done
echo.
echo SUCCESS: Windows build completed.
echo Exe:
echo %CD%\%EXE_PATH%
echo.
if exist "%INSTALLER_PATH%" (
  echo Installer:
  echo %CD%\%INSTALLER_PATH%
) else (
  echo Installer was not created because Inno Setup was skipped.
)
echo.
echo Test the installed app from the Desktop or Start Menu shortcut.

endlocal
