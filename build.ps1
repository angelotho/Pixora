<#
.SYNOPSIS
  Prepara o ambiente, roda os testes e gera o Pixora para Windows.
.EXAMPLE
  .\build.ps1             # pasta dist\Pixora\ com Pixora.exe + ZIP para distribuição
  .\build.ps1 -OneFile    # um único dist\Pixora.exe
  .\build.ps1 -SkipTests
#>
param([switch]$OneFile, [switch]$SkipTests)
# Ferramentas nativas escrevem progresso no stderr; erros são checados via $LASTEXITCODE.
$ErrorActionPreference = "Continue"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Criando ambiente virtual..." -ForegroundColor Cyan
    py -3.12 -m venv .venv
    if (-not $?) { python -m venv .venv }
}
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install --upgrade pip --quiet
& $py -m pip install -r requirements-dev.txt --quiet
if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar dependências" }

if (-not $SkipTests) {
    Write-Host "Executando testes..." -ForegroundColor Cyan
    & $py -m pytest
    if ($LASTEXITCODE -ne 0) { throw "Testes falharam; build interrompido." }
}

$env:QT_QPA_PLATFORM = "offscreen"
& $py scripts\make_icon.py
$iconExit = $LASTEXITCODE
Remove-Item Env:\QT_QPA_PLATFORM
if ($iconExit -ne 0) { throw "Falha ao gerar o ícone" }

if ($OneFile) { $env:PIXORA_ONEFILE = "1" } else { Remove-Item Env:\PIXORA_ONEFILE -ErrorAction SilentlyContinue }
Write-Host "Gerando executável com PyInstaller..." -ForegroundColor Cyan
& $py -m PyInstaller pixora.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

$exe = if ($OneFile) { "dist\Pixora.exe" } else { "dist\Pixora\Pixora.exe" }

Write-Host "Teste de inicialização do executável..." -ForegroundColor Cyan
$env:PIXORA_SMOKE_TEST = "1"
$proc = Start-Process -FilePath $exe -PassThru -Wait
Remove-Item Env:\PIXORA_SMOKE_TEST
if ($proc.ExitCode -ne 0) { throw "O executável não iniciou corretamente (código $($proc.ExitCode))." }

if (-not $OneFile) {
    $zip = "dist\Pixora-1.0.0-windows-x64.zip"
    if (Test-Path $zip) { Remove-Item $zip }
    Compress-Archive -Path "dist\Pixora" -DestinationPath $zip
    Write-Host "Pacote: $zip" -ForegroundColor Green
}
Write-Host "Pronto: $exe" -ForegroundColor Green
