# pull_journal.ps1 - Smart Sync Journal Memory
$journalPath = "$PSScriptRoot\..\data\journal"

Write-Host "🔄 Smart Syncing Journal..." -ForegroundColor Cyan

# 1. Check for local changes
$status = git -C $journalPath status --porcelain

if ($status) {
    Write-Host "📝 Local changes detected. Committing..." -ForegroundColor Yellow
    
    # 2. Add and Commit
    git -C $journalPath add .
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
    git -C $journalPath commit -m "Manual Log Update $timestamp"
    
    Write-Host "✅ Local changes saved." -ForegroundColor Green
} else {
    Write-Host "ℹ️  No local changes to save." -ForegroundColor Gray
}

# 3. Pull (Merge)
Write-Host "⬇️  Pulling from Cloud..." -ForegroundColor Cyan
git -C $journalPath pull origin main

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Sync Complete." -ForegroundColor Green
} else {
    Write-Error "❌ Sync Failed. You may have a merge conflict."
}

pause
