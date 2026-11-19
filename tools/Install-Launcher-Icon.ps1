$ErrorActionPreference = 'Stop'

$launcherRoot = Split-Path -Parent $PSScriptRoot
$launcherPath = Join-Path $launcherRoot 'tools\launchers\SaberTrials.cmd'
$previousLauncherPath = Join-Path $launcherRoot 'Launch-SaberTrials-Overhaul.cmd'
$iconPath = Join-Path $launcherRoot 'assets\branding\SaberTrials.ico'
$gameDataPath = Split-Path -Parent $launcherRoot
$desktopPath = [Environment]::GetFolderPath('Desktop')

foreach ($requiredPath in @($launcherPath, $iconPath)) {
    if (-not (Test-Path -LiteralPath $requiredPath -PathType Leaf)) {
        throw "Required launcher file is missing: $requiredPath"
    }
}

$shortcutPaths = @(
    (Join-Path $launcherRoot 'Saber Trials.lnk'),
    (Join-Path $desktopPath 'Saber Trials.lnk')
)
$shortcutShell = New-Object -ComObject WScript.Shell

# Do not replace an unrelated shortcut that happens to use the same name.
foreach ($shortcutPath in $shortcutPaths) {
    if (Test-Path -LiteralPath $shortcutPath) {
        $existing = $shortcutShell.CreateShortcut($shortcutPath)
        if ($existing.TargetPath -ne $launcherPath -and $existing.TargetPath -ne $previousLauncherPath) {
            throw "A different shortcut already uses this name: $shortcutPath"
        }
    }
}

foreach ($shortcutPath in $shortcutPaths) {
    $shortcut = $shortcutShell.CreateShortcut($shortcutPath)
    $shortcut.TargetPath = $launcherPath
    $shortcut.Arguments = ''
    $shortcut.WorkingDirectory = $gameDataPath
    $shortcut.IconLocation = "$iconPath,0"
    $shortcut.Description = 'Saber Trials'
    $shortcut.WindowStyle = 1
    $shortcut.Save()

    $verified = $shortcutShell.CreateShortcut($shortcutPath)
    if ($verified.TargetPath -ne $launcherPath -or
        $verified.IconLocation -ne "$iconPath,0" -or
        $verified.WorkingDirectory -ne $gameDataPath -or
        $verified.Arguments -ne '') {
        throw "Launcher shortcut verification failed: $shortcutPath"
    }
    Write-Output "Installed launcher shortcut: $shortcutPath"
}

# Refresh Explorer's icon associations without restarting Explorer or the game.
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class SaberTrialsIconRefresh {
    [DllImport("shell32.dll")]
    public static extern void SHChangeNotify(uint eventId, uint flags, IntPtr item1, IntPtr item2);
}
'@
[SaberTrialsIconRefresh]::SHChangeNotify(0x08000000, 0, [IntPtr]::Zero, [IntPtr]::Zero)
