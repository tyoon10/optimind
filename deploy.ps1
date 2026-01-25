# deploy.ps1 - One-Click Deployment for OptiMind

Write-Host "🚀 Starting OptiMind Deployment..." -ForegroundColor Green

# Generate unique tag based on timestamp to bypass cache
$TAG = Get-Date -Format "yyyyMMdd-HHmmss"
$IMAGE_NAME = "us-central1-docker.pkg.dev/optimind-production/optimind-repo/optimind:$TAG"

# 1. Build
Write-Host "`n📦 Building Docker Image: $IMAGE_NAME" -ForegroundColor Cyan
docker build -t $IMAGE_NAME .
if ($LASTEXITCODE -ne 0) { Write-Error "Build Failed"; exit 1 }

# 2. Push
Write-Host "`n☁️  Pushing to Artifact Registry..." -ForegroundColor Cyan
docker push $IMAGE_NAME
if ($LASTEXITCODE -ne 0) { Write-Error "Push Failed"; exit 1 }

# 3. Deploy
Write-Host "`n🚀 Deploying to Cloud Run..." -ForegroundColor Cyan
gcloud run deploy optimind-service `
  --image $IMAGE_NAME `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "GOOGLE_PROJECT_ID=optimind-production" `
  --set-env-vars "OPTIMIND_ENV=production" `
  --set-env-vars "SLACK_BOT_TOKEN=xoxb-..." `
  --set-env-vars "SLACK_SIGNING_SECRET=your-signing-secret" `
  --set-env-vars "GITHUB_PAT=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" `
  --set-env-vars "JOURNAL_REPO_URL=https://github.com/tyoon10/optimind-journal.git" `
  --set-env-vars "GOOGLE_API_KEY=your-google-api-key" `
  --no-cpu-throttling

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Deployment Complete!" -ForegroundColor Green
} else {
    Write-Error "`n❌ Deployment Failed"
}
