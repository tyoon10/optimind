# Deploying OptiMind to Google Cloud Run

This guide steps you through deploying your **Stateless** bot to the **Serverless** Cloud Run environment.

## Prerequisites
1.  **GCP Project**: `optimind-production`.
2.  **gcloud CLI**: Installed and logged in (`gcloud auth login`).
3.  **GitHub PAT**: Your Personal Access Token with `repo` scope.

## Step 1: Set up Artifact Registry
Create a repository to store your Docker images.
```bash
gcloud artifacts repositories create optimind-repo --repository-format=docker --location=us-central1 --description="OptiMind Docker Repo"
```

## Step 2: Build & Push the Image
Run this from your project root (`/path/to/OptiMind`):

```powershell
# 1. Authenticate Docker with GCP
gcloud auth configure-docker us-central1-docker.pkg.dev

# 2. Build the Image
docker build -t us-central1-docker.pkg.dev/optimind-production/optimind-repo/optimind:latest .

# 3. Push to Registry
docker push us-central1-docker.pkg.dev/optimind-production/optimind-repo/optimind:latest
```

## Step 3: Deploy to Cloud Run
This command deploys the container and sets the environment variables. **Replace the values with your actual secrets.**

```powershell
gcloud run deploy optimind-service `
  --image us-central1-docker.pkg.dev/optimind-production/optimind-repo/optimind:latest `
  --platform managed `
  --region us-central1 `
  --allow-unauthenticated `
  --set-env-vars "GOOGLE_PROJECT_ID=optimind-production" `
  --set-env-vars "OPTIMIND_ENV=production" `
  --set-env-vars "SLACK_BOT_TOKEN=xoxb-..." `
  --set-env-vars "SLACK_APP_TOKEN=xapp-YOUR-TOKEN" `
  --set-env-vars "SLACK_SIGNING_SECRET=your-signing-secret" `
  --set-env-vars "GITHUB_PAT=ghp_..." `
  --set-env-vars "JOURNAL_REPO_URL=https://github.com/..." `
  --set-env-vars "GOOGLE_API_KEY=your-google-api-key"
```
*(Note: I added `.dockerignore` to your project to prevent your local `.env` from breaking the cloud build. Please Re-Build before switching to this step!)*

## Step 4: Update Slack
1.  Cloud Run will give you a Service URL (e.g., `https://optimind-service-xyz.a.run.app`).
2.  Go to **Slack App Dashboard** -> **Event Subscriptions**.
3.  Update Request URL to `https://optimind-service-xyz.a.run.app/slack/events`.

## Troubleshooting
*   **"Authentication Failed"**: Check your `GITHUB_PAT`.
*   **"Container failed to start"**: Check logs (`gcloud logging read "resource.type=cloud_run_revision" --limit 20`). It might be failing to clone the repo.
