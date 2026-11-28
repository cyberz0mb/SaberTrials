# Build the real .NET Framework model and run its Windows playback integration checks.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$project = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$locator = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $locator -latest -products '*' -requires Microsoft.Component.MSBuild -property installationPath
$compiler = Join-Path $vs 'MSBuild/Current/Bin/Roslyn/csc.exe'
$framework = Join-Path ${env:ProgramFiles(x86)} 'Reference Assemblies/Microsoft/Framework/.NETFramework/v4.8'
$sdkRoot = Join-Path ${env:ProgramFiles(x86)} 'Windows Kits/10/UnionMetadata'
$sdk = Get-ChildItem -LiteralPath $sdkRoot -Directory |
    Where-Object { $_.Name -as [version] -and (Test-Path -LiteralPath (Join-Path $_.FullName 'Windows.winmd')) } |
    Sort-Object { [version]$_.Name } -Descending | Select-Object -First 1
if (!$sdk -or [version]$sdk.Name -lt [version]'10.0.17763.0') { throw 'Install Windows SDK 10.0.17763 or newer.' }
$references = @('mscorlib','System','System.Core','WindowsBase','PresentationCore','PresentationFramework','System.Xaml') |
    ForEach-Object { "/r:$framework/$_.dll" }
$references += @('System.Runtime','System.Runtime.InteropServices.WindowsRuntime','System.Threading.Tasks','System.Collections','System.ObjectModel') |
    ForEach-Object { "/r:$framework/Facades/$_.dll" }
$references += "/r:$env:WINDIR/Microsoft.NET/Framework64/v4.0.30319/System.Runtime.WindowsRuntime.dll"
$references += "/r:$($sdk.FullName)/Windows.winmd"

$tempRoot = (Get-Item -LiteralPath ([IO.Path]::GetTempPath())).FullName
$runName = 'SaberTrials-Music-Test-' + [guid]::NewGuid().ToString('N')
$runDirectory = (New-Item -ItemType Directory -Path (Join-Path $tempRoot $runName)).FullName
try {
    $exe = Join-Path $runDirectory 'MediaChecks.exe'
    $model = Join-Path $project 'development-source/music-player/MusicModel.cs'
    $test = Join-Path $PSScriptRoot 'MediaChecks.cs'
    $art = Join-Path $project 'development-source/music-player/TrackArtwork.cs'
    $volume = Join-Path $project 'development-source/music-player/AppVolume.cs'
    & $compiler /nologo /noconfig /nostdlib+ /warnaserror /langversion:7.3 /platform:x64 /target:exe "/out:$exe" @references $model $art $volume $test
    if ($LASTEXITCODE -ne 0) { throw 'Media test compilation failed.' }
    & $exe $runDirectory
    if ($LASTEXITCODE -ne 0) { throw 'One or more Windows playback checks failed.' }
}
finally {
    $verified = (Resolve-Path -LiteralPath $runDirectory).Path
    if ([IO.Path]::GetDirectoryName($verified).TrimEnd('\') -ne $tempRoot.TrimEnd('\') -or
        [IO.Path]::GetFileName($verified) -ne $runName) { throw 'Unexpected test directory.' }
    Remove-Item -LiteralPath $verified -Recurse -Force
}
