# chat.ps1 - Run OptiMind in Console Mode
# Resolve the project root (one level up from bin/)
$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
Set-Location $ProjectRoot

Write-Host "Starting OptiMind CLI from $ProjectRoot..." -ForegroundColor Cyan
python src/cli.py
