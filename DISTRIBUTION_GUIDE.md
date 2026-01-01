# Python API Distribution & Windows Executable Guide

## Quick Start for Building

### Option 1: Using Batch Script (Windows Only)
1. Open Command Prompt in the PythonAPI directory
2. Run: `build_exe.bat`
3. Wait for completion (~2-3 minutes)
4. Find the executable in `dist\TalentMarketplace-API.exe`

### Option 2: Using Python Script (Cross-platform)
```bash
python build_executable.py
```

## What Gets Built

The Windows executable package includes:
```
dist/
├── TalentMarketplace-API.exe          # Main executable
├── Start API.bat                       # Launch script
├── README.txt                          # User guide
├── models/                             # NLP model (required)
│   └── talent_ner_model/
│       ├── ner/
│       ├── tok2vec/
│       └── vocab/
└── data/                               # Training data (required)
    ├── skills.json
    ├── normalization_map.json
    ├── tech_dict_with_categories.json
    └── ...
```

## File Sizes (Approximate)

| Component | Size |
|-----------|------|
| Executable (.exe) | 250-350 MB |
| Models folder | 100-150 MB |
| Data folder | 5-10 MB |
| **Total** | **~400-500 MB** |

The large executable size includes Python interpreter + all packages. This is normal and expected.

## Distribution Package

### Option A: Full Standalone (Recommended)
**Package everything together:**

1. Create distribution folder:
   ```bash
   mkdir TalentMarketplace-API-v1.0
   xcopy dist\* TalentMarketplace-API-v1.0\ /E
   ```

2. Create ZIP archive:
   ```bash
   # PowerShell
   Compress-Archive -Path "TalentMarketplace-API-v1.0" -DestinationPath "TalentMarketplace-API-v1.0.zip"
   ```

3. Archive size: ~400-500 MB
4. Users extract and run: `Start API.bat`

### Option B: Installer Package
Create a proper Windows installer using NSIS:

1. Install NSIS (Nullsoft Scriptable Install System)
2. Create installer script (`installer.nsi`)
3. Generate `.exe` installer
4. Easier distribution and uninstallation

See `NSIS_INSTALLER_GUIDE.md` for details.

## User Installation Instructions

### For End Users:

**Step 1: Download**
- Download `TalentMarketplace-API-v1.0.zip` from your distribution point

**Step 2: Extract**
- Extract to desired location:
  - `C:\Program Files\TalentMarketplace-API\` (recommended)
  - `C:\Users\YourName\AppData\Local\TalentMarketplace-API\`
  - Or any accessible folder

**Step 3: Run**
- Double-click `Start API.bat`
- You should see:
  ```
  Running on http://localhost:5000
  ```

**Step 4: Test**
- Open browser: `http://localhost:5000`
- You should see API response

**Step 5: Keep Running**
- Keep the command window open while using the API
- Close it to stop the API

## System Requirements

### Minimum
- Windows 7 SP1 or later
- 2 GB RAM
- 500 MB disk space
- .NET Framework 3.5+ (already included in Windows)

### Recommended
- Windows 10 or later
- 4 GB RAM
- 1 GB SSD space (faster model loading)
- Modern processor (Intel Core i5+ or AMD Ryzen 5+)

## Pre-built Binary Distribution

To provide pre-built binaries without requiring build tools:

1. **Build the executable** on a Windows machine:
   ```bash
   build_exe.bat
   ```

2. **Create distribution package:**
   ```bash
   mkdir dist-final
   xcopy dist\* dist-final\ /E
   copy config.ini dist-final\
   copy LICENSE dist-final\
   copy README.md dist-final\README_DEVELOPER.md
   ```

3. **Test thoroughly** on clean Windows system

4. **Create ZIP for distribution:**
   ```bash
   Compress-Archive -Path "dist-final" -DestinationPath "TalentMarketplace-API-Windows.zip"
   ```

5. **Host for download:**
   - GitHub Releases
   - Company server
   - S3/Cloud storage

## Verification Checklist

After building, verify:

- [ ] `TalentMarketplace-API.exe` exists and is executable
- [ ] Size is ~250-350 MB
- [ ] `models/` folder contains `talent_ner_model/`
- [ ] `data/` folder contains `.json` files
- [ ] `Start API.bat` is present
- [ ] `README.txt` is present
- [ ] File structure matches above diagram

## Testing the Build

### Quick Test
```bash
dist\TalentMarketplace-API.exe
```

Should output:
```
 * Running on http://0.0.0.0:5000
 * Press CTRL+C to quit
```

### API Test
Open new command prompt:
```bash
curl http://localhost:5000/health
```

Should return:
```json
{"status": "healthy"}
```

## Troubleshooting Build Issues

### Issue: "Module not found: spacy"
**Solution:** Run `pip install spacy` separately, then rebuild

### Issue: "PyInstaller not found"
**Solution:** Run `pip install pyinstaller` first

### Issue: Build takes very long (>10 minutes)
**Solution:** This is normal on first run. Subsequent builds are faster. Consider using SSD.

### Issue: Executable crashes immediately
**Solution:** 
1. Run from command prompt to see error messages
2. Check all required data files are present
3. Check Python version compatibility

## Advanced Configuration

### Changing API Port
Edit `config.ini` in the dist folder:
```ini
[api]
port = 5000
host = 0.0.0.0
```

### Running as Windows Service
For production deployments, run as service (requires admin):
```bash
nssm install TalentMarketplaceAPI "C:\path\to\TalentMarketplace-API.exe"
nssm start TalentMarketplaceAPI
```

## Version Updates

When releasing new versions:

1. **Version number** in this documentation
2. **Update changelog** with new features
3. **Re-build executable**
4. **Re-package and test**
5. **Update installation instructions**

## Uninstalling

Users can simply:
1. Close the API window
2. Delete the TalentMarketplace-API folder
3. Done (no registry entries or system modifications)

## Support & Issues

If users encounter issues:

1. **Check Windows Defender** - may flag executable (false positive)
2. **Port already in use** - change port in config
3. **Performance issues** - normal on first request (model loading)
4. **Network access** - check firewall settings for port 5000

## Digital Signature (Optional)

For trusted distribution:
1. Obtain code signing certificate
2. Sign the executable:
   ```bash
   signtool sign /f certificate.pfx /p password /t http://timestamp.server /d "TalentMarketplace API" TalentMarketplace-API.exe
   ```

This prevents Windows SmartScreen warnings.

## Next Steps

1. ✅ Build the executable: `build_exe.bat`
2. ✅ Test on clean Windows system
3. ✅ Create ZIP archive
4. ✅ Host for download
5. ✅ Distribute to users
6. ✅ Provide support

---

**Last Updated:** January 2026
**Build Method:** PyInstaller
**Target:** Windows 7 SP1+
