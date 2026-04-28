@echo off
REM Build script for GPC Converter Windows executable (single-file portable)
REM Requires: pip install pyinstaller

echo === Building GPC Converter (Single-File Portable) ===

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
if exist "GPC Converter.exe" del /f /q "GPC Converter.exe" 2>nul

echo [1/2] Building single-file executable with PyInstaller...
pyinstaller gpc_converter_gui.spec --clean --noconfirm --onefile

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed! Check output above.
    pause
    exit /b 1
)

echo.
echo [2/2] Creating ZIP archive...

REM Ensure dist folder exists
if not exist "dist" mkdir dist

REM Copy the single exe to a temp folder for zipping
mkdir "temp_zip" 2>nul
copy "dist\GPC Converter.exe" "temp_zip\" >nul

REM Create ZIP with just the exe
powershell -Command "Compress-Archive -Path 'temp_zip\*' -DestinationPath 'GPC_Converter_Windows.zip' -Force"

REM Cleanup temp folder
rmdir /s /q temp_zip

echo.
echo ========================================
echo Build complete! Portable executable:
echo   dist\GPC Converter.exe
echo Archive: GPC_Converter_Windows.zip
echo ========================================
echo.
echo Optional: Use Inno Setup to create an .msi installer:
echo   gpc_converter.iss
echo.
pause
