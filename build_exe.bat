@echo off
REM Build Windows Executable for Python NLP API
REM This script creates a standalone .exe that doesn't require Python installation
REM Usage: build_exe.bat

setlocal enabledelayedexpansion

echo.
echo ========================================
echo Building Python API as Windows Executable
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.9+ from https://www.python.org/
    pause
    exit /b 1
)

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [Step 1] Installing PyInstaller...
    pip install pyinstaller --upgrade
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
)

REM Check if dependencies are installed
echo [Step 2] Installing/updating dependencies from requirements.txt...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

REM Clean previous builds
echo [Step 3] Cleaning previous builds...
if exist dist rmdir /s /q dist >nul 2>&1
if exist build rmdir /s /q build >nul 2>&1
if exist *.spec del *.spec >nul 2>&1

REM Create the executable
echo [Step 4] Creating executable with PyInstaller...
echo This may take 2-3 minutes on first run...
echo.

pyinstaller ^
    --name "TalentMarketplace-API" ^
    --onefile ^
    --console ^
    --add-data "models;models" ^
    --add-data "data;data" ^
    --add-data "services;services" ^
    --hidden-import=spacy ^
    --hidden-import=flask ^
    --hidden-import=flask_cors ^
    --hidden-import=chromadb ^
    --hidden-import=sentence_transformers ^
    --hidden-import=pyodbc ^
    --paths=.

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to create executable
    echo Please check the error messages above
    pause
    exit /b 1
)

REM Verify executable was created
if not exist "dist\TalentMarketplace-API.exe" (
    echo [ERROR] Executable was not created
    pause
    exit /b 1
)

echo.
echo ========================================
echo [SUCCESS] Build completed!
echo ========================================
echo.
echo Location: dist\TalentMarketplace-API.exe
echo Size: 
for /f "tokens=5" %%A in ('dir "dist\TalentMarketplace-API.exe" ^| find "TalentMarketplace-API.exe"') do (
    echo %%A bytes
)
echo.
echo To run the API:
echo   dist\TalentMarketplace-API.exe
echo.
echo The API will be available at:
echo   http://localhost:5000
echo.

REM Optional: Copy models and data to dist folder for easier distribution
echo [Step 5] Copying models and data files...
if not exist "dist\models" mkdir dist\models
if not exist "dist\data" mkdir dist\data
xcopy /E /I /Y models dist\models >nul 2>&1
xcopy /E /I /Y data dist\data >nul 2>&1

echo.
echo [INFO] Ready for distribution!
echo The 'dist' folder contains everything needed to run the API on Windows
echo.

REM Optional: Create a startup batch file
echo [Step 6] Creating startup batch file...
(
    echo @echo off
    echo echo.
    echo echo =========================================
    echo echo TalentMarketplace NLP API
    echo echo =========================================
    echo echo.
    echo echo Starting API...
    echo echo The API will be available at:
    echo echo   http://localhost:5000
    echo echo.
    echo echo Close this window to stop the API
    echo echo.
    echo echo =========================================
    echo echo.
    echo TalentMarketplace-API.exe
    echo pause
) > "dist\Start API.bat"

echo [INFO] Created 'Start API.bat' for easy startup
echo.

pause
