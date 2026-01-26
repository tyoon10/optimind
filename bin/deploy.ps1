# deploy.ps1 - Secure One-Click Deployment
# Reads secrets from .env file so you don't have to hardcode them.

Write-Host "🚀 Starting OptiMind Deployment..." -ForegroundColor Green

# 1. Load Secrets from .env (Gitignored)
$EnvPath = Join-Path $PSScriptRoot "..\.env"
if (-not (Test-Path $EnvPath)) {
    Write-Error "Error: .env file not found at $EnvPath"
    Write-Host "Please create a .env file with your secrets (SLACK_BOT_TOKEN, etc.)"
    exit 1
}

# Parse .env and set local variables
Get-Content $EnvPath | ForEach-Object {
    if ($_ -match "^\s*([^#=]+)\s*=\s*(.*)$") {
        $Key = $matches[1]
        $Value = $matches[2]
        # Set variable in current scope (not system-wide)
        Set-Item -Path "env:$Key" -Value $Value
    }
}

# 2. Validation
$Required = @("SLACK_BOT_TOKEN", "SLACK_SIGNING_SECRET", "GITHUB_PAT", "GOOGLE_API_KEY")
foreach ($Var in $Required) {
    if (-not (Get-Item env:$Var -ErrorAction SilentlyContinue)) {
        Write-Error "Missing required secret in .env: $Var"
        exit 1
    }
}

# 3. Build & Push
$TAG = Get-Date -Format "yyyyMMdd-HHmmss"
$IMAGE_NAME = "us-central1-docker.pkg.dev/optimind-production/optimind-repo/optimind:$TAG"

Write-Host "`n📦 Building Docker Image: $IMAGE_NAME" -ForegroundColor Cyan
docker build -t $IMAGE_NAME .
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "`n☁️  Pushing to Artifact Registry..." -ForegroundColor Cyan
docker push $IMAGE_NAME
if ($LASTEXITCODE -ne 0) { exit 1 }

# 4. Deploy (Injecting secrets from our secure local scope)
Write-Host "`n🚀 Deploying to Cloud Run..." -ForegroundColor Cyan
gcloud run deploy optimind-service `
  --image $IMAGE_NAME `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "GOOGLE_PROJECT_ID=optimind-production" `
  --set-env-vars "OPTIMIND_ENV=production" `
  --set-env-vars "SLACK_BOT_TOKEN=$env:SLACK_BOT_TOKEN" `
  --set-env-vars "SLACK_SIGNING_SECRET=$env:SLACK_SIGNING_SECRET" `
  --set-env-vars "GITHUB_PAT=$env:GITHUB_PAT" `
  --set-env-vars "JOURNAL_REPO_URL=$env:JOURNAL_REPO_URL" `
  --set-env-vars "GOOGLE_API_KEY=$env:GOOGLE_API_KEY" `
  --no-cpu-throttling

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Success! Deployed version: $TAG" -ForegroundColor Green
}
