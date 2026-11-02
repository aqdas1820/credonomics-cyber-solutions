param([switch]$OcrOnly)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath $PSScriptRoot
$assets=@(
 @{Path='tessdata\eng.traineddata';Url='https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/923915d4ced2a7235221788285785a29c4a42d4a/eng.traineddata';Hash='7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2'},
 @{Path='tessdata\hin.traineddata';Url='https://raw.githubusercontent.com/tesseract-ocr/tessdata_fast/4e7c9ce934584e30654178261986ca1a03ffcfe8/hin.traineddata';Hash='4c73ffc59d497c186b19d1e90f5d721d678ea6b2e277b719bee4e2af12271825'}
)
foreach($asset in $assets){
 $path=Join-Path $PSScriptRoot $asset.Path
 if(-not(Test-Path -LiteralPath $path)){
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path)|Out-Null
  Invoke-WebRequest -UseBasicParsing -Uri $asset.Url -OutFile $path
 }
 if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToLower() -ne $asset.Hash){throw "OCR asset integrity check failed: $($asset.Path)"}
}
Write-Host 'English/Hindi OCR data verified. No background-removal weights are provisioned.'
