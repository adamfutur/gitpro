// PART 1 of 6
const http = require('http');
const https = require('https');
const url = require('url');
const crypto = require('crypto');
const { GoogleGenerativeAI } = require('@google/generative-ai');

const PORT = 3000;

// Load environment variables from .env file
require('dotenv').config();

const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID;
const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET;
const JWT_SECRET = process.env.JWT_SECRET || 'your-secret-key';
const FRONTEND_URL = process.env.FRONTEND_URL || 'http://localhost:3000';
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

// Initialize Gemini AI
const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);

// In-memory storage (in production, use a database)
const tokenStore = new Map();
const chatSessions = new Map(); // sessionId -> { userId, repoId, messages, createdAt }
const analysisCache = new Map(); // repoId -> analysis results

// Helper function to make HTTPS requests to GitHub API
function githubRequest(path, token, method = 'GET') {
    return new Promise((resolve, reject) => {
        const options = {
            hostname: 'api.github.com',
            path: path,
            method: method,
            headers: {
                'User-Agent': 'GitPro-App',
                'Accept': 'application/vnd.github.v3+json'
            }
        };

        if (token) {
            options.headers['Authorization'] = `token ${token}`;
        }

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                if (res.statusCode >= 200 && res.statusCode < 300) {
                    try {
                        resolve(JSON.parse(data));
                    } catch (err) {
                        // Some responses might be empty or not JSON - return as-is
                        resolve(data);
                    }
                } else {
                    reject(new Error(`GitHub API error: ${res.statusCode} - ${data}`));
                }
            });
        });

        req.on('error', reject);
        req.end();
    });
}

// Helper function to exchange code for access token
function exchangeCodeForToken(code) {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            client_id: GITHUB_CLIENT_ID,
            client_secret: GITHUB_CLIENT_SECRET,
            code: code
        });

        const options = {
            hostname: 'github.com',
            path: '/login/oauth/access_token',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };

        const req = https.request(options, (res) => {
            let data = '';
            res.on('data', (chunk) => data += chunk);
            res.on('end', () => {
                try {
                    const parsed = JSON.parse(data);
                    if (parsed.access_token) {
                        resolve(parsed.access_token);
                    } else {
                        reject(new Error('Failed to get access token: ' + data));
                    }
                } catch (err) {
                    reject(new Error('Failed to parse token response: ' + data));
                }
            });
        });

        req.on('error', reject);
        req.write(postData);
        req.end();
    });
}

// Generate JWT token
function generateJWT(userId) {
    const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64url');
    const payload = Buffer.from(JSON.stringify({ userId, exp: Date.now() + 24 * 60 * 60 * 1000 })).toString('base64url');
    const signature = crypto.createHmac('sha256', JWT_SECRET).update(`${header}.${payload}`).digest('base64url');
    return `${header}.${payload}.${signature}`;
}

// Helper function to call Gemini AI
async function callGemini(prompt, context = '') {
    try {
        const model = genAI.getGenerativeModel({ model: 'gemini-2.5-flash' });
        const fullPrompt = context ? `${context}\n\n${prompt}` : prompt;
        const result = await model.generateContent(fullPrompt);
        const response = await result.response;
        return response.text();
    } catch (error) {
        console.error('Gemini API error:', error);
        throw new Error('Failed to get AI response');
    }
}
// PART 2 of 6

// Fetch repository files from GitHub
async function fetchRepoFiles(owner, repo, githubToken, path = '') {
    try {
        const apiPath = `/repos/${owner}/${repo}/contents/${path}`;
        return await githubRequest(apiPath, githubToken);
    } catch (error) {
        console.error('Error fetching repo files:', error);
        return [];
    }
}

// Fetch repository README
async function fetchRepoReadme(owner, repo, githubToken) {
    try {
        const readme = await githubRequest(`/repos/${owner}/${repo}/readme`, githubToken);
        if (readme && readme.content) {
            return Buffer.from(readme.content, 'base64').toString('utf-8');
        }
        return null;
    } catch (error) {
        return null;
    }
}

/*
  New helper: Recursively fetch "important" files from the repo and return
  an array of { name, content } objects (content is truncated to avoid huge prompts).
  Limits:
   - up to MAX_FILES files
   - file content truncated to MAX_CONTENT_CHARS per file
*/
async function fetchImportantFiles(owner, repo, githubToken, path = '') {
    const MAX_FILES = 20;
    const MAX_CONTENT_CHARS = 4000;

    const importantExtensions = ['.js', '.ts', '.jsx', '.tsx', '.json', '.md', '.yml', '.yaml', '.env', '.py', '.go', '.java'];
    const importantNames = ['.env.example', 'readme.md', 'package.json', 'dockerfile', 'docker-compose.yml', 'Makefile'];

    let results = [];

    try {
        const items = await fetchRepoFiles(owner, repo, githubToken, path);

        if (!items || !Array.isArray(items)) return results;

        for (const item of items) {
            if (results.length >= MAX_FILES) break;

            try {
                if (item.type === 'file') {
                    const lowerName = item.name.toLowerCase();
                    const isImportant =
                        importantExtensions.some(ext => lowerName.endsWith(ext)) ||
                        importantNames.includes(lowerName);

                    if (isImportant) {
                        try {
                            const fileContentObj = await githubRequest(`/repos/${owner}/${repo}/contents/${item.path}`, githubToken);
                            if (fileContentObj && fileContentObj.content) {
                                const decoded = Buffer.from(fileContentObj.content, 'base64').toString('utf8');
                                results.push({
                                    name: item.path,
                                    content: decoded.substring(0, MAX_CONTENT_CHARS)
                                });
                            }
                        } catch (err) {
                            // skip problematic file
                            console.warn(`Failed to fetch content for ${item.path}:`, err.message || err);
                        }
                    }
                } else if (item.type === 'dir') {
                    // Recurse into directories unless we've hit limit
                    if (results.length < MAX_FILES) {
                        const sub = await fetchImportantFiles(owner, repo, githubToken, item.path);
                        for (const s of sub) {
                            results.push(s);
                            if (results.length >= MAX_FILES) break;
                        }
                    }
                }
            } catch (err) {
                console.warn('Error processing item', item && item.path, err && err.message);
            }
        }
    } catch (err) {
        console.error('Error in fetchImportantFiles:', err && err.message ? err.message : err);
    }

    return results.slice(0, MAX_FILES);
}

// New helpers: commits & PRs
async function fetchRepoCommits(owner, repo, githubToken) {
    try {
        return await githubRequest(`/repos/${owner}/${repo}/commits?per_page=5`, githubToken);
    } catch (err) {
        console.error('Error fetching commits:', err);
        return [];
    }
}

async function fetchRepoPullRequests(owner, repo, githubToken) {
    try {
        // include all states so AI can know about open/closed/merged PRs
        return await githubRequest(`/repos/${owner}/${repo}/pulls?state=all&per_page=5`, githubToken);
    } catch (err) {
        console.error('Error fetching PRs:', err);
        return [];
    }
}

async function fetchPullRequestChanges(owner, repo, prNumber, githubToken) {
    try {
        return await githubRequest(`/repos/${owner}/${repo}/pulls/${prNumber}/files`, githubToken);
    } catch (err) {
        console.error('Error fetching PR changes:', err);
        return [];
    }
}
// PART 3 of 6

const server = http.createServer(async (req, res) => {
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
    const query = parsedUrl.query;

    console.log(`${req.method} ${path}`);

    try {
        // GitHub OAuth initiation
        if (path === '/api/auth/github') {
            const redirectUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=repo,read:user,user:email`;
            res.writeHead(302, { 'Location': redirectUrl });
            res.end();
            return;
        }

        // OAuth callback - handle multiple possible paths
        if (path === '/callback' || path === '/api/auth/callback' || path === '/api/auth/github/callback') {
            const code = query.code;
            if (!code) {
                res.writeHead(302, { 'Location': `${FRONTEND_URL}/auth/callback?error=no_code` });
                res.end();
                return;
            }

            try {
                // Exchange code for access token
                const accessToken = await exchangeCodeForToken(code);

                // Get user info from GitHub
                const githubUser = await githubRequest('/user', accessToken);

                // Generate our JWT token
                const jwtToken = generateJWT(githubUser.id);

                // Store the GitHub access token associated with our JWT
                tokenStore.set(jwtToken, accessToken);

                // Redirect to frontend with token
                res.writeHead(302, { 'Location': `${FRONTEND_URL}/auth/callback?token=${jwtToken}` });
                res.end();
            } catch (error) {
                console.error('OAuth error:', error);
                res.writeHead(302, { 'Location': `${FRONTEND_URL}/auth/callback?error=oauth_failed` });
                res.end();
            }
            return;
        }

        // DEV LOGIN: Direct PAT login for testing
        if (path === '/api/dev/login' && req.method === 'POST') {
            let body = '';
            req.on('data', chunk => body += chunk);
            req.on('end', async () => {
                try {
                    const data = JSON.parse(body);
                    const pat = data.token;

                    if (!pat) {
                        res.writeHead(400, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ error: 'Token required' }));
                        return;
                    }

                    // Verify token by fetching user
                    try {
                        const githubUser = await githubRequest('/user', pat);

                        // Generate JWT
                        const jwtToken = generateJWT(githubUser.id);

                        // Store PAT as the access token
                        tokenStore.set(jwtToken, pat);

                        res.writeHead(200, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({
                            token: jwtToken,
                            user: {
                                id: githubUser.id,
                                username: githubUser.login,
                                name: githubUser.name
                            }
                        }));
                    } catch (err) {
                        res.writeHead(401, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ error: 'Invalid GitHub Token' }));
                    }
                } catch (error) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Invalid request' }));
                }
            });
            return;
        }

        // Get current user
        if (path === '/api/auth/me') {
            const authHeader = req.headers.authorization;
            if (!authHeader) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Unauthorized' }));
                return;
            }

            const token = authHeader.replace('Bearer ', '');
            const githubToken = tokenStore.get(token);

            if (!githubToken) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid token' }));
                return;
            }

            try {
                const githubUser = await githubRequest('/user', githubToken);
                const user = {
                    id: githubUser.id,
                    github_id: githubUser.id,
                    username: githubUser.login,
                    avatar_url: githubUser.avatar_url,
                    email: githubUser.email || `${githubUser.login}@users.noreply.github.com`,
                    name: githubUser.name,
                    bio: githubUser.bio,
                    created_at: githubUser.created_at
                };

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(user));
            } catch (error) {
                console.error('Error fetching user:', error);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Failed to fetch user' }));
            }
            return;
        }
        // PART 4 of 6

        // Get repositories
        if (path === '/api/repos') {
            const authHeader = req.headers.authorization;
            if (!authHeader) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Unauthorized' }));
                return;
            }

            const token = authHeader.replace('Bearer ', '');
            const githubToken = tokenStore.get(token);

            if (!githubToken) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid token' }));
                return;
            }

            try {
                const githubRepos = await githubRequest('/user/repos?sort=updated&per_page=30', githubToken);
                const repos = githubRepos.map(repo => ({
                    id: repo.id,
                    name: repo.name,
                    full_name: repo.full_name,
                    description: repo.description,
                    language: repo.language,
                    stars_count: repo.stargazers_count,
                    forks_count: repo.forks_count,
                    open_issues_count: repo.open_issues_count,
                    default_branch: repo.default_branch,
                    private: repo.private,
                    html_url: repo.html_url,
                    created_at: repo.created_at,
                    updated_at: repo.updated_at,
                    analysis_status: 'pending'
                }));

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(repos));
            } catch (error) {
                console.error('Error fetching repos:', error);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Failed to fetch repositories' }));
            }
            return;
        }

        // Get single repository
        if (path.match(/\/api\/repos\/\d+$/)) {
            const authHeader = req.headers.authorization;
            if (!authHeader) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Unauthorized' }));
                return;
            }

            const token = authHeader.replace('Bearer ', '');
            const githubToken = tokenStore.get(token);

            if (!githubToken) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid token' }));
                return;
            }

            const repoId = parseInt(path.split('/').pop());

            try {
                // First get all repos to find the one with matching ID
                const githubRepos = await githubRequest('/user/repos?per_page=100', githubToken);
                const repo = githubRepos.find(r => r.id === repoId);

                if (!repo) {
                    res.writeHead(404, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Repository not found' }));
                    return;
                }

                const repoData = {
                    id: repo.id,
                    name: repo.name,
                    full_name: repo.full_name,
                    description: repo.description,
                    language: repo.language,
                    stars_count: repo.stargazers_count,
                    forks_count: repo.forks_count,
                    open_issues_count: repo.open_issues_count,
                    default_branch: repo.default_branch,
                    private: repo.private,
                    html_url: repo.html_url,
                    created_at: repo.created_at,
                    updated_at: repo.updated_at,
                    analysis_status: 'pending'
                };

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(repoData));
            } catch (error) {
                console.error('Error fetching repo:', error);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Failed to fetch repository' }));
            }
            return;
        }

        // Chat Session endpoints
        if (path === '/api/chat/sessions' && req.method === 'POST') {
            let body = '';
            req.on('data', chunk => body += chunk);
            req.on('end', async () => {
                try {
                    const data = JSON.parse(body);
                    const sessionId = Date.now();

                    chatSessions.set(sessionId, {
                        userId: data.user_id,
                        repoId: data.repo_id,
                        title: data.title || 'New Chat',
                        messages: [],
                        createdAt: new Date().toISOString()
                    });

                    res.writeHead(201, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ session_id: sessionId }));
                } catch (error) {
                    res.writeHead(400, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Invalid request' }));
                }
            });
            return;
        }

        // Get chat messages
        if (path.match(/\/api\/chat\/sessions\/\d+\/messages$/)) {
            const sessionId = parseInt(path.split('/')[4]);
            const session = chatSessions.get(sessionId);

            if (!session) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Session not found' }));
                return;
            }

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(session.messages));
            return;
        }
        // PART 5 of 6

        // Send chat message with real AI
        if (path === '/api/chat/message' && req.method === 'POST') {
            const authHeader = req.headers.authorization;
            if (!authHeader) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Unauthorized' }));
                return;
            }

            const token = authHeader.replace('Bearer ', '');
            const githubToken = tokenStore.get(token);

            if (!githubToken) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid token' }));
                return;
            }

            let body = '';
            req.on('data', chunk => body += chunk);
            req.on('end', async () => {
                try {
                    const data = JSON.parse(body);
                    const session = chatSessions.get(data.session_id);

                    if (!session) {
                        res.writeHead(404, { 'Content-Type': 'application/json' });
                        res.end(JSON.stringify({ error: 'Session not found' }));
                        return;
                    }

                    // Build context from repository if available
                    let context = 'You are an expert AI coding assistant helping developers understand their GitHub repositories.';

                    if (session.repoId) {
                        // Fetch repo details
                        const repos = await githubRequest('/user/repos?per_page=100', githubToken);
                        const repo = repos.find(r => r.id === session.repoId);

                        if (repo) {
                            context += `\n\nRepository Context:\n- Name: ${repo.name}\n- Description: ${repo.description || 'No description'}\n- Language: ${repo.language || 'Unknown'}\n- Stars: ${repo.stargazers_count}\n`;

                            // Try to fetch README for additional context
                            const [owner, repoName] = repo.full_name.split('/');
                            const readme = await fetchRepoReadme(owner, repoName, githubToken);
                            if (readme) {
                                context += `\nREADME Summary:\n${readme.substring(0, 1000)}...`;
                            }

                            // -----------------------
                            // Add commit & PR activity
                            // -----------------------
                            try {
                                // Recent commits
                                const commits = await fetchRepoCommits(owner, repoName, githubToken);
                                if (commits && commits.length > 0) {
                                    context += `\n\nRecent Commits:\n`;
                                    commits.slice(0, 5).forEach(c => {
                                        const authorName = (c && c.commit && c.commit.author && c.commit.author.name) ? c.commit.author.name : (c.author && c.author.login) || 'unknown';
                                        const date = (c && c.commit && c.commit.author && c.commit.author.date) ? c.commit.author.date : 'unknown';
                                        const message = (c && c.commit && c.commit.message) ? c.commit.message.split('\n')[0] : 'no message';
                                        context += `- ${message} (by ${authorName}, ${date})\n`;
                                    });
                                }

                                // Recent PRs and file changes
                                const prs = await fetchRepoPullRequests(owner, repoName, githubToken);
                                if (prs && prs.length > 0) {
                                    context += `\n\nRecent Pull Requests:\n`;
                                    for (const pr of prs.slice(0, 5)) {
                                        const prNumber = pr.number;
                                        const prTitle = pr.title || '';
                                        const prState = pr.state || '';
                                        const prAuthor = (pr.user && pr.user.login) ? pr.user.login : 'unknown';
                                        const prMerged = pr.merged_at ? true : false;
                                        const prCreated = pr.created_at || 'unknown';
                                        const prUpdated = pr.updated_at || 'unknown';

                                        context += `\nPR #${prNumber}: ${prTitle}\nState: ${prState}\nAuthor: ${prAuthor}\nCreated: ${prCreated}\nUpdated: ${prUpdated}\nMerged: ${prMerged ? 'Yes' : 'No'}\n`;

                                        // Fetch changes for this PR
                                        try {
                                            const changes = await fetchPullRequestChanges(owner, repoName, prNumber, githubToken);
                                            if (changes && changes.length > 0) {
                                                context += `Changed Files:\n`;
                                                changes.slice(0, 20).forEach(file => {
                                                    const fname = file.filename || file.path || 'unknown';
                                                    const additions = typeof file.additions === 'number' ? file.additions : 0;
                                                    const deletions = typeof file.deletions === 'number' ? file.deletions : 0;
                                                    context += `- ${fname} (+${additions}/-${deletions})\n`;
                                                });
                                            }
                                        } catch (err) {
                                            console.warn('Failed to fetch PR changes for PR', prNumber, err && err.message);
                                        }
                                    }
                                }
                            } catch (err) {
                                console.warn('Error assembling commit/PR context:', err && err.message);
                            }
                        }
                    }

                    // Add conversation history
                    if (session.messages.length > 0) {
                        context += '\n\nPrevious conversation:\n';
                        session.messages.slice(-5).forEach(msg => {
                            context += `${msg.role}: ${msg.content}\n`;
                        });
                    }

                    // Get AI response
                    const aiResponse = await callGemini(data.message, context);

                    // Store messages
                    session.messages.push({
                        role: 'user',
                        content: data.message,
                        created_at: new Date().toISOString()
                    });

                    session.messages.push({
                        role: 'assistant',
                        content: aiResponse,
                        created_at: new Date().toISOString()
                    });

                    res.writeHead(200, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ response: aiResponse }));
                } catch (error) {
                    console.error('Chat error:', error);
                    res.writeHead(500, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({
                        response: 'Sorry, I encountered an error processing your request. Please try again.'
                    }));
                }
            });
            return;
        }
        // PART 6 of 6

        // Repository Analysis endpoint
        if (path.match(/\/api\/repos\/\d+\/analyze$/) && req.method === 'POST') {
            const authHeader = req.headers.authorization;
            if (!authHeader) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Unauthorized' }));
                return;
            }

            const token = authHeader.replace('Bearer ', '');
            const githubToken = tokenStore.get(token);

            if (!githubToken) {
                res.writeHead(401, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({ error: 'Invalid token' }));
                return;
            }

            const repoId = parseInt(path.split('/')[3]);

            try {
                const repos = await githubRequest('/user/repos?per_page=100', githubToken);
                const repo = repos.find(r => r.id === repoId);

                if (!repo) {
                    res.writeHead(404, { 'Content-Type': 'application/json' });
                    res.end(JSON.stringify({ error: 'Repository not found' }));
                    return;
                }

                // Build analysis prompt
                const [owner, repoName] = repo.full_name.split('/');
                const readme = await fetchRepoReadme(owner, repoName, githubToken);

                // Fetch important files (content included)
                const importantFiles = await fetchImportantFiles(owner, repoName, githubToken);

                let analysisPrompt = `Analyze this GitHub repository and provide insights:\n\nRepository: ${repo.name}\nDescription: ${repo.description || 'No description'}\nLanguage: ${repo.language}\n`;

                if (readme) {
                    analysisPrompt += `\nREADME:\n${readme.substring(0, 2000)}\n`;
                }

                // Include important files and contents
                if (importantFiles && importantFiles.length > 0) {
                    analysisPrompt += `\nImportant Files (${importantFiles.length}):\n`;
                    importantFiles.forEach(f => {
                        analysisPrompt += `\n\n=== FILE: ${f.name} ===\n${f.content}\n`;
                    });
                } else {
                    // Fallback to listing top-level names if no important files found
                    const files = await fetchRepoFiles(owner, repoName, githubToken);
                    if (files && files.length > 0) {
                        analysisPrompt += `\nFile Structure:\n${files.map(f => f.name).slice(0, 20).join(', ')}\n`;
                    }
                }

                // Optionally include recent commits and PRs summary in analysis prompt for deeper insights
                try {
                    const commits = await fetchRepoCommits(owner, repoName, githubToken);
                    if (commits && commits.length > 0) {
                        analysisPrompt += `\n\nRecent Commits Summary:\n`;
                        commits.slice(0, 5).forEach(c => {
                            const authorName = (c && c.commit && c.commit.author && c.commit.author.name) ? c.commit.author.name : (c.author && c.author.login) || 'unknown';
                            const date = (c && c.commit && c.commit.author && c.commit.author.date) ? c.commit.author.date : 'unknown';
                            const message = (c && c.commit && c.commit.message) ? c.commit.message.split('\n')[0] : 'no message';
                            analysisPrompt += `- ${message} (by ${authorName}, ${date})\n`;
                        });
                    }

                    const prs = await fetchRepoPullRequests(owner, repoName, githubToken);
                    if (prs && prs.length > 0) {
                        analysisPrompt += `\n\nRecent Pull Requests Summary:\n`;
                        for (const pr of prs.slice(0, 5)) {
                            analysisPrompt += `- PR #${pr.number}: ${pr.title} (state: ${pr.state}, author: ${pr.user && pr.user.login ? pr.user.login : 'unknown'}, merged: ${pr.merged_at ? 'yes' : 'no'})\n`;
                        }
                    }
                } catch (err) {
                    console.warn('Failed to append commits/PRs to analysis prompt:', err && err.message);
                }

                analysisPrompt += `\nProvide a comprehensive analysis including:\n1. Code quality assessment (score 1-10)\n2. Architecture overview\n3. Security considerations\n4. Performance insights\n5. Suggested improvements`;

                const analysis = await callGemini(analysisPrompt);

                const result = {
                    repo_id: repoId,
                    analysis: analysis,
                    generated_at: new Date().toISOString(),
                    status: 'completed'
                };

                analysisCache.set(repoId, result);

                res.writeHead(200, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify(result));
            } catch (error) {
                console.error('Analysis error:', error);
                res.writeHead(500, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    error: 'Failed to analyze repository',
                    details: error.message
                }));
            }
            return;
        }

        // Get analysis results
        if (path.match(/\/api\/analysis\/\d+$/)) {
            const repoId = parseInt(path.split('/').pop());
            const analysis = analysisCache.get(repoId);

            if (!analysis) {
                res.writeHead(404, { 'Content-Type': 'application/json' });
                res.end(JSON.stringify({
                    status: 'not_analyzed',
                    message: 'No analysis available. Please trigger analysis first.'
                }));
                return;
            }

            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(analysis));
            return;
        }

        // Not found
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Not found' }));

    } catch (error) {
        console.error('Server error:', error);
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Internal server error' }));
    }
});

server.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log(`🚀 GitPro Enhanced Backend with Real GitHub Data`);
    console.log('='.repeat(60));
    console.log(`✅ Server running on http://localhost:${PORT}`);
    console.log(`✅ GitHub OAuth configured`);
    console.log(`✅ Ready to authenticate with your GitHub account`);
    console.log('='.repeat(60));
    console.log('\n📝 Next steps:');
    console.log('1. Open http://localhost:3000 in your browser');
    console.log('2. Click "CONNECT_TO_GITHUB"');
    console.log('3. Authorize the app on GitHub');
    console.log('4. See YOUR real repositories!\n');
});
