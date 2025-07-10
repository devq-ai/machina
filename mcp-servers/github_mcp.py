#!/usr/bin/env python3
"""
GitHub MCP Server
Provides GitHub repository management, issues, PRs, and project operations using FastMCP.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    import httpx
    from github import Github
    from github.GithubException import GithubException
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    Github = None
    GithubException = Exception


class GitHubMCP:
    """
    GitHub MCP Server using FastMCP framework

    Provides comprehensive GitHub operations including:
    - Repository management
    - Issue tracking
    - Pull request operations
    - Project management
    - User and organization management
    """

    def __init__(self):
        self.mcp = FastMCP("github-mcp", version="1.0.0", description="GitHub operations and repository management")
        self.github_client: Optional[Github] = None
        self.token = os.getenv("GITHUB_TOKEN") or os.getenv("GITHUB_PAT")
        self._setup_tools()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize GitHub client"""
        if not GITHUB_AVAILABLE:
            logfire.warning("GitHub dependencies not available. Install with: pip install PyGithub httpx")
            return

        if self.token:
            try:
                self.github_client = Github(self.token)
                # Test connection
                user = self.github_client.get_user()
                logfire.info(f"GitHub client initialized for user: {user.login}")
            except Exception as e:
                logfire.error(f"Failed to initialize GitHub client: {str(e)}")
        else:
            logfire.warning("GitHub token not provided. Set GITHUB_TOKEN or GITHUB_PAT environment variable")

    def _setup_tools(self):
        """Setup GitHub MCP tools"""

        @self.mcp.tool(
            name="get_user_info",
            description="Get information about the authenticated user or specified user",
            input_schema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username to get info for (optional, defaults to authenticated user)"}
                }
            }
        )
        async def get_user_info(username: str = "") -> Dict[str, Any]:
            """Get user information"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                if username:
                    user = self.github_client.get_user(username)
                else:
                    user = self.github_client.get_user()

                return {
                    "login": user.login,
                    "name": user.name,
                    "email": user.email,
                    "company": user.company,
                    "location": user.location,
                    "bio": user.bio,
                    "public_repos": user.public_repos,
                    "followers": user.followers,
                    "following": user.following,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "avatar_url": user.avatar_url,
                    "html_url": user.html_url
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="list_repositories",
            description="List repositories for the authenticated user or specified user/organization",
            input_schema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "Username or organization (optional)"},
                    "type": {"type": "string", "enum": ["all", "owner", "member"], "description": "Repository type filter"},
                    "sort": {"type": "string", "enum": ["created", "updated", "pushed", "full_name"], "description": "Sort order"},
                    "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Results per page"}
                }
            }
        )
        async def list_repositories(username: str = "", type: str = "all", sort: str = "updated", per_page: int = 30) -> Dict[str, Any]:
            """List repositories"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                if username:
                    user = self.github_client.get_user(username)
                    repos = user.get_repos(type=type, sort=sort)
                else:
                    repos = self.github_client.get_user().get_repos(type=type, sort=sort)

                repositories = []
                for i, repo in enumerate(repos):
                    if i >= per_page:
                        break

                    repositories.append({
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "description": repo.description,
                        "private": repo.private,
                        "html_url": repo.html_url,
                        "clone_url": repo.clone_url,
                        "language": repo.language,
                        "stargazers_count": repo.stargazers_count,
                        "forks_count": repo.forks_count,
                        "open_issues_count": repo.open_issues_count,
                        "created_at": repo.created_at.isoformat() if repo.created_at else None,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                        "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None
                    })

                return {
                    "repositories": repositories,
                    "total_count": len(repositories)
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="get_repository",
            description="Get detailed information about a specific repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format 'owner/repo'"}
                },
                "required": ["repo_name"]
            }
        )
        async def get_repository(repo_name: str) -> Dict[str, Any]:
            """Get repository details"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                repo = self.github_client.get_repo(repo_name)

                return {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description,
                    "private": repo.private,
                    "html_url": repo.html_url,
                    "clone_url": repo.clone_url,
                    "ssh_url": repo.ssh_url,
                    "language": repo.language,
                    "stargazers_count": repo.stargazers_count,
                    "watchers_count": repo.watchers_count,
                    "forks_count": repo.forks_count,
                    "open_issues_count": repo.open_issues_count,
                    "size": repo.size,
                    "default_branch": repo.default_branch,
                    "topics": list(repo.get_topics()),
                    "license": repo.license.name if repo.license else None,
                    "created_at": repo.created_at.isoformat() if repo.created_at else None,
                    "updated_at": repo.updated_at.isoformat() if repo.updated_at else None,
                    "pushed_at": repo.pushed_at.isoformat() if repo.pushed_at else None,
                    "has_issues": repo.has_issues,
                    "has_projects": repo.has_projects,
                    "has_wiki": repo.has_wiki,
                    "archived": repo.archived,
                    "disabled": repo.disabled
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="list_issues",
            description="List issues for a repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format 'owner/repo'"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "Issue state filter"},
                    "labels": {"type": "string", "description": "Comma-separated list of label names"},
                    "sort": {"type": "string", "enum": ["created", "updated", "comments"], "description": "Sort field"},
                    "direction": {"type": "string", "enum": ["asc", "desc"], "description": "Sort direction"},
                    "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Results per page"}
                },
                "required": ["repo_name"]
            }
        )
        async def list_issues(repo_name: str, state: str = "open", labels: str = "",
                            sort: str = "created", direction: str = "desc", per_page: int = 30) -> Dict[str, Any]:
            """List repository issues"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                repo = self.github_client.get_repo(repo_name)

                # Parse labels
                label_list = [l.strip() for l in labels.split(",")] if labels else []

                issues = repo.get_issues(
                    state=state,
                    labels=label_list,
                    sort=sort,
                    direction=direction
                )

                issue_list = []
                for i, issue in enumerate(issues):
                    if i >= per_page:
                        break

                    issue_list.append({
                        "number": issue.number,
                        "title": issue.title,
                        "body": issue.body,
                        "state": issue.state,
                        "user": issue.user.login,
                        "assignees": [a.login for a in issue.assignees],
                        "labels": [l.name for l in issue.labels],
                        "comments": issue.comments,
                        "html_url": issue.html_url,
                        "created_at": issue.created_at.isoformat() if issue.created_at else None,
                        "updated_at": issue.updated_at.isoformat() if issue.updated_at else None,
                        "closed_at": issue.closed_at.isoformat() if issue.closed_at else None
                    })

                return {
                    "issues": issue_list,
                    "total_count": len(issue_list)
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="create_issue",
            description="Create a new issue in a repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format 'owner/repo'"},
                    "title": {"type": "string", "description": "Issue title"},
                    "body": {"type": "string", "description": "Issue description"},
                    "assignees": {"type": "array", "items": {"type": "string"}, "description": "List of usernames to assign"},
                    "labels": {"type": "array", "items": {"type": "string"}, "description": "List of label names"}
                },
                "required": ["repo_name", "title"]
            }
        )
        async def create_issue(repo_name: str, title: str, body: str = "",
                             assignees: List[str] = None, labels: List[str] = None) -> Dict[str, Any]:
            """Create a new issue"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                repo = self.github_client.get_repo(repo_name)

                issue = repo.create_issue(
                    title=title,
                    body=body,
                    assignees=assignees or [],
                    labels=labels or []
                )

                return {
                    "number": issue.number,
                    "title": issue.title,
                    "html_url": issue.html_url,
                    "state": issue.state,
                    "created_at": issue.created_at.isoformat() if issue.created_at else None
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="list_pull_requests",
            description="List pull requests for a repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format 'owner/repo'"},
                    "state": {"type": "string", "enum": ["open", "closed", "all"], "description": "PR state filter"},
                    "base": {"type": "string", "description": "Base branch name"},
                    "head": {"type": "string", "description": "Head branch name"},
                    "sort": {"type": "string", "enum": ["created", "updated", "popularity"], "description": "Sort field"},
                    "direction": {"type": "string", "enum": ["asc", "desc"], "description": "Sort direction"},
                    "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Results per page"}
                },
                "required": ["repo_name"]
            }
        )
        async def list_pull_requests(repo_name: str, state: str = "open", base: str = "", head: str = "",
                                   sort: str = "created", direction: str = "desc", per_page: int = 30) -> Dict[str, Any]:
            """List repository pull requests"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                repo = self.github_client.get_repo(repo_name)

                pulls = repo.get_pulls(
                    state=state,
                    base=base if base else None,
                    head=head if head else None,
                    sort=sort,
                    direction=direction
                )

                pr_list = []
                for i, pr in enumerate(pulls):
                    if i >= per_page:
                        break

                    pr_list.append({
                        "number": pr.number,
                        "title": pr.title,
                        "body": pr.body,
                        "state": pr.state,
                        "user": pr.user.login,
                        "head": {
                            "ref": pr.head.ref,
                            "sha": pr.head.sha,
                            "repo": pr.head.repo.full_name if pr.head.repo else None
                        },
                        "base": {
                            "ref": pr.base.ref,
                            "sha": pr.base.sha,
                            "repo": pr.base.repo.full_name
                        },
                        "mergeable": pr.mergeable,
                        "merged": pr.merged,
                        "draft": pr.draft,
                        "html_url": pr.html_url,
                        "created_at": pr.created_at.isoformat() if pr.created_at else None,
                        "updated_at": pr.updated_at.isoformat() if pr.updated_at else None,
                        "merged_at": pr.merged_at.isoformat() if pr.merged_at else None
                    })

                return {
                    "pull_requests": pr_list,
                    "total_count": len(pr_list)
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="create_pull_request",
            description="Create a new pull request",
            input_schema={
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Repository name in format 'owner/repo'"},
                    "title": {"type": "string", "description": "PR title"},
                    "head": {"type": "string", "description": "Head branch (source)"},
                    "base": {"type": "string", "description": "Base branch (target)"},
                    "body": {"type": "string", "description": "PR description"},
                    "draft": {"type": "boolean", "description": "Create as draft PR"}
                },
                "required": ["repo_name", "title", "head", "base"]
            }
        )
        async def create_pull_request(repo_name: str, title: str, head: str, base: str,
                                    body: str = "", draft: bool = False) -> Dict[str, Any]:
            """Create a new pull request"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                repo = self.github_client.get_repo(repo_name)

                pr = repo.create_pull(
                    title=title,
                    body=body,
                    head=head,
                    base=base,
                    draft=draft
                )

                return {
                    "number": pr.number,
                    "title": pr.title,
                    "html_url": pr.html_url,
                    "state": pr.state,
                    "draft": pr.draft,
                    "created_at": pr.created_at.isoformat() if pr.created_at else None
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="search_repositories",
            description="Search for repositories on GitHub",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "sort": {"type": "string", "enum": ["stars", "forks", "help-wanted-issues", "updated"], "description": "Sort field"},
                    "order": {"type": "string", "enum": ["asc", "desc"], "description": "Sort order"},
                    "per_page": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Results per page"}
                },
                "required": ["query"]
            }
        )
        async def search_repositories(query: str, sort: str = "stars", order: str = "desc", per_page: int = 30) -> Dict[str, Any]:
            """Search repositories"""
            if not self._check_client():
                return {"error": "GitHub client not initialized"}

            try:
                repos = self.github_client.search_repositories(
                    query=query,
                    sort=sort,
                    order=order
                )

                repo_list = []
                for i, repo in enumerate(repos):
                    if i >= per_page:
                        break

                    repo_list.append({
                        "name": repo.name,
                        "full_name": repo.full_name,
                        "description": repo.description,
                        "html_url": repo.html_url,
                        "language": repo.language,
                        "stargazers_count": repo.stargazers_count,
                        "forks_count": repo.forks_count,
                        "open_issues_count": repo.open_issues_count,
                        "owner": repo.owner.login,
                        "created_at": repo.created_at.isoformat() if repo.created_at else None,
                        "updated_at": repo.updated_at.isoformat() if repo.updated_at else None
                    })

                return {
                    "repositories": repo_list,
                    "total_count": repos.totalCount,
                    "results_returned": len(repo_list)
                }
            except GithubException as e:
                return {"error": f"GitHub API error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

    def _check_client(self) -> bool:
        """Check if GitHub client is available and initialized"""
        if not GITHUB_AVAILABLE:
            return False
        return self.github_client is not None

    async def run(self):
        """Run the GitHub MCP server"""
        await self.mcp.run_stdio()


async def main():
    """Main entry point"""
    server = GitHubMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
