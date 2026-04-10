Param(
  [string]$AppName = "SRF_Desktop"
)

$ErrorActionPreference = "Stop"

$exePath = Join-Path $PSScriptRoot "dist\$AppName\$AppName.exe"
if (!(Test-Path $exePath)) {
  throw "Executavel nao encontrado em: $exePath"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "SRF.lnk"

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $exePath
$shortcut.WorkingDirectory = Split-Path -Parent $exePath
$shortcut.IconLocation = $exePath
$shortcut.Description = "SRF App Desktop"
$shortcut.Save()

Write-Host "Atalho criado em: $shortcutPath"
