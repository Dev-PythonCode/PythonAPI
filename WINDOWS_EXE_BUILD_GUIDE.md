# Python API - Windows Executable Setup Guide

## Overview
This guide explains how to create a standalone Windows executable (.exe) for the Python NLP API that can run without requiring Python installation or package management.

## Method: Using PyInstaller

### Prerequisites
- Python 3.9+ installed on Windows
- PyInstaller package

### Step 1: Install PyInstaller
```bash
pip install pyinstaller
```

### Step 2: Install All Dependencies
```bash
cd /path/to/PythonAPI
pip install -r requirements.txt
```

### Step 3: Create the Executable

Create a file called `build_exe.bat` in the PythonAPI directory:

```batch
@echo off
REM Build Windows Executable for Python NLP API
REM This script creates a standalone .exe that doesn't require Python installation

echo.
echo ========================================
echo Building Python API as Windows Executable
echo ========================================
echo.

REM Clean previous builds
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build
if exist *.spec del *.spec

REM Create the executable
echo [Step 1] Creating executable with PyInstaller...
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
    --icon=app_icon.ico ^
    --paths=%CD%\services ^
    app.py

if errorlevel 1 (
    echo [ERROR] Failed to create executable
    pause
    exit /b 1
)

echo [Step 2] Build completed successfully!
echo.
echo ========================================
echo Executable created at: dist\TalentMarketplace-API.exe
echo ========================================
echo.
echo Usage: dist\TalentMarketplace-API.exe
echo The API will run on http://localhost:5000
echo.
pause
```

### Step 4: Run the Build Script
```bash
cd PythonAPI
build_exe.bat
```

The executable will be created in the `dist` folder.

## Alternative Method: Using cx_Freeze (Better for Complex Apps)

For more complex packaging with proper dependencies, use cx_Freeze:

### Setup File (setup_cx_freeze.py)
```python
from cx_Freeze import setup, Executable
import sys

# Add the modules path
sys.path.insert(0, 'C:\\path\\to\\PythonAPI')

includes = [
    'flask',
    'flask_cors',
    'spacy',
    'chromadb',
    'sentence_transformers',
    'pyodbc',
    'services.query_parser',
    'services.resume_parser',
    'services.skill_normalizer',
]

options = {
    'build_exe': {
        'includes': includes,
        'include_files': [
            ('models', 'models'),
            ('data', 'data'),
            ('services', 'services'),
        ],
        'optimize': 2,
    }
}

executables = [
    Executable(
        'app.py',
        base='Console',
        target_name='TalentMarketplace-API.exe'
    )
]

setup(
    name='TalentMarketplace-API',
    version='1.0.0',
    description='NLP API for Talent Marketplace',
    options=options,
    executables=executables
)
```

### Build Command
```bash
python setup_cx_freeze.py build
```

## Running the Executable

### From Command Line
```bash
dist\TalentMarketplace-API.exe
```

### From Windows Start Menu (Optional)
Create a batch file that users can double-click:

```batch
@echo off
echo Starting TalentMarketplace API...
echo.
echo API will be available at: http://localhost:5000
echo.
TalentMarketplace-API.exe
pause
```

## Distributing the Executable

### Package Contents
Create a distribution folder with:
```
TalentMarketplace-API/
├── TalentMarketplace-API.exe
├── models/
│   └── talent_ner_model/
├── data/
│   ├── skills.json
│   ├── tech_dict_with_categories.json
│   ├── normalization_map.json
│   └── ...
├── README.txt
├── Start API.bat
└── config.ini
```

### CreateZip Archive
```bash
# Using PowerShell
Compress-Archive -Path "TalentMarketplace-API" -DestinationPath "TalentMarketplace-API-v1.0.zip"
```

## System Requirements

### Minimum
- Windows 7 SP1 or later
- 2GB RAM
- 500MB disk space (for models)

### Recommended
- Windows 10 or later
- 4GB+ RAM
- 1GB disk space
- SSD for faster model loading

## Troubleshooting

### Issue: "Module not found" error
**Solution**: Add the missing module to the `--hidden-import` flag in PyInstaller command

### Issue: Large executable size (500MB+)
**Solution**: The size is normal because it includes Python interpreter and all packages. This is expected with PyInstaller.

### Issue: Anti-virus warns about executable
**Solution**: This is common with PyInstaller executables. Users can verify the file hash or source.

### Issue: Performance is slow on first run
**Solution**: The NLP model loads on first request. Subsequent requests are much faster. Typical first request: 2-5 seconds.

## Performance Optimization

### For Distribution
1. Pre-load the model:
   Add to `app.py` startup:
   ```python
   @app.before_request
   def load_model():
       if not hasattr(g, 'nlp_loaded'):
           app.logger.info("Pre-loading NLP model...")
           from services.query_parser import QueryParser
           qp = QueryParser()
           g.nlp_loaded = True
   ```

2. Use UPX to compress the executable:
   ```bash
   upx --best --lzma dist\TalentMarketplace-API.exe
   ```
   This can reduce size by 40-50%

## User Installation Instructions

For end users:

1. Download `TalentMarketplace-API-v1.0.zip`
2. Extract to desired location (e.g., `C:\Program Files\TalentMarketplace-API\`)
3. Double-click `Start API.bat`
4. Wait for message: "Running on http://localhost:5000"
5. Open browser to `http://localhost:5000`
6. The .NET Blazor app can now connect to the API

## Building Without PyInstaller (Using py2exe)

Alternative approach using py2exe:

```python
from distutils.core import setup
import py2exe

setup(
    name='TalentMarketplace-API',
    version='1.0.0',
    console=['app.py'],
    data_files=[
        ('models', ['models']),
        ('data', ['data']),
    ],
)
```

Build: `python setup.py py2exe`

## Notes
- The executable size (~300-500MB) is normal for Python apps with all dependencies
- First run takes longer (model loading)
- Network access to `http://localhost:5000` is required from the .NET app
- The executable is single-file and self-contained
