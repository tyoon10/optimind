# Google Cloud Platform (GCP) Setup Guide

To enable OptiMind to use the Gemini 3 Flash model, you need to set up a Google Cloud Project and generate a Service Account Key.

## Step 1: Create a NEW Project (OptiMind)
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Click the project dropdown (top-left) > **"New Project"**.
3.  **Critical**: Name it `OptiMind-Production` (or similar, distinct from 'Porfirio').
4.  Click **Create** and **SELECT** the new project.
5.  Copy your **Project ID** (e.g., `optimall-production-98765`) -> You will need this for the `.env` file.

## Step 2: Enable Vertex AI API
The agent needs access to the Vertex AI API to call Gemini.
1.  In the Cloud Console search bar, type **"Vertex AI API"**.
2.  Select **"Vertex AI API"** from the marketplace results.
3.  Click **Enable**.

## Step 3: Create Service Account Credentials
1.  Go to **IAM & Admin** > **[Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)**.
2.  Click **+ CREATE SERVICE ACCOUNT**.
    *   **Name**: `optimall-agent`
    *   **Description**: "For local agent execution"
    *   Click **Create and Continue**.
3.  **Grant Access**:
    *   Role: **Vertex AI User** (Start typing "Vertex AI User" to find it).
    *   Click **Continue** -> **Done**.

## Step 4: Generate JSON Key
1.  In the Service Accounts list, click on the email of the account you just created (`optimall-agent@...`).
2.  Go to the **KEYS** tab (top menu).
3.  Click **ADD KEY** > **Create new key**.
4.  Select **JSON** and click **Create**.
5.  A file will automatically download (e.g., `optimall-assistant-12345-abcdef.json`).

## Step 5: Configure Local Environment
1.  Move the downloaded JSON file to your project root (same folder as `main.py`'s parent).
    *   *Security Note*: Ensure this file is ignored by git (add `*.json` to `.gitignore`).
2.  Update your `.env` file:
    ```env
    GOOGLE_APPLICATION_CREDENTIALS="path/to/your-service-account-key.json"
    GOOGLE_PROJECT_ID="your-project-id"
    ```
    *(Note: Use forward slashes `/` in the path to avoid escape character issues)*.
