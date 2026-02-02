# 🐦‍🔥 GitPro
### **The Autonomous Repository Intelligence System**

**GitPro** is a high-performance, microservice-based platform that analyzes GitHub repositories using AI to detect vulnerabilities, generate vector embeddings, and enable deep semantic chat over your entire codebase.

[![Python Core](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Cognition](https://img.shields.io/badge/Cognition-Google_Gemini-orange?style=for-the-badge&logo=google-gemini)](https://deepmind.google/technologies/gemini/)
[![Memory](https://img.shields.io/badge/Memory-pgvector-00FFCC?style=for-the-badge&logo=postgresql)](https://github.com/pgvector/pgvector)
[![Orchestration](https://img.shields.io/badge/Orchestration-Docker-blue?style=for-the-badge&logo=docker)](https://www.docker.com/)

---

## 🏗️ The Neural Infrastructure
Phoenix is engineered as a distributed network of Python microservices. It balances futuristic automation with production-grade stability.

### 🛠️ Technical Specifications
*   **Core Engine:** Asynchronous Python 3.10+ (FastAPI / Uvicorn).
*   **Database Sharding:** 5 independent PostgreSQL instances + **pgvector** for high-dimensional search.
*   **Async Processing:** Redis-backed task queuing for intensive code analysis.
*   **AI Orchestration:** Google Gemini Pro via RAG (Retrieval-Augmented Generation).

### 🛰️ Service Registry & Port Mapping
| Node | Port | Role | Database / Tech |
| :--- | :--- | :--- | :--- |
| **The Nexus** | `8000` | API Gateway & Routing | Nginx / FastAPI |
| **Auth Cell** | `8001` | GitHub OAuth2 & JWT | PostgreSQL (`auth_db`) |
| **Sync Engine** | `8002` | GitHub API Sync | PostgreSQL (`repos_db`) |
| **Cortex** | `8003` | Neural Embeddings & Scanning | PostgreSQL + `pgvector` |
| **Oracle** | `8004` | Context-Aware Chat | Google Gemini Pro |
| **Pulse** | `8005` | Webhook Event Listener | Redis |

---

## 📡 API Protocols
All requests are routed through the Nexus Gateway (`:8000`). Most endpoints require an `Authorization: Bearer <jwt_token>` header.

| Method | Endpoint | Description | Payload Example |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/auth/github` | Initiate OAuth Flow | - |
| `POST` | `/api/repos/:id/sync` | Force GitHub Sync | - |
| `POST` | `/api/repos/:id/analyze`| Trigger AI Audit | `{ "depth": "full" }` |
| `GET` | `/api/analysis/:id` | Get Security Report | - |
| `POST` | `/api/chat/message` | Query the Oracle | `{ "message": "Find SQL injection risks" }` |
| `GET` | `/api/embeddings/search`| Semantic Code Search | `?q=auth_logic&limit=5` |

---

## 🚀 Activation Sequence

### 1. Environmental Synthesis
Prepare your `.env` matrix. You will need a GitHub OAuth App and a Google AI Studio Key.
```bash
cp .env.example .env
# Edit .env with your GITHUB_CLIENT_ID, GEMINI_API_KEY, and JWT_SECRET
```

### 2. Ignite the Mesh
Phoenix uses Docker Compose to orchestrate its 6 services and 6 data containers simultaneously.
```bash
docker-compose up --build -d
```

### 3. Calibration Check
Ensure all nodes are operational:
```bash
curl http://localhost:8000/health
```

---

## 🧠 Intelligence Flow (Grounded AI)
Phoenix doesn't just "read" code; it understands it through a multi-stage pipeline:

1.  **Ingestion:** The **Sync Engine** clones the repo and extracts metadata.
2.  **Vectorization:** The **Cortex** breaks code into chunks and converts them into 768-dimensional vectors using Gemini embeddings.
3.  **Storage:** Vectors are stored in **pgvector**, allowing for "semantic" search (finding code by meaning, not just keywords).
4.  **Inference:** When you chat with the **Oracle**, it retrieves the most relevant code snippets (RAG) and feeds them to Gemini for a grounded, accurate response.

---

## 📂 Project Anatomy
```text
gitpro/
├── services/
│   ├── api-gateway/      # Entry logic & Request filtering
│   ├── auth-service/     # Identity & Permissions
│   ├── repo-service/     # GitHub Ingestion logic
│   ├── ai-service/       # Vectorization & Security Scans
│   ├── chat-service/     # LLM Context Management (RAG)
│   └── webhook-service/  # Async Event Handlers
├── docker-compose.yml    # Full-stack blueprint
└── .env.example          # Security template
```

---

## 🗺️ Evolution Roadmap
- [x] **v1.0:** Python Mesh Architecture & Vector Core.
- [x] **v1.2:** Gemini Pro Integration & RAG logic.
- [ ] **v2.0:** **Next.js Phoenix Dashboard** (Cyberpunk UI/UX).
- [ ] **v2.5:** Automated PR remediation (AI writes the fix).

---
**Developed by 🐍. Optimized for 🐦‍🔥. The future of github experience is here.**
