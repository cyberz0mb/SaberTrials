[Setup]
AppId={{845E0B40-4607-48ED-991A-08986C17826B}
AppName=Saber Trials
AppVersion={#BetaVersion}
AppVerName=Saber Trials {#BetaVersion}
DefaultDirName={code:DefaultGameData}
DefaultGroupName=Saber Trials
AppendDefaultDirName=no
DisableDirPage=no
DisableProgramGroupPage=yes
DirExistsWarning=no
AllowNoIcons=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
UninstallFilesDir={app}\SaberTrials\uninstall
UninstallDisplayIcon={app}\SaberTrials.x86_64.exe
SetupIconFile={#BrandIcon}
OutputBaseFilename=SaberTrials-Windows-{#BetaVersion}-Setup
Compression=lzma2/fast
SolidCompression=no
WizardStyle=modern
RestartApplications=no

[Types]
Name: "lite"; Description: "Lite — six offline translation languages"
Name: "full"; Description: "Full — all bundled offline translation languages"

[Components]
Name: "game"; Description: "Saber Trials player, dedicated server and six translation languages"; Types: lite full; Flags: fixed
Name: "languages"; Description: "Additional offline translation languages"; Types: full

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut to play Saber Trials"; Flags: unchecked

[Files]
#include FileList

[Icons]
Name: "{group}\Play Saber Trials"; Filename: "{app}\SaberTrials.x86_64.exe"; WorkingDir: "{app}"
Name: "{group}\Saber Trials Dedicated Server"; Filename: "{app}\SaberTrialsDed.x86_64.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Saber Trials"; Filename: "{app}\SaberTrials.x86_64.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Messages]
SelectDirLabel3=Choose the GameData folder inside your existing Jedi Academy installation.

[Code]
function GameDataAt(Dir: String): String;
var
  I: Integer;
begin
  Result := '';
  if Dir = '' then Exit;
  Dir := RemoveBackslashUnlessRoot(Dir);
  if DirExists(AddBackslash(Dir) + 'GameData\base') then
    Dir := AddBackslash(Dir) + 'GameData';
  for I := 0 to 3 do
    if not FileExists(AddBackslash(Dir) + 'base\assets' + IntToStr(I) + '.pk3') then Exit;
  Result := Dir;
end;

// Valve uses quoted key/value pairs in both its library list and app manifests.
function ValueForKey(Line, Key: String): String;
var
  Value: String;
  N: Integer;
begin
  Result := '';
  Line := Trim(Line);
  Key := '"' + Key + '"';
  if CompareText(Copy(Line, 1, Length(Key)), Key) <> 0 then Exit;
  Value := Trim(Copy(Line, Length(Key) + 1, Length(Line)));
  if Copy(Value, 1, 1) <> '"' then Exit;
  Delete(Value, 1, 1);
  N := Pos('"', Value);
  if N = 0 then Exit;
  Result := Copy(Value, 1, N - 1);
  StringChangeEx(Result, '\\', '\', True);
end;

function InLibrary(LibraryPath: String): String;
var
  Manifest: TArrayOfString;
  InstallName, Apps: String;
  I: Integer;
begin
  Apps := AddBackslash(LibraryPath) + 'steamapps\';
  Result := GameDataAt(Apps + 'common\Jedi Academy');
  if Result <> '' then Exit;
  if LoadStringsFromFile(Apps + 'appmanifest_6020.acf', Manifest) then
    for I := 0 to GetArrayLength(Manifest) - 1 do begin
      InstallName := ValueForKey(Manifest[I], 'installdir');
      if InstallName <> '' then begin
        Result := GameDataAt(Apps + 'common\' + InstallName);
        if Result <> '' then Exit;
      end;
    end;
end;

function DefaultGameData(Param: String): String;
var
  Steam, Dir: String;
  Libraries: TArrayOfString;
  I: Integer;
begin
  if RegQueryStringValue(HKLM64, 'Software\Microsoft\Windows\CurrentVersion\Uninstall\Steam App 6020',
    'InstallLocation', Dir) then begin
    Result := GameDataAt(Dir);
    if Result <> '' then Exit;
  end;
  if not RegQueryStringValue(HKCU, 'Software\Valve\Steam', 'SteamPath', Steam) then
    if not RegQueryStringValue(HKLM32, 'Software\Valve\Steam', 'InstallPath', Steam) then
      Steam := ExpandConstant('{commonpf32}\Steam');
  Result := InLibrary(Steam);
  if Result <> '' then Exit;
  if LoadStringsFromFile(AddBackslash(Steam) + 'steamapps\libraryfolders.vdf', Libraries) then
    for I := 0 to GetArrayLength(Libraries) - 1 do begin
      Dir := ValueForKey(Libraries[I], 'path');
      if Dir <> '' then begin
        Result := InLibrary(Dir);
        if Result <> '' then Exit;
      end;
    end;
  Result := GameDataAt(ExtractFileDir(ExpandConstant('{srcexe}')));
  if Result = '' then Result := AddBackslash(Steam) + 'steamapps\common\Jedi Academy\GameData';
end;

const
  FolderHelp = 'Choose the Jedi Academy installation folder or its GameData folder. Setup needs the four original base\assets*.pk3 files. In Steam, right-click Jedi Academy and select Manage > Browse local files.';

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Dir: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then begin
    Dir := GameDataAt(WizardDirValue);
    Result := Dir <> '';
    if Result then WizardForm.DirEdit.Text := Dir
    else SuppressibleMsgBox(FolderHelp, mbError, MB_OK, IDOK);
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  if GameDataAt(WizardDirValue) = '' then Result := FolderHelp
  else WizardForm.DirEdit.Text := GameDataAt(WizardDirValue);
end;
