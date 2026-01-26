# pull_journal.ps1 - Sync Journal Memory
Write-Host "🔄 Syncing Journal..." -ForegroundColor Cyan

# Run git pull strictly inside the data/journal directory
git -C "$PSScriptRoot\..\data\journal" pull origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Synced." -ForegroundColor Green
} else {
    Write-Error "❌ Sync Failed."
}

pause
