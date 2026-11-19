param([Parameter(Mandatory=$true)][string]$Output,[Parameter(Mandatory=$true)][string]$Metrics)
$ErrorActionPreference='Stop'
Add-Type -AssemblyName System.Drawing
Add-Type -Path "$PSScriptRoot/../development-source/mvp-cinematic/art/MvpArt.cs" -ReferencedAssemblies System.Drawing
try { [MvpArt]::Generate($Output,$Metrics) }
catch { throw $_.Exception.ToString() }
