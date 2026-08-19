# 🚀 GitPro Quick Start

## Step 1: Get API Credentials (5 minutes)

### GitHub OAuth App
1. Visit: https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in:
   - Application name: `GitPro Local`
   - Homepage URL: `http://localhost:8000`
   - Callback URL: `http://localhost:8001/callback`
4. **Copy Client ID and Secret** → Add to `.env`

### Google Gemini API
1. Visit: https://makersuite.google.com/app/apikey
2. Click **"Create API Key"**
3. **Copy the key** → Add to `.env` as `GEMINI_API_KEY`

## Step 2: Configure .env

Edit `C:\Users\imlou\Desktop\Pro\gitpro\.env`:

```env
GITHUB_CLIENT_ID=your_client_id_here
GITHUB_CLIENT_SECRET=your_client_secret_here
GEMINI_API_KEY=your_gemini_key_here
JWT_SECRET=any-random-string-here
```

## Step 3: Start Backend

```bash
cd C:\Users\imlou\Desktop\Pro\gitpro
docker-compose up --build
```

Wait for all services to start (2-3 minutes first time).

## Step 4: Test

**Run health check:**
```bash
test-health.bat
```

**Test OAuth in browser:**
```
http://localhost:8001/github
```

## ✅ Success Indicators

- All 6 services return `{"status":"healthy"}`
- OAuth redirects to GitHub
- No errors in Docker logs

## 📚 Full Testing Guide

See [TESTING.md](file:///C:/Users/imlou/Desktop/Pro/gitpro/TESTING.md) for detailed tests.
