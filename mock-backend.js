const http = require('http');
const url = require('url');

const PORT = 8000;

const mockUser = {
    id: 1,
    github_id: 12345678,
    username: "developer",
    avatar_url: "https://avatars.githubusercontent.com/u/1?v=4",
    email: "dev@example.com"
};

const mockRepos = [
    {
        id: 1,
        name: "ai-chatbot",
        description: "Advanced AI chatbot with natural language processing",
        language: "Python",
        stars_count: 1234,
        forks_count: 89,
        analysis_status: "completed"
    },
    {
        id: 2,
        name: "microservices-backend",
        description: "Scalable microservices architecture with Go",
        language: "Go",
        stars_count: 567,
        forks_count: 45,
        analysis_status: "processing"
    }
];

const server = http.createServer((req, res) => {
    // CORS headers
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const parsedUrl = url.parse(req.url, true);
    const path = parsedUrl.pathname;

    console.log(`${req.method} ${path}`);

    // Auth Routes
    if (path === '/api/auth/github') {
        // Simulate redirect to GitHub and back
        res.writeHead(302, { 'Location': 'http://localhost:3000/auth/callback?token=mock_jwt_token' });
        res.end();
        return;
    }

    if (path === '/api/auth/me') {
        if (req.headers.authorization) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(mockUser));
        } else {
            res.writeHead(401);
            res.end(JSON.stringify({ error: 'Unauthorized' }));
        }
        return;
    }

    // Repo Routes
    if (path === '/api/repos') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify(mockRepos));
        return;
    }

    if (path.match(/\/api\/repos\/\d+/)) {
        const id = parseInt(path.split('/').pop());
        const repo = mockRepos.find(r => r.id === id);
        if (repo) {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(repo));
        } else {
            res.writeHead(404);
            res.end(JSON.stringify({ error: 'Not found' }));
        }
        return;
    }

    // Chat Routes
    if (path === '/api/chat/sessions' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            res.writeHead(201, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ session_id: 123 }));
        });
        return;
    }

    if (path === '/api/chat/message' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => body += chunk);
        req.on('end', () => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
                response: "I am a mock AI response from the Node.js server. I received your message!"
            }));
        });
        return;
    }

    res.writeHead(404);
    res.end(JSON.stringify({ error: 'Not found' }));
});

server.listen(PORT, () => {
    console.log(`Mock Backend running on http://localhost:${PORT}`);
});
