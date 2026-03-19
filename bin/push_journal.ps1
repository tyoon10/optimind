# push_journal.ps1 - Fast Sync to Cloud
Write-Host "🧠 Pushing Memory..." -ForegroundColor Cyan

$Target = "$PSScriptRoot\..\data\journal"
git -C $Target add .
git -C $Target commit -m "Manual update: $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
git -C $Target push origin main

if ($LASTEXITCODE -eq 0) { Write-Host "✅ Done." -ForegroundColor Green }
pause
