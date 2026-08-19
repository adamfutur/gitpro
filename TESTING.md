# Backend Testing Guide

## 🔑 Required API Credentials

### 1. GitHub OAuth App

**Create GitHub OAuth App:**
1. Go to: https://github.com/settings/developers
2. Click "New OAuth App"
3. Fill in:
   - **Application name**: GitPro Local Dev
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8001/callback`
4. Click "Register application"
5. Copy **Client ID** → Add to `.env` as `GITHUB_CLIENT_ID`
6. Click "Generate a new client secret"
7. Copy **Client Secret** → Add to `.env` as `GITHUB_CLIENT_SECRET`

### 2. Google Gemini API Key

**Get Gemini API Key:**
1. Go to: https://makersuite.google.com/app/apikey
2. Click "Create API Key"
3. Select project or create new one
4. Copy the API key → Add to `.env` as `GEMINI_API_KEY`

### 3. Optional: Generate JWT Secret

```bash
# On Windows PowerShell
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object {[char]$_})
```

Copy the output → Add to `.env` as `JWT_SECRET`

---

## 🚀 Start the Backend

```bash
cd C:\Users\imlou\Desktop\Pro\gitpro

# Make sure .env is configured
# Then start all services
docker-compose up --build
```

**Expected Output:**
- All databases starting and becoming healthy
- Redis starting
- All 6 services starting on ports 8000-8005

---

## ✅ Test Each Service

### 1. Health Check All Services

```bash
# API Gateway
curl http://localhost:8000/health

# Auth Service
curl http://localhost:8001/health

# Repository Service
curl http://localhost:8002/health

# AI Service
curl http://localhost:8003/health

# Chat Service
curl http://localhost:8004/health

# Webhook Service
curl http://localhost:8005/health
```

**Expected:** Each should return `{"status":"healthy","service":"..."}`

---

### 2. Test GitHub OAuth Flow

**Open in browser:**
```
http://localhost:8001/github
```

**Expected:**
- Redirects to GitHub authorization page
- After approving, redirects to frontend URL with token parameter
- Since frontend doesn't exist yet, you'll see a redirect URL in browser

**Extract JWT Token:**
Look for URL pattern: `http://localhost:3000/auth/callback?token=<JWT_TOKEN>`

Copy the JWT token for next tests.

---

### 3. Test Auth Service - Get User Info

Replace `<JWT_TOKEN>` with your token:

```bash
curl http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer <JWT_TOKEN>"
```

**Expected:**
```json
{
  "id": 1,
  "github_id": 12345678,
  "username": "your-github-username",
  "email": "your@email.com",
  "avatar_url": "https://avatars.githubusercontent.com/...",
  "created_at": "2025-11-21T..."
}
```

---

### 4. Test Repository Service - Sync Repos

This requires your GitHub access token. After OAuth, it's stored in the database.

**For testing, use your GitHub personal access token:**
1. Go to: https://github.com/settings/tokens
2. Generate new token (classic)
3. Select scopes: `repo`, `read:user`
4. Copy token

```bash
# List repos (will be empty initially)
curl "http://localhost:8000/api/repos?user_id=1"
```

To actually sync repos from GitHub, you'd need to implement a sync endpoint that fetches from GitHub API using the stored token.

---

### 5. Test AI Service - Manual Analysis

The AI service works via background jobs. Let's test it manually:

**Check if pgvector is working:**
```bash
# Connect to AI database
docker exec -it gitpro-ai-db-1 psql -U postgres -d ai_db

# In psql shell:
SELECT * FROM pg_extension WHERE extname = 'vector';

# Should show vector extension is installed
\q
```

---

### 6. Test Chat Service

```bash
# Create a chat session
curl -X POST http://localhost:8000/api/chat/sessions \
  -H "Content-Type: application/json" \
  -d "{\"user_id\": 1, \"title\": \"Test Chat\"}"
```

**Expected:**
```json
{"session_id": 1}
```

**Send a message:**
```bash
curl -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": 1, \"message\": \"What is microservices architecture?\"}"
```

**Expected:**
```json
{
  "response": "Microservices architecture is a software development approach where..."
}
```

**Get chat history:**
```bash
curl http://localhost:8000/api/chat/sessions/1/messages
```

---

### 7. Test Webhook Service

```bash
# Send a test webhook (without signature verification)
curl -X POST http://localhost:8000/api/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: push" \
  -H "X-GitHub-Delivery: test-123" \
  -d "{\"repository\": {\"id\": 123, \"name\": \"test-repo\"}}"
```

**Expected:**
```json
{
  "message": "Webhook received",
  "event": "push"
}
```

---

## 🔍 Troubleshooting

### Services Won't Start

**Check logs:**
```bash
docker-compose logs auth-service
docker-compose logs repo-service
docker-compose logs ai-service
```

**Common issues:**
- Missing environment variables → Check `.env` file
- Port already in use → Stop other services on ports 8000-8005, 5432-5436, 6379
- Database not ready → Wait for health checks to pass

### Database Connection Errors

```bash
# Check database status
docker-compose ps

# Restart a specific database
docker-compose restart auth-db
```

### Gemini API Errors

**Rate limits:**
- Free tier: 60 requests/minute
- Solution: Wait a minute between tests

**Invalid API key:**
- Verify key at: https://makersuite.google.com/app/apikey
- Regenerate if needed

### OAuth Redirect Issues

**Callback URL mismatch:**
- GitHub OAuth app callback MUST be: `http://localhost:8001/callback`
- Check GitHub app settings

---

## 📊 View Logs

**All services:**
```bash
docker-compose logs -f
```

**Specific service:**
```bash
docker-compose logs -f ai-service
docker-compose logs -f chat-service
```

---

## 🛑 Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

---

## ✨ Ready for Frontend?

Once all tests pass:
- ✅ All health checks return success
- ✅ OAuth flow redirects correctly
- ✅ Chat service responds with AI messages
- ✅ No errors in logs

Then we're ready to build the futuristic frontend! 🚀
