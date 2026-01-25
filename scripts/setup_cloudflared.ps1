$ProgressPreference = 'SilentlyContinue'
Write-Host "Downloading cloudflared..."
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "cloudflared.exe"
Write-Host "Download complete: cloudflared.exe"
