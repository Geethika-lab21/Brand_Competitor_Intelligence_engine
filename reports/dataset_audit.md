# Dataset Audit Report

This report evaluates the authenticity of the dataset collected for the **Brand & Competitor Intelligence Engine** as of Phase 2.

---

## 1. Core Ingestion Audit Questions

### Q1: Is the current dataset real Reddit data or mock/offline generated data?
* **Answer**: The current dataset is **100% mock/offline generated data**. None of the 7 posts and 35 comments stored in the database or raw CSV exports represent actual Reddit submissions or replies.

### Q2: Were Reddit API credentials successfully used during collection?
* **Answer**: **No**. Reddit API credentials were not used during collection. The connection attempt was bypassed or failed.

### Q3: Is the pipeline currently running in mock mode?
* **Answer**: **Yes**. The pipeline is running in mock mode.

---

## 2. Ingestion Status Analysis

### Why is the pipeline running in Mock Mode?
1. **Missing Configuration File**: The local workspace does not contain a `.env` configuration file containing active Reddit API keys. Only the `.env.example` template was present.
2. **Missing Environment Keys**: In `src/utils/config.py`, checks for `REDDIT_CLIENT_ID` and `REDDIT_CLIENT_SECRET` returned empty strings.
3. **Silent Fallback Design**: In Phase 1, `src/data_collection/reddit_collector.py` was designed to log a warning and fall back to mock data generation instead of crashing, allowing code execution to succeed in offline conditions.

---

## 3. Action Plan: Switching to Live Reddit Collection

To establish a live data pipeline and collect real discussions, please complete the following steps:

### Step 1: Create a Reddit Developer Application
1. Log into your Reddit account and navigate to [Reddit App Preferences](https://www.reddit.com/prefs/apps).
2. Click the **"are you a developer? create another app..."** or **"create app"** button.
3. Fill in the fields:
   - **Name**: `brand-intelligence-engine`
   - **App Type**: Select **"script"** (Crucial: choosing Web App or Installed App will fail with PRAW script execution).
   - **Description**: `Competitor skincare intelligence collector`
   - **About URL**: Leave blank.
   - **Redirect URI**: `http://localhost:8080` (or any valid URL).
4. Click **"create app"**.
5. Locate your credentials:
   - **Client ID**: The string located directly under the text "personal use script" (usually 14 characters).
   - **Client Secret**: The string labeled "secret" (usually 27 characters).

### Step 2: Configure the Local Environment
1. In the root of your project directory, copy `.env.example` to a new file named `.env`:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` in your editor and enter your credentials:
   ```ini
   REDDIT_CLIENT_ID=your_14_char_client_id_here
   REDDIT_CLIENT_SECRET=your_27_char_client_secret_here
   REDDIT_USER_AGENT=brand-intel-engine/1.0 by /u/your_reddit_username_here
   ```

### Step 3: Run the Upgraded Pipeline
Once credentials are set, run the new expanded collection pipeline to pull live data:
```bash
python pipeline_expand.py
```
*Note: In Phase 3, we have disabled the silent mock fallback. If the credentials in `.env` are missing or incorrect, the collector will raise a validation exception rather than collecting dummy data.*
