$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$python=Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if(-not(Test-Path -LiteralPath $python)){throw 'Create the development environment first; see CONTRIBUTING.md'}
& '.\setup-model.ps1' -OcrOnly
$priorPlatform=$env:QT_QPA_PLATFORM
try{
 $env:QT_QPA_PLATFORM='offscreen'
 & $python -m pytest -q
 if($LASTEXITCODE -ne 0){throw 'Tests failed; build stopped'}
}finally{$env:QT_QPA_PLATFORM=$priorPlatform}
$env:CREDONOMICS_RELEASE_PROFILE='store-submission'
& $python -m PyInstaller --noconfirm --distpath dist --workpath build CredoNomics.spec
if($LASTEXITCODE -ne 0){throw 'Packaging failed'}
Write-Host 'Unsigned local build: dist\CredoNomics Cyber Solutions\CredoNomics Cyber Solutions.exe'
