$ProgressPreference = 'SilentlyContinue'
Write-Host "Downloading ngrok..."
Invoke-WebRequest -Uri "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip" -OutFile "ngrok.zip"
Write-Host "Extracting ngrok..."
Expand-Archive -Path "ngrok.zip" -DestinationPath "." -Force
Write-Host "Done. You can now run '.\ngrok.exe http 8000'"
Remove-Item "ngrok.zip"
