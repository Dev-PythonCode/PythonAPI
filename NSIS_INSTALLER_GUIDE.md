# Creating Windows Installer for TalentMarketplace Python API

## Overview
NSIS (Nullsoft Scriptable Install System) creates professional Windows installers that handle:
- Installation wizard
- Uninstallation
- Registry entries
- Start menu shortcuts
- Desktop shortcuts

## Prerequisites

1. **Download NSIS**
   - Visit: http://nsis.sourceforge.net/
   - Download NSIS 3.x or later
   - Install to default location: `C:\Program Files (x86)\NSIS\`

2. **Build the executable first**
   ```bash
   build_exe.bat
   ```

## Create Installer Script

Create file `installer.nsi` in PythonAPI root directory:

```nsis
; TalentMarketplace API Windows Installer
; Built with NSIS

; Include Modern UI
!include "MUI2.nsh"

; General
Name "TalentMarketplace API"
OutFile "TalentMarketplace-API-Setup.exe"
InstallDir "$PROGRAMFILES\TalentMarketplace-API"
InstallDirRegKey HKCU "Software\TalentMarketplace-API" ""

; Version Information
VIProductVersion "1.0.0.0"
VIAddVersionKey /LANG=1033 "ProductName" "TalentMarketplace API"
VIAddVersionKey /LANG=1033 "CompanyName" "Your Company"
VIAddVersionKey /LANG=1033 "FileDescription" "NLP API for TalentMarketplace"
VIAddVersionKey /LANG=1033 "FileVersion" "1.0.0"
VIAddVersionKey /LANG=1033 "ProductVersion" "1.0.0"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright 2026"

; MUI Settings
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "LICENSE.txt"
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_LANGUAGE "English"

; Section: Install
Section "Install"
    SetOutPath "$INSTDIR"
    
    ; Copy executable and files
    File "dist\TalentMarketplace-API.exe"
    File "README.txt"
    File "LICENSE.txt"
    
    ; Copy models and data
    SetOutPath "$INSTDIR\models"
    File /r "dist\models\*.*"
    
    SetOutPath "$INSTDIR\data"
    File /r "dist\data\*.*"
    
    SetOutPath "$INSTDIR"
    
    ; Create batch file for running
    FileOpen $0 "$INSTDIR\Start API.bat" w
    FileWrite $0 "@echo off$\r$\n"
    FileWrite $0 "echo.$\r$\n"
    FileWrite $0 "echo Starting TalentMarketplace NLP API...$\r$\n"
    FileWrite $0 "echo.$\r$\n"
    FileWrite $0 "echo The API will be available at:$\r$\n"
    FileWrite $0 "echo   http://localhost:5000$\r$\n"
    FileWrite $0 "echo.$\r$\n"
    FileWrite $0 "TalentMarketplace-API.exe$\r$\n"
    FileWrite $0 "pause$\r$\n"
    FileClose $0
    
    ; Write registry
    WriteRegStr HKCU "Software\TalentMarketplace-API" "" "$INSTDIR"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TalentMarketplace-API" \
                     "DisplayName" "TalentMarketplace API"
    WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TalentMarketplace-API" \
                     "UninstallString" "$INSTDIR\uninstall.exe"
    
    ; Create Start Menu shortcut
    SetOutPath "$SMPROGRAMS\TalentMarketplace"
    CreateDirectory "$SMPROGRAMS\TalentMarketplace"
    CreateShortCut "$SMPROGRAMS\TalentMarketplace\Start API.lnk" "$INSTDIR\Start API.bat" "" "$INSTDIR\TalentMarketplace-API.exe"
    CreateShortCut "$SMPROGRAMS\TalentMarketplace\Uninstall.lnk" "$INSTDIR\uninstall.exe"
    
    ; Create Desktop shortcut (optional)
    CreateShortCut "$DESKTOP\Start TalentMarketplace API.lnk" "$INSTDIR\Start API.bat" "" "$INSTDIR\TalentMarketplace-API.exe"
    
    ; Create uninstaller
    WriteUninstaller "$INSTDIR\uninstall.exe"
SectionEnd

; Section: Uninstall
Section "Uninstall"
    ; Kill running process
    ExecWait 'taskkill /F /IM TalentMarketplace-API.exe'
    
    ; Remove files
    RMDir /r "$INSTDIR\models"
    RMDir /r "$INSTDIR\data"
    Delete "$INSTDIR\TalentMarketplace-API.exe"
    Delete "$INSTDIR\Start API.bat"
    Delete "$INSTDIR\README.txt"
    Delete "$INSTDIR\LICENSE.txt"
    Delete "$INSTDIR\uninstall.exe"
    
    ; Remove directory
    RMDir "$INSTDIR"
    
    ; Remove shortcuts
    RMDir /r "$SMPROGRAMS\TalentMarketplace"
    Delete "$DESKTOP\Start TalentMarketplace API.lnk"
    
    ; Remove registry
    DeleteRegKey HKCU "Software\TalentMarketplace-API"
    DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\TalentMarketplace-API"
SectionEnd

; Uninstaller page
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_LANGUAGE "English"
```

## Build the Installer

### Option 1: GUI
1. Open NSIS installation
2. Click "Compiler"
3. Select the `installer.nsi` file
4. Click "Compile NSI scripts"
5. Choose `installer.nsi`
6. Installer will be created as `TalentMarketplace-API-Setup.exe`

### Option 2: Command Line
```bash
cd C:\Program Files (x86)\NSIS
makensis.exe "C:\path\to\PythonAPI\installer.nsi"
```

## Installer Features

The installer provides:

✅ **Welcome Screen**
- Professional introduction
- License agreement

✅ **Installation Directory**
- Users can choose install location
- Default: `C:\Program Files\TalentMarketplace-API\`

✅ **Files Copy**
- Executable (250-350 MB)
- Models (100-150 MB)
- Data files
- Documentation

✅ **Start Menu**
- "Start API" shortcut
- "Uninstall" shortcut
- Located in Start Menu → TalentMarketplace

✅ **Desktop Shortcut**
- Optional shortcut on desktop
- Direct access to run API

✅ **Uninstaller**
- Clean removal of all files
- Registry cleanup
- Process termination

## Distribution

The installer file `TalentMarketplace-API-Setup.exe` is ready for distribution:

```
Size: ~350-400 MB (compressed executable)
Format: Windows Installer
Requirements: Windows 7 SP1+
Installation time: ~1-2 minutes
```

### Create Distribution Package:
```bash
# Copy installer to distribution folder
mkdir TalentMarketplace-API-Setup
copy TalentMarketplace-API-Setup.exe TalentMarketplace-API-Setup\
copy README.txt TalentMarketplace-API-Setup\
copy GETTING_STARTED.txt TalentMarketplace-API-Setup\

# Create ZIP
Compress-Archive -Path "TalentMarketplace-API-Setup" -DestinationPath "TalentMarketplace-API-Setup.zip"
```

## User Experience

### Installation
1. User downloads `TalentMarketplace-API-Setup.exe`
2. Double-click to run installer
3. Click through wizard (welcome → license → directory → install)
4. Installation complete
5. Start Menu now has "TalentMarketplace" folder

### Running the API
1. Click Start → TalentMarketplace → Start API
2. Or double-click desktop shortcut
3. Command window opens with:
   ```
   Running on http://localhost:5000
   ```
4. Keep window open to use API

### Uninstalling
1. Control Panel → Programs → Programs and Features
2. Find "TalentMarketplace API"
3. Click Uninstall
4. Confirm removal
5. All files and shortcuts removed

## Customization

### Change Company Name
Edit in `installer.nsi`:
```nsis
VIAddVersionKey /LANG=1033 "CompanyName" "Your Company Name"
```

### Add Custom Logo
```nsis
!insertmacro MUI_PAGE_WELCOME
!define MUI_WELCOMEFINISHPAGE_BITMAP "path\to\logo.bmp"
```

### Change Install Directory
```nsis
InstallDir "$LOCALAPPDATA\TalentMarketplace-API"
```

### Add More Start Menu Shortcuts
```nsis
CreateShortCut "$SMPROGRAMS\TalentMarketplace\API Documentation.lnk" "http://localhost:5000"
```

## Advanced Features

### System Service Installation
Run API as Windows Service automatically:

```nsis
; Install as service using NSSM
ExecWait 'nssm install TalentMarketplaceAPI "$INSTDIR\TalentMarketplace-API.exe"'
ExecWait 'nssm set TalentMarketplaceAPI AppDirectory "$INSTDIR"'
```

### Port Configuration
```nsis
; Create config file during installation
FileOpen $0 "$INSTDIR\config.ini" w
FileWrite $0 "[api]$\r$\n"
FileWrite $0 "port=5000$\r$\n"
FileWrite $0 "host=0.0.0.0$\r$\n"
FileClose $0
```

### Firewall Exception
```nsis
; Allow firewall access (requires admin)
ExecWait 'netsh advfirewall firewall add rule name="TalentMarketplace API" dir=in action=allow program="$INSTDIR\TalentMarketplace-API.exe" enable=yes'
```

## Troubleshooting

### Issue: "NSIS is not installed"
Solution: Download and install NSIS from http://nsis.sourceforge.net/

### Issue: "Script compilation error"
Solution: Check file paths in installer.nsi match your actual file structure

### Issue: Large installer size (400+ MB)
This is normal - includes full Python + all packages

### Issue: Antivirus warns about installer
Solution: Code-sign the installer (see digital signature section in main guide)

## Next Steps

1. ✅ Create `installer.nsi`
2. ✅ Build executable: `build_exe.bat`
3. ✅ Compile installer with NSIS
4. ✅ Test installation on clean Windows
5. ✅ Distribute `TalentMarketplace-API-Setup.exe`

---

**NSIS Official Site:** http://nsis.sourceforge.net/
**Documentation:** http://nsis.sourceforge.io/Docs/
