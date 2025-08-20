; ----------------------------
; Gesturefy Windows Installer
; ----------------------------

[Setup]
AppName=Gesturefy
AppVersion=1.0
DefaultDirName={pf}\Gesturefy
DefaultGroupName=Gesturefy
OutputDir=dist\installer
OutputBaseFilename=GesturefyInstaller
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

; License page
LicenseFile=LICENSE.txt

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

; ----------------------------
; Tasks for Desktop Shortcut
; ----------------------------
[Tasks]
Name: desktopicon; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; 

; ----------------------------
; Files to install
; ----------------------------
[Files]
Source: "dist\Gesturefy.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\Gesturefy_Windows\*"; DestDir: "{app}\_internal"; Flags: recursesubdirs createallsubdirs

; ----------------------------
; Shortcuts
; ----------------------------
[Icons]
Name: "{group}\Gesturefy"; Filename: "{app}\Gesturefy.exe"
Name: "{userdesktop}\Gesturefy"; Filename: "{app}\Gesturefy.exe"; Tasks: desktopicon

; ----------------------------
; Run app after installation
; ----------------------------
[Run]
Filename: "{app}\Gesturefy.exe"; Description: "Launch Gesturefy"; Flags: nowait postinstall skipifsilent

; ----------------------------
; Custom Messages 
; ----------------------------
[Messages]
WelcomeLabel1=Welcome to the Gesturefy Installer!
WelcomeLabel2=This wizard will guide you through installing Gesturefy on your computer.

