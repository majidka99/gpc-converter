@echo off
REM Build script for GPC Converter Windows executable
REM Requires: pip install pyinstaller

echo === Building GPC Converter ===

REM Check if PyInstaller is installed
pyinstaller --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PyInstaller is not installed.
    echo Install it with: pip install pyinstaller
    pause
    exit /b 1
)

REM Clean previous builds
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist
if exist "GPC Converter" rmdir /s /q "GPC Converter"

echo [1/2] Building executable with PyInstaller...
pyinstaller gpc_converter_gui.spec --clean

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! Check output above.
    pause
    exit /b 1
)

echo.
echo [2/2] Creating installer...

REM Copy additional files to dist folder
copy README.md "dist\GPC Converter\" >nul 2>&1
copy convert_to_gpc.py "dist\GPC Converter\" >nul 2>&1

echo.
echo ========================================
echo Build complete! Executable is in:
echo   dist\GPC Converter\GPC Converter.exe
echo ========================================
echo.
echo Optional: Use Inno Setup or NSIS to create an .msi installer.
echo.
pause
