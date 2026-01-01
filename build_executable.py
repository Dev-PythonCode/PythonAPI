#!/usr/bin/env python3
"""
Build Windows Executable for TalentMarketplace Python API
This script packages the Flask API with all dependencies into a standalone .exe file
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

class BuildExecutable:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.dist_dir = self.project_root / 'dist'
        self.build_dir = self.project_root / 'build'
        
    def log(self, level, message):
        """Print formatted log message"""
        icons = {'INFO': 'ℹ️', 'SUCCESS': '✅', 'ERROR': '❌', 'WARN': '⚠️'}
        print(f"[{level:7}] {icons.get(level, '')} {message}")
    
    def check_python(self):
        """Check if Python is installed"""
        self.log('INFO', 'Checking Python installation...')
        result = subprocess.run([sys.executable, '--version'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            self.log('SUCCESS', f"Python found: {result.stdout.strip()}")
            return True
        else:
            self.log('ERROR', 'Python not found or not in PATH')
            return False
    
    def check_pyinstaller(self):
        """Check and install PyInstaller if needed"""
        self.log('INFO', 'Checking PyInstaller...')
        result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'pyinstaller'],
                              capture_output=True)
        if result.returncode != 0:
            self.log('INFO', 'PyInstaller not found, installing...')
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller', '--upgrade'],
                         check=True)
        self.log('SUCCESS', 'PyInstaller ready')
        return True
    
    def install_dependencies(self):
        """Install dependencies from requirements.txt"""
        self.log('INFO', 'Installing dependencies from requirements.txt...')
        req_file = self.project_root / 'requirements.txt'
        if not req_file.exists():
            self.log('ERROR', f'requirements.txt not found at {req_file}')
            return False
        
        result = subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', str(req_file)],
                              cwd=str(self.project_root))
        if result.returncode == 0:
            self.log('SUCCESS', 'Dependencies installed')
            return True
        else:
            self.log('ERROR', 'Failed to install dependencies')
            return False
    
    def clean_builds(self):
        """Clean previous build artifacts"""
        self.log('INFO', 'Cleaning previous builds...')
        if self.dist_dir.exists():
            shutil.rmtree(self.dist_dir)
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        # Remove .spec files
        for spec_file in self.project_root.glob('*.spec'):
            spec_file.unlink()
        
        self.log('SUCCESS', 'Cleaned old builds')
    
    def build_executable(self):
        """Build the executable using PyInstaller"""
        self.log('INFO', 'Building executable with PyInstaller...')
        self.log('INFO', 'This may take 2-3 minutes on first run...')
        
        app_file = self.project_root / 'app.py'
        if not app_file.exists():
            self.log('ERROR', f'app.py not found at {app_file}')
            return False
        
        # PyInstaller command
        cmd = [
            sys.executable, '-m', 'PyInstaller',
            '--name', 'TalentMarketplace-API',
            '--onefile',
            '--console',
            '--add-data', f'models{os.pathsep}models',
            '--add-data', f'data{os.pathsep}data',
            '--add-data', f'services{os.pathsep}services',
            '--hidden-import=spacy',
            '--hidden-import=flask',
            '--hidden-import=flask_cors',
            '--hidden-import=chromadb',
            '--hidden-import=sentence_transformers',
            '--hidden-import=pyodbc',
            '--distpath', str(self.dist_dir),
            '--buildpath', str(self.build_dir),
            str(app_file)
        ]
        
        result = subprocess.run(cmd, cwd=str(self.project_root))
        
        if result.returncode != 0:
            self.log('ERROR', 'Failed to create executable')
            return False
        
        self.log('SUCCESS', 'Executable created')
        return True
    
    def verify_executable(self):
        """Verify the executable was created"""
        exe_path = self.dist_dir / 'TalentMarketplace-API.exe'
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            self.log('SUCCESS', f'Executable verified: {size_mb:.1f} MB')
            return True
        else:
            self.log('ERROR', 'Executable not found')
            return False
    
    def copy_assets(self):
        """Copy models and data to dist folder"""
        self.log('INFO', 'Copying models and data files...')
        
        models_src = self.project_root / 'models'
        models_dst = self.dist_dir / 'models'
        if models_src.exists() and not models_dst.exists():
            shutil.copytree(models_src, models_dst)
        
        data_src = self.project_root / 'data'
        data_dst = self.dist_dir / 'data'
        if data_src.exists() and not data_dst.exists():
            shutil.copytree(data_src, data_dst)
        
        self.log('SUCCESS', 'Assets copied')
    
    def create_startup_script(self):
        """Create a batch file for easy startup"""
        self.log('INFO', 'Creating startup batch file...')
        
        batch_content = '''@echo off
echo.
echo =========================================
echo TalentMarketplace NLP API
echo =========================================
echo.
echo Starting API...
echo The API will be available at:
echo   http://localhost:5000
echo.
echo Close this window to stop the API
echo.
echo =========================================
echo.
TalentMarketplace-API.exe
pause
'''
        
        batch_file = self.dist_dir / 'Start API.bat'
        batch_file.write_text(batch_content)
        self.log('SUCCESS', 'Created Start API.bat')
    
    def create_readme(self):
        """Create a README for distribution"""
        self.log('INFO', 'Creating README...')
        
        readme_content = '''# TalentMarketplace Python NLP API - Standalone Executable

## Quick Start

1. Double-click "Start API.bat" to launch the API
2. Wait for the message "Running on http://localhost:5000"
3. The API is now ready to receive requests

## Requirements

- Windows 7 SP1 or later
- 2GB RAM minimum (4GB recommended)
- No Python installation required

## API Documentation

The API runs on: http://localhost:5000

Main endpoints:
- POST /api/parse-query - Parse natural language queries
- GET /health - Check API status

## Default Configuration

- Port: 5000
- Host: 0.0.0.0 (accessible from other machines)
- Timeout: 30 seconds per request

## Troubleshooting

### Issue: "Port 5000 is already in use"
Solution: Close other applications using port 5000, or modify the port in config.ini

### Issue: Slow on first startup
This is normal. The API loads the NLP model on first request (takes 2-5 seconds).
Subsequent requests are much faster.

### Issue: API not responding
Check that:
1. The executable is still running (check taskbar)
2. Your firewall allows connections to port 5000
3. You're using the correct URL: http://localhost:5000

## Performance Tips

- First request: 2-5 seconds (model loading)
- Subsequent requests: <500ms
- Keep the window open while using the API
- For production use, consider running as Windows Service (advanced setup)

## Updating

To update the API:
1. Close the current API window
2. Delete the old TalentMarketplace-API folder
3. Extract the new version
4. Run Start API.bat

## Support

For issues or questions, check the documentation or contact support.

---
Generated from TalentMarketplace Python API
'''
        
        readme_file = self.dist_dir / 'README.txt'
        readme_file.write_text(readme_content)
        self.log('SUCCESS', 'Created README.txt')
    
    def build(self):
        """Execute the full build process"""
        print('\n' + '='*50)
        print('TalentMarketplace Python API - Build Executable')
        print('='*50 + '\n')
        
        steps = [
            ('Python Check', self.check_python),
            ('PyInstaller Check', self.check_pyinstaller),
            ('Install Dependencies', self.install_dependencies),
            ('Clean Old Builds', self.clean_builds),
            ('Build Executable', self.build_executable),
            ('Verify Executable', self.verify_executable),
            ('Copy Assets', self.copy_assets),
            ('Create Startup Script', self.create_startup_script),
            ('Create Documentation', self.create_readme),
        ]
        
        for step_name, step_func in steps:
            try:
                if not step_func():
                    self.log('ERROR', f'{step_name} failed')
                    return False
            except Exception as e:
                self.log('ERROR', f'{step_name} raised exception: {e}')
                return False
        
        print('\n' + '='*50)
        print('✅ BUILD SUCCESSFUL!')
        print('='*50)
        print(f'\nLocation: {self.dist_dir}')
        print(f'\nTo run the API:')
        print(f'  Double-click: dist\\Start API.bat')
        print(f'  Or directly: dist\\TalentMarketplace-API.exe')
        print(f'\nThe API will be available at:')
        print(f'  http://localhost:5000')
        print(f'\nReady for distribution!\n')
        
        return True

if __name__ == '__main__':
    builder = BuildExecutable()
    success = builder.build()
    sys.exit(0 if success else 1)
