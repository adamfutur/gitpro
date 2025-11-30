# GitPro - AI-Powered GitHub Companion Platform

A microservices-based AI platform for GitHub developers featuring code analysis, commit insights, security scanning, and repo-aware conversational AI.

## Architecture

GitPro uses a microservices architecture with the following services:

- **API Gateway** (Port 8000) - Single entry point for all client requests
- **Auth Service** (Port 8001) - GitHub OAuth and JWT management
- **Repository Service** (Port 8002) - Repository metadata and GitHub API integration
- **AI Service** (Port 8003) - Code analysis, embeddings generation, security scanning
- **Chat Service** (Port 8004) - Repo-aware conversational AI
- **Webhook Service** (Port 8005) - GitHub webhook event processing

## Tech Stack

**Backend:**
- Go 1.21
- Fiber web framework
- PostgreSQL with pgvector
- Redis for job queuing
- Google Gemini AI

**Frontend (Future):**
- Next.js 14
- TypeScript
- TailwindCSS
- Futuristic cyberpunk UI

## Prerequisites

- Docker & Docker Compose
- Go 1.21+ (for local development)
- GitHub OAuth App credentials
- Google Gemini API key

## Quick Start

### 1. Setup Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and add your credentials:
- `GITHUB_CLIENT_ID` - From GitHub OAuth App
- `GITHUB_CLIENT_SECRET` - From GitHub OAuth App
- `GEMINI_API_KEY` - From Google AI Studio
- `JWT_SECRET` - Random secret for JWT signing

### 2. Start All Services

```bash
docker-compose up --build
```

This will start:
- All 5 databases (PostgreSQL + pgvector)
- Redis
- All 6 microservices
- API Gateway on port 8000

### 3. Verify Services

Check health status:
```bash
curl http://localhost:8000/health
```

Individual service health checks:
```bash
curl http://localhost:8001/health  # Auth
curl http://localhost:8002/health  # Repository
curl http://localhost:8003/health  # AI
curl http://localhost:8004/health  # Chat
curl http://localhost:8005/health  # Webhook
```

## API Endpoints

All requests go through the API Gateway at `http://localhost:8000/api`

### Authentication

```bash
# Start GitHub OAuth flow
GET /api/auth/github

# OAuth callback (handled automatically)
GET /api/auth/callback

# Get current user
GET /api/auth/me
Authorization: Bearer <jwt_token>

# Logout
POST /api/auth/logout
```

### Repositories

```bash
# List user repositories
GET /api/repos?user_id=1
Authorization: Bearer <jwt_token>

# Get repository details
GET /api/repos/:id

# Sync repository from GitHub
POST /api/repos/:id/sync
X-GitHub-Token: <github_access_token>

# Trigger AI analysis
POST /api/repos/:id/analyze
```

### AI Analysis

```bash
# Get analysis results for repository
GET /api/analysis/:repo_id

# Search code embeddings
GET /api/embeddings/search?q=authentication&repo_id=1
```

### Chat

```bash
# Create chat session
POST /api/chat/sessions
{
  "user_id": 1,
  "repo_id": 123,
  "title": "Ask about authentication"
}

# Get chat history
GET /api/chat/sessions/:id/messages

# Send message
POST /api/chat/message
{
  "session_id": 1,
  "message": "How does authentication work in this repo?"
}
```

### Webhooks

```bash
# GitHub webhook endpoint
POST /api/webhooks/github
X-Hub-Signature-256: <signature>
X-GitHub-Event: <event_type>
```

## Database Schemas

Each service has its own database:

- **auth_db**: Users, sessions
- **repos_db**: Repositories, commits, issues, pull requests
- **ai_db**: Code embeddings (pgvector), analysis results, vulnerabilities
- **chat_db**: Chat sessions, messages
- **webhook_db**: Webhook events log

## Development

### Local Development (Without Docker)

1. **Start databases:**
```bash
# Use Docker for databases only
docker-compose up auth-db repos-db ai-db chat-db webhook-db redis
```

2. **Run services individually:**
```bash
cd services/auth-service && go run cmd/main.go
cd services/repo-service && go run cmd/main.go
cd services/ai-service && go run cmd/main.go
cd services/chat-service && go run cmd/main.go
cd services/webhook-service && go run cmd/main.go
cd services/api-gateway && go run cmd/main.go
```

### Testing

```bash
# Test individual services
cd services/auth-service && go test ./...
cd services/repo-service && go test ./...
```

## Data Flow

1. **User Authentication:**
   - User clicks "Login with GitHub" → API Gateway → Auth Service
   - OAuth flow completes → JWT token returned

2. **Repository Analysis:**
   - User triggers analysis → API Gateway → Repository Service
   - Repo Service publishes job to Redis queue
   - AI Service consumes job → Clones repo → Generates embeddings
   - Performs code quality + security analysis → Stores in ai_db

3. **Chat with AI:**
   - User sends message → API Gateway → Chat Service
   - Chat Service queries embeddings from ai_db for context
   - Sends to Gemini with repo context → Returns AI response

4. **Webhook Processing:**
   - GitHub sends webhook → API Gateway → Webhook Service
   - Signature verified → Event stored → Processing job queued

## Deployment

### Docker Compose (Production)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Kubernetes

Kubernetes manifests are available in `/k8s` directory:

```bash
kubectl apply -f k8s/
```

## GitHub OAuth Setup

1. Go to GitHub Settings → Developer settings → OAuth Apps
2. Create new OAuth App
3. Set Authorization callback URL: `http://localhost:8001/callback`
4. Copy Client ID and Client Secret to `.env`

## Gemini API Setup

1. Visit Google AI Studio: https://makersuite.google.com/app/apikey
2. Create API key
3. Add to `.env` as `GEMINI_API_KEY`

## Project Structure

```
gitpro/
├── services/
│   ├── api-gateway/
│   ├── auth-service/
│   ├── repo-service/
│   ├── ai-service/
│   ├── chat-service/
│   └── webhook-service/
├── docker-compose.yml
├── .env.example
└── README.md
```

## Features

✅ **Implemented (Backend):**
- Microservices architecture
- GitHub OAuth authentication
- Repository syncing from GitHub
- AI-powered code analysis
- Security vulnerability scanning
- Code embeddings with pgvector
- Repo-aware chat assistant
- GitHub webhook processing
- Background job queue with Redis

🚧 **Next Phase (Frontend):**
- Next.js 14 application
- Futuristic cyberpunk UI
- 3D code visualizations
- Real-time dashboards
- Interactive chat interface

## Troubleshooting

**Services not starting:**
- Check Docker logs: `docker-compose logs <service_name>`
- Verify environment variables in `.env`

**Database connection errors:**
- Ensure databases are healthy: `docker-compose ps`
- Check database URLs in service configs

**AI Service failing:**
- Verify GEMINI_API_KEY is valid
- Check API quotas in Google AI Studio

## Contributing

This is a demonstration project. For production use, consider:
- Implementing proper error handling
- Adding comprehensive tests
- Setting up CI/CD pipelines
- Implementing service mesh (Istio/Linkerd)
- Adding distributed tracing (Jaeger)
- Implementing rate limiting
- Adding caching layers

## License

MIT License - See LICENSE file for details
