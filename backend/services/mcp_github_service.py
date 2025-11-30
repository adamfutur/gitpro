"""
MCP GitHub Service - Efficient GitHub operations using Model Context Protocol
"""
import os
import asyncio
from typing import List, Dict, Optional, Any
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPGitHubService:
    """
    GitHub service using MCP for efficient repository analysis.
    Uses the official MCP GitHub server for optimized API access.
    """
    
    def __init__(self, github_token: str):
        self.github_token = github_token
        self.session: Optional[ClientSession] = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize MCP GitHub server connection."""
        if self._initialized:
            return
        
        # Configure MCP GitHub server
        server_params = StdioServerParameters(
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-github",
            ],
            env={
                **os.environ,
                "GITHUB_PERSONAL_ACCESS_TOKEN": self.github_token
            }
        )
        
        try:
            # Start MCP client session
            self.stdio_transport = await stdio_client(server_params)
            self.session = self.stdio_transport[1]
            self._initialized = True
            print("✓ MCP GitHub server initialized")
        except Exception as e:
            print(f"⚠ MCP GitHub server initialization failed: {e}")
            raise
    
    async def close(self):
        """Close MCP session."""
        if self.session:
            await self.stdio_transport[0].__aexit__(None, None, None)
            self._initialized = False
    
    async def get_file_contents(self, owner: str, repo: str, paths: List[str]) -> List[Dict[str, str]]:
        """
        Get contents of multiple files efficiently using MCP.
        
        Args:
            owner: Repository owner
            repo: Repository name
            paths: List of file paths to fetch
            
        Returns:
            List of {path, content, name} dictionaries
        """
        await self.initialize()
        
        results = []
        for path in paths[:5]:  # Limit to 5 files for performance
            try:
                # Use MCP GitHub tool to get file contents
                result = await self.session.call_tool(
                    "get_file_contents",
                    arguments={
                        "owner": owner,
                        "repo": repo,
                        "path": path
                    }
                )
                
                # Extract content from response
                if result and result.content:
                    content = self._extract_content(result.content)
                    results.append({
                        'path': path,
                        'name': path.split('/')[-1],
                        'content': content[:8000]  # Limit content size
                    })
            except Exception as e:
                print(f"Error fetching {path}: {e}")
                continue
        
        return results
    
    async def list_repository_files(self, owner: str, repo: str, max_files: int = 5) -> List[str]:
        """
        List important repository files using MCP.
        
        Args:
            owner: Repository owner
            repo: Repository name
            max_files: Maximum number of files to return
            
        Returns:
            List of file paths (prioritized by importance)
        """
        await self.initialize()
        
        # Priority file patterns
        priority_files = [
            'README.md', 'package.json', 'requirements.txt', 
            'go.mod', 'Dockerfile', 'docker-compose.yml'
        ]
        
        important_extensions = ['.py', '.js', '.ts', '.go', '.rs', '.java', '.tsx', '.jsx']
        
        try:
            # Search for files in repository
            result = await self.session.call_tool(
                "search_repositories",
                arguments={
                    "query": f"repo:{owner}/{repo}",
                    "type": "code"
                }
            )
            
            # Extract and prioritize files
            files = self._extract_files_from_search(result)
            prioritized = self._prioritize_files(files, priority_files, important_extensions)
            
            return prioritized[:max_files]
            
        except Exception as e:
            print(f"Error listing files: {e}")
            # Fallback to default important files
            return priority_files[:max_files]
    
    async def get_repository_tree(self, owner: str, repo: str) -> List[str]:
        """Get repository file tree using MCP."""
        await self.initialize()
        
        try:
            result = await self.session.call_tool(
                "list_commits",
                arguments={
                    "owner": owner,
                    "repo": repo,
                    "limit": 1
                }
            )
            
            # Use default important files for now
            # MCP GitHub server may not have direct tree API
            return [
                'README.md',
                'src/main.py',
                'app.py',
                'index.js',
                'main.go'
            ]
        except Exception as e:
            print(f"Error getting tree: {e}")
            return []
    
    def _extract_content(self, mcp_content: Any) -> str:
        """Extract text content from MCP response."""
        if isinstance(mcp_content, list):
            for item in mcp_content:
                if hasattr(item, 'text'):
                    return item.text
        elif hasattr(mcp_content, 'text'):
            return mcp_content.text
        return str(mcp_content)
    
    def _extract_files_from_search(self, result: Any) -> List[str]:
        """Extract file paths from MCP search result."""
        files = []
        # Implementation depends on MCP response format
        # For now, return empty list as fallback
        return files
    
    def _prioritize_files(self, files: List[str], priority: List[str], extensions: List[str]) -> List[str]:
        """Prioritize files based on importance."""
        prioritized = []
        
        # First, add priority files
        for pf in priority:
            if pf in files:
                prioritized.append(pf)
        
        # Then add files with important extensions
        for f in files:
            if f not in prioritized and any(f.endswith(ext) for ext in extensions):
                prioritized.append(f)
        
        return prioritized


# Synchronous wrapper for Flask compatibility
class MCPGitHubServiceSync:
    """Synchronous wrapper for MCP GitHub service."""
    
    def __init__(self, github_token: str):
        self.service = MCPGitHubService(github_token)
        self.loop = None
    
    def _get_loop(self):
        """Get or create event loop."""
        if self.loop is None:
            try:
                self.loop = asyncio.get_event_loop()
            except RuntimeError:
                self.loop = asyncio.new_event_loop()
                asyncio.set_event_loop(self.loop)
        return self.loop
    
    def get_important_files(self, owner: str, repo: str, max_files: int = 5) -> List[Dict[str, str]]:
        """
        Synchronous method to get important repository files.
        
        Args:
            owner: Repository owner
            repo: Repository name
            max_files: Maximum number of files
            
        Returns:
            List of {path, name, content} dictionaries
        """
        loop = self._get_loop()
        
        async def fetch():
            # Get file list
            file_paths = await self.service.list_repository_files(owner, repo, max_files)
            # Get file contents
            files = await self.service.get_file_contents(owner, repo, file_paths)
            await self.service.close()
            return files
        
        try:
            return loop.run_until_complete(fetch())
        except Exception as e:
            print(f"MCP fetch error: {e}")
            return []
    
    def close(self):
        """Close MCP session."""
        if self.loop:
            self.loop.run_until_complete(self.service.close())
