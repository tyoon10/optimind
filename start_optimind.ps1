# OptiMind Startup Script

$root = "/path/to/OptiMind"
Set-Location $root

Write-Host "🚀 Launching OptiMind..." -ForegroundColor Cyan

# 1. Start FastApi Server
Write-Host "1. Starting Uvicorn API Server..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", "python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"

# 2. Start Cloudflare Tunnel
Write-Host "2. Starting Cloudflare Tunnel..."
Start-Process powershell -ArgumentList "-NoExit", "-Command", ".\cloudflared.exe tunnel --url http://localhost:8000"

Write-Host "✅ Done!" -ForegroundColor Green
Write-Host "---------------------------------------------------"
Write-Host "IMPORTANT: Since you are using a Quick Tunnel:" -ForegroundColor Yellow
Write-Host "1. Look at the 'Cloudflared' window that just opened."
Write-Host "2. Copy the URL ending in '.trycloudflare.com'"
Write-Host "3. Update your Slack App 'Event Subscriptions' URL to:"
Write-Host "   [Your-URL]/slack/events"
Write-Host "---------------------------------------------------"
Read-Host "Press Enter to exit this launcher (Server windows will stay open)..."
