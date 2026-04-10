Param(
  [string]$AppName = "SRF_Desktop",
  [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$cloud = Join-Path $root "cloud"

Set-Location $cloud

python -m pip install -r requirements.txt
python assets\generate_lion_icon.py

$dist = Join-Path $cloud "dist"
$work = Join-Path $cloud "build"
$spec = Join-Path $cloud "$AppName.spec"
$icon = Join-Path $cloud "assets\srf_lion_icon.ico"

if (Test-Path $dist) { Remove-Item $dist -Recurse -Force }
# Em alguns ambientes o build anterior pode manter ficheiros bloqueados por segundos.
# Não travamos o processo por isso; o --clean do PyInstaller trata o restante.
if (Test-Path $work) {
  try { Remove-Item $work -Recurse -Force -ErrorAction Stop } catch { }
}
if (Test-Path $spec) { Remove-Item $spec -Force }

$sep = ";"
$pyExe = (Get-Command python).Source
$pyHome = Split-Path $pyExe -Parent
$py3Dll = Join-Path $pyHome "python3.dll"
if (!(Test-Path $py3Dll)) {
  throw "Nao encontrei python3.dll em $pyHome"
}

if ($OneFile) {
  python -m PyInstaller `
    --noconfirm `
    --clean `
    --name $AppName `
    --onefile `
    --windowed `
    --icon $icon `
    --hidden-import app.main `
    --hidden-import app.auth `
    --hidden-import app.session `
    --hidden-import app.storage `
    --hidden-import app.report_parser `
    --hidden-import app.rules_engine `
    --hidden-import app.ollama_bridge `
    --exclude-module torch `
    --exclude-module torchvision `
    --exclude-module torchaudio `
    --exclude-module tensorflow `
    --exclude-module transformers `
    --exclude-module scipy `
    --exclude-module sklearn `
    --exclude-module cv2 `
    --exclude-module onnxruntime `
    --add-binary="${py3Dll}:." `
    --add-data="app:app" `
    --add-data="..\aparencia:aparencia" `
    --add-data="..\atm_v5.py:." `
    --add-data="..\srf_excel_format.py:." `
    --add-data="..\config.json:." `
    --add-data="..\testes:testes" `
    --add-data="..\tutorial:tutorial" `
    desktop_app.py
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou no modo onefile (exit $LASTEXITCODE)." }
}
else {
  python -m PyInstaller `
    --noconfirm `
    --clean `
    --name $AppName `
    --onedir `
    --windowed `
    --icon $icon `
    --hidden-import app.main `
    --hidden-import app.auth `
    --hidden-import app.session `
    --hidden-import app.storage `
    --hidden-import app.report_parser `
    --hidden-import app.rules_engine `
    --hidden-import app.ollama_bridge `
    --exclude-module torch `
    --exclude-module torchvision `
    --exclude-module torchaudio `
    --exclude-module tensorflow `
    --exclude-module transformers `
    --exclude-module scipy `
    --exclude-module sklearn `
    --exclude-module cv2 `
    --exclude-module onnxruntime `
    --add-binary="${py3Dll}:." `
    --add-data="app:app" `
    --add-data="..\aparencia:aparencia" `
    --add-data="..\atm_v5.py:." `
    --add-data="..\srf_excel_format.py:." `
    --add-data="..\config.json:." `
    --add-data="..\testes:testes" `
    --add-data="..\tutorial:tutorial" `
    desktop_app.py
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou no modo onedir (exit $LASTEXITCODE)." }
}

Write-Host ""
Write-Host "Build concluido."
if ($OneFile) {
  Write-Host "Executavel:" (Join-Path $dist "$AppName.exe")
}
else {
  Write-Host "Executavel:" (Join-Path (Join-Path $dist $AppName) "$AppName.exe")
}
