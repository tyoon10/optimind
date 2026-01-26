# OptiMind Startup Script

$root = "/path/to/OptiMind"
Set-Location $root

Write-Host "🚀 Launching OptiMind..." -ForegroundColor Cyan

# 1. Start FastApi Server
Write-Host "1. Starting Uvicorn API Server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload" -WorkingDirectory $root

Write-Host "✅ Done! Server running." -ForegroundColor Green
Write-Host "---------------------------------------------------"
Read-Host "Press Enter to stop the server..."
