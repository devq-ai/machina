#!/usr/bin/env python3
"""
GitHub MCP Server - Production Implementation
Provides GitHub repository operations including repos, issues, PRs, and more.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import base64

try:
    from github import Github, GithubException
    from github.Repository import Repository
    from github.PullRequest import PullRequest
    from github.Issue import Issue
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call(["pip", "install", "PyGithub"])
    from github import Github, GithubException
    from github.Repository import Repository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"


class MCPError:
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class GitHubClient:
    """GitHub API client wrapper"""

    def __init__(self, token: Optional[str] = None):
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise ValueError("GitHub token is required")

        self.github = Github(self.token)
        self.user = self.github.get_user()

    async def list_repositories(self, user: Optional[str] = None,
                              organization: Optional[str] = None,
                              visibility: Optional[str] = None) -> List[Dict[str, Any]]:
        """List repositories"""
        try:
            repos = []

            if organization:
                org = self.github.get_organization(organization)
                repo_list = org.get_repos()
            elif user:
                u = self.github.get_user(user)
                repo_list = u.get_repos()
            else:
                repo_list = self.user.get_repos()

            for repo in repo_list:
                if visibility and repo.visibility != visibility:
                    continue

                repos.append({
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "fork": repo.fork,
                    "created_at": repo.created_at.isoformat(),
                    "updated_at": repo.updated_at.isoformat(),
                    "language": repo.language,
                    "stars": repo.stargazers_count,
                    "forks": repo.forks_count,
                    "default_branch": repo.default_branch
                })

            return repos
        except GithubException as e:
            logger.error(f"Error listing repositories: {e}")
            raise

    async def create_repository(self, name: str, description: Optional[str] = None,
                              private: bool = False, auto_init: bool = True) -> Dict[str, Any]:
        """Create a new repository"""
        try:
            repo = self.user.create_repo(
                name=name,
                description=description,
                private=private,
                auto_init=auto_init
            )

            return {
                "name": repo.name,
                "full_name": repo.full_name,
                "url": repo.html_url,
                "clone_url": repo.clone_url,
                "created": True
            }
        except GithubException as e:
            logger.error(f"Error creating repository: {e}")
            raise

    async def get_repository(self, owner: str, repo: str) -> Repository:
        """Get a specific repository"""
        try:
            return self.github.get_repo(f"{owner}/{repo}")
        except GithubException as e:
            logger.error(f"Error getting repository: {e}")
            raise

    async def list_issues(self, owner: str, repo: str, state: str = "open",
                        labels: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List repository issues"""
        try:
            repository = await self.get_repository(owner, repo)
            issues = []

            issue_list = repository.get_issues(state=state, labels=labels)

            for issue in issue_list:
                if issue.pull_request:  # Skip PRs
                    continue

                issues.append({
                    "number": issue.number,
                    "title": issue.title,
                    "body": issue.body,
                    "state": issue.state,
                    "created_at": issue.created_at.isoformat(),
                    "updated_at": issue.updated_at.isoformat(),
                    "user": issue.user.login,
                    "labels": [label.name for label in issue.labels],
                    "assignees": [assignee.login for assignee in issue.assignees],
                    "comments": issue.comments
                })

            return issues
        except GithubException as e:
            logger.error(f"Error listing issues: {e}")
            raise

    async def create_issue(self, owner: str, repo: str, title: str,
                         body: Optional[str] = None, labels: Optional[List[str]] = None,
                         assignees: Optional[List[str]] = None) -> Dict[str, Any]:
        """Create a new issue"""
        try:
            repository = await self.get_repository(owner, repo)

            issue = repository.create_issue(
                title=title,
                body=body,
                labels=labels,
                assignees=assignees
            )

            return {
                "number": issue.number,
                "title": issue.title,
                "url": issue.html_url,
                "created": True
            }
        except GithubException as e:
            logger.error(f"Error creating issue: {e}")
            raise

    async def list_pull_requests(self, owner: str, repo: str, state: str = "open") -> List[Dict[str, Any]]:
        """List pull requests"""
        try:
            repository = await self.get_repository(owner, repo)
            prs = []

            pr_list = repository.get_pulls(state=state)

            for pr in pr_list:
                prs.append({
                    "number": pr.number,
                    "title": pr.title,
                    "body": pr.body,
                    "state": pr.state,
                    "created_at": pr.created_at.isoformat(),
                    "updated_at": pr.updated_at.isoformat(),
                    "user": pr.user.login,
                    "head": pr.head.ref,
                    "base": pr.base.ref,
                    "mergeable": pr.mergeable,
                    "merged": pr.merged,
                    "commits": pr.commits,
                    "additions": pr.additions,
                    "deletions": pr.deletions,
                    "changed_files": pr.changed_files
                })

            return prs
        except GithubException as e:
            logger.error(f"Error listing pull requests: {e}")
            raise

    async def create_pull_request(self, owner: str, repo: str, title: str,
                                head: str, base: str, body: Optional[str] = None,
                                draft: bool = False) -> Dict[str, Any]:
        """Create a pull request"""
        try:
            repository = await self.get_repository(owner, repo)

            pr = repository.create_pull(
                title=title,
                body=body,
                head=head,
                base=base,
                draft=draft
            )

            return {
                "number": pr.number,
                "title": pr.title,
                "url": pr.html_url,
                "created": True
            }
        except GithubException as e:
            logger.error(f"Error creating pull request: {e}")
            raise

    async def get_file_contents(self, owner: str, repo: str, path: str,
                              ref: Optional[str] = None) -> Dict[str, Any]:
        """Get file contents"""
        try:
            repository = await self.get_repository(owner, repo)

            contents = repository.get_contents(path, ref=ref)

            if not contents.content:
                return {
                    "path": path,
                    "type": contents.type,
                    "size": contents.size
                }

            decoded_content = base64.b64decode(contents.content).decode('utf-8')

            return {
                "path": contents.path,
                "name": contents.name,
                "size": contents.size,
                "content": decoded_content,
                "sha": contents.sha,
                "download_url": contents.download_url
            }
        except GithubException as e:
            logger.error(f"Error getting file contents: {e}")
            raise

    async def create_or_update_file(self, owner: str, repo: str, path: str,
                                  message: str, content: str, branch: Optional[str] = None,
                                  sha: Optional[str] = None) -> Dict[str, Any]:
        """Create or update a file"""
        try:
            repository = await self.get_repository(owner, repo)

            # Get current file SHA if updating
            if not sha:
                try:
                    existing = repository.get_contents(path, ref=branch)
                    sha = existing.sha
                except:
                    pass  # File doesn't exist, will create

            if sha:
                # Update existing file
                result = repository.update_file(
                    path=path,
                    message=message,
                    content=content,
                    sha=sha,
                    branch=branch
                )
            else:
                # Create new file
                result = repository.create_file(
                    path=path,
                    message=message,
                    content=content,
                    branch=branch
                )

            return {
                "path": path,
                "sha": result['content'].sha,
                "commit": result['commit'].sha,
                "created": sha is None,
                "updated": sha is not None
            }
        except GithubException as e:
            logger.error(f"Error creating/updating file: {e}")
            raise

    async def list_branches(self, owner: str, repo: str) -> List[Dict[str, Any]]:
        """List repository branches"""
        try:
            repository = await self.get_repository(owner, repo)
            branches = []

            for branch in repository.get_branches():
                branches.append({
                    "name": branch.name,
                    "protected": branch.protected,
                    "commit_sha": branch.commit.sha,
                    "commit_url": branch.commit.url
                })

            return branches
        except GithubException as e:
            logger.error(f"Error listing branches: {e}")
            raise

    async def list_commits(self, owner: str, repo: str, sha: Optional[str] = None,
                         path: Optional[str] = None, author: Optional[str] = None) -> List[Dict[str, Any]]:
        """List commits"""
        try:
            repository = await self.get_repository(owner, repo)
            commits = []

            commit_list = repository.get_commits(sha=sha, path=path, author=author)

            for commit in commit_list[:20]:  # Limit to 20 commits
                commits.append({
                    "sha": commit.sha,
                    "message": commit.commit.message,
                    "author": commit.commit.author.name,
                    "author_email": commit.commit.author.email,
                    "date": commit.commit.author.date.isoformat(),
                    "url": commit.html_url,
                    "additions": commit.stats.additions,
                    "deletions": commit.stats.deletions,
                    "total": commit.stats.total
                })

            return commits
        except GithubException as e:
            logger.error(f"Error listing commits: {e}")
            raise


class GitHubMCPServer:
    """GitHub MCP Server implementation"""

    def __init__(self):
        self.client: Optional[GitHubClient] = None
        self.server_info = {
            "name": "github-mcp",
            "version": "1.0.0",
            "description": "GitHub repository operations MCP server",
            "author": "DevQ.ai Team"
        }

    async def initialize(self):
        """Initialize the server"""
        try:
            self.client = GitHubClient()
            logger.info("GitHub MCP Server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            self.client = None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": "list_repos",
                "description": "List GitHub repositories",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user": {"type": "string", "description": "Username (optional)"},
                        "organization": {"type": "string", "description": "Organization name (optional)"},
                        "visibility": {"type": "string", "enum": ["public", "private"], "description": "Filter by visibility"}
                    }
                }
            },
            {
                "name": "create_repo",
                "description": "Create a new repository",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Repository name"},
                        "description": {"type": "string", "description": "Repository description"},
                        "private": {"type": "boolean", "description": "Make repository private"},
                        "auto_init": {"type": "boolean", "description": "Initialize with README"}
                    },
                    "required": ["name"]
                }
            },
            {
                "name": "list_issues",
                "description": "List repository issues",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue state"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Filter by labels"}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "create_issue",
                "description": "Create a new issue",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "Issue title"},
                        "body": {"type": "string", "description": "Issue body"},
                        "labels": {"type": "array", "items": {"type": "string"}, "description": "Issue labels"},
                        "assignees": {"type": "array", "items": {"type": "string"}, "description": "Assignees"}
                    },
                    "required": ["owner", "repo", "title"]
                }
            },
            {
                "name": "list_pull_requests",
                "description": "List pull requests",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "PR state"}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "create_pull_request",
                "description": "Create a pull request",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "title": {"type": "string", "description": "PR title"},
                        "head": {"type": "string", "description": "Head branch"},
                        "base": {"type": "string", "description": "Base branch"},
                        "body": {"type": "string", "description": "PR body"},
                        "draft": {"type": "boolean", "description": "Create as draft"}
                    },
                    "required": ["owner", "repo", "title", "head", "base"]
                }
            },
            {
                "name": "get_file",
                "description": "Get file contents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "path": {"type": "string", "description": "File path"},
                        "ref": {"type": "string", "description": "Branch/tag/commit (optional)"}
                    },
                    "required": ["owner", "repo", "path"]
                }
            },
            {
                "name": "create_or_update_file",
                "description": "Create or update a file",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "path": {"type": "string", "description": "File path"},
                        "message": {"type": "string", "description": "Commit message"},
                        "content": {"type": "string", "description": "File content"},
                        "branch": {"type": "string", "description": "Target branch"},
                        "sha": {"type": "string", "description": "SHA of file being replaced"}
                    },
                    "required": ["owner", "repo", "path", "message", "content"]
                }
            },
            {
                "name": "list_branches",
                "description": "List repository branches",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"}
                    },
                    "required": ["owner", "repo"]
                }
            },
            {
                "name": "list_commits",
                "description": "List repository commits",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string", "description": "Repository owner"},
                        "repo": {"type": "string", "description": "Repository name"},
                        "sha": {"type": "string", "description": "SHA or branch name"},
                        "path": {"type": "string", "description": "Only commits for this path"},
                        "author": {"type": "string", "description": "Filter by author"}
                    },
                    "required": ["owner", "repo"]
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        if not self.client:
            return {"error": "GitHub client not initialized. Please provide GITHUB_TOKEN."}

        try:
            if tool_name == "list_repos":
                repos = await self.client.list_repositories(**arguments)
                return {"repositories": repos, "count": len(repos)}

            elif tool_name == "create_repo":
                result = await self.client.create_repository(**arguments)
                return result

            elif tool_name == "list_issues":
                issues = await self.client.list_issues(**arguments)
                return {"issues": issues, "count": len(issues)}

            elif tool_name == "create_issue":
                result = await self.client.create_issue(**arguments)
                return result

            elif tool_name == "list_pull_requests":
                prs = await self.client.list_pull_requests(**arguments)
                return {"pull_requests": prs, "count": len(prs)}

            elif tool_name == "create_pull_request":
                result = await self.client.create_pull_request(**arguments)
                return result

            elif tool_name == "get_file":
                result = await self.client.get_file_contents(**arguments)
                return result

            elif tool_name == "create_or_update_file":
                result = await self.client.create_or_update_file(**arguments)
                return result

            elif tool_name == "list_branches":
                branches = await self.client.list_branches(**arguments)
                return {"branches": branches, "count": len(branches)}

            elif tool_name == "list_commits":
                commits = await self.client.list_commits(**arguments)
                return {"commits": commits, "count": len(commits)}

            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                await self.initialize()
                result = {
                    "protocolVersion": MCP_VERSION,
                    "serverInfo": self.server_info,
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False,
                        "logging": False
                    },
                    "instructions": "GitHub MCP server for repository operations"
                }
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
            elif method == "health":
                result = {
                    "status": "healthy" if self.client else "no_auth",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "authenticated": self.client is not None
                }
            else:
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": request_id,
                    "error": {
                        "code": MCPError.METHOD_NOT_FOUND,
                        "message": f"Method not found: {method}"
                    }
                }

            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": MCPError.INTERNAL_ERROR,
                    "message": str(e)
                }
            }

    async def run_stdio(self):
        """Run the server in stdio mode"""
        logger.info("Starting GitHub MCP Server in stdio mode")

        try:
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )

                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Write response to stdout
                    print(json.dumps(response))

                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": None,
                        "error": {
                            "code": MCPError.PARSE_ERROR,
                            "message": f"Parse error: {e}"
                        }
                    }
                    print(json.dumps(error_response))

        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")


async def main():
    """Main entry point"""
    server = GitHubMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
