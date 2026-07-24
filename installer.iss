; Inno Setup Script for OCR Nominas
; Requires Inno Setup 6+ (Unicode)

#define MyAppName "OCR Nominas"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "OCR Nominas"
#define MyAppURL "http://localhost:8000"
#define MyAppExeName "OCRNominas.exe"

; Check if Tesseract is on the system at COMPILE time
#define TesseractPath "C:\Program Files\Tesseract-OCR"
#define HasTesseract FileExists(TesseractPath + "\tesseract.exe")

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist\installer
OutputBaseFilename=OCRNominas-Installer
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
SetupIconFile=public\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear acceso directo en el escritorio"; GroupDescription: "Accesos directos:"; Flags: checkedonce

[Files]
; OCRNominas app files
Source: "dist\OCRNominas\OCRNominas.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\OCRNominas\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

#if HasTesseract
; Tesseract OCR (bundled)
Source: "{#TesseractPath}\tesseract.exe"; DestDir: "{app}\tesseract"; Flags: ignoreversion
Source: "{#TesseractPath}\*.dll"; DestDir: "{app}\tesseract"; Flags: ignoreversion
Source: "{#TesseractPath}\tessdata\*"; DestDir: "{app}\tesseract\tessdata"; Flags: ignoreversion recursesubdirs createallsubdirs
#else
; Tesseract NOT bundled - app will look for system Tesseract
#endif

[Dirs]
Name: "{app}\tesseract\tessdata"

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName}"; Flags: nowait postinstall skipifsilent shellexec
