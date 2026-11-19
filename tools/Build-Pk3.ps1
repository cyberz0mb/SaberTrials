[CmdletBinding()]
param(
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Version = 'dev'
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$modRoot = Split-Path -Parent $PSScriptRoot
$expectedFolderName = 'SaberTrials'

if ((Split-Path -Leaf $modRoot) -ne $expectedFolderName) {
    throw "Safety check failed: this script must stay inside the $expectedFolderName mod folder."
}

$contentFolders = @(
    'ext_data',
    'maps',
    'models',
    'server',
    'scripts',
    'shaders',
    'sound',
    'textures',
    'ui'
)

$distPath = Join-Path $modRoot 'dist'
$packagePath = Join-Path $distPath "SaberTrials-$Version.pk3"
New-Item -ItemType Directory -Path $distPath -Force | Out-Null

if (Test-Path -LiteralPath $packagePath) {
    Remove-Item -LiteralPath $packagePath -Force
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$archive = [System.IO.Compression.ZipFile]::Open(
    $packagePath,
    [System.IO.Compression.ZipArchiveMode]::Create
)

try {
    $fileCount = 0

    foreach ($folderName in $contentFolders) {
        $folderPath = Join-Path $modRoot $folderName
        if (-not (Test-Path -LiteralPath $folderPath -PathType Container)) {
            continue
        }

        foreach ($file in Get-ChildItem -LiteralPath $folderPath -Recurse -File) {
            if ($file.Name -eq '.gitkeep') {
                continue
            }

            $relativePath = $file.FullName.Substring($modRoot.Length).TrimStart([char[]]'\/')
            $entryName = $relativePath.Replace('\', '/')

            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive,
                $file.FullName,
                $entryName,
                [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
            $fileCount++
        }
    }
}
finally {
    $archive.Dispose()
}

if ($fileCount -eq 0) {
    Remove-Item -LiteralPath $packagePath -Force
    throw 'No mod assets were found. Add content before building a PK3.'
}

Write-Host "Built $packagePath"
Write-Host "Included $fileCount file(s)."

# Ship editable examples beside the PK3, never a user's live root config.
$templateOutput = Join-Path $distPath "SaberTrials-$Version-templates"
New-Item -ItemType Directory -Path $templateOutput -Force | Out-Null
foreach ($templateName in @('staff-setup.cfg', 'server.cfg', 'README.md')) {
    Copy-Item -LiteralPath (Join-Path $modRoot "templates/$templateName") -Destination (Join-Path $templateOutput $templateName) -Force
}
Write-Host "Editable configuration templates: $templateOutput"
