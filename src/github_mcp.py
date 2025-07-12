#!/usr/bin/env python
"""
GitHub MCP Server
FastMCP server for GitHub API integration using official patterns.
Provides repository management, issues, pull requests, and workflow operations.
"""
import asyncio
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import httpx
import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='github-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("github-mcp")

class GitHubClient:
    """GitHub API client using official patterns."""
    
    def __init__(self):
        self.token = os.getenv('GITHUB_PAT') or os.getenv('GITHUB_TOKEN')
        self.base_url = "https://api.github.com"
        self.default_org = os.getenv('GITHUB_DEFAULT_ORG', 'devq-ai')
        
        if not self.token:
            # logfire.warning("No GitHub token found in environment variables")
        
            pass
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make authenticated GitHub API request."""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self.headers,
                timeout=30.0,
                **kwargs
            )
            
            result = {
                "status_code": response.status_code,
                "success": response.status_code < 400,
                "url": str(response.url),
                "headers": dict(response.headers)
            }
            
            try:
                result["data"] = response.json()
            except Exception:
                result["data"] = response.text
            
            if not result["success"]:
                # logfire.error("GitHub API request failed", 
                #              method=method,
                #              endpoint=endpoint,
                #              status_code=response.status_code,
                #              response=result["data"])
                pass
            
            return result

github_client = GitHubClient()

@app.tool()
@logfire.instrument("github_health_check")
async def github_health_check() -> Dict[str, Any]:
    """Check GitHub API connectivity and authentication."""
    # logfire.info("GitHub health check requested")
    
    try:
        if not github_client.token:
            raise ValueError("GitHub token not configured")
        
        # Test API connectivity with user endpoint
        result = await github_client.make_request("GET", "/user")
        
        if result["success"]:
            user_data = result["data"]
            health_status = {
                "status": "healthy",
                "authenticated_user": user_data.get("login", "unknown"),
                "user_type": user_data.get("type", "unknown"),
                "api_url": github_client.base_url,
                "rate_limit_remaining": result["headers"].get("x-ratelimit-remaining"),
                "rate_limit_reset": result["headers"].get("x-ratelimit-reset"),
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise RuntimeError(f"GitHub API authentication failed: {result['data']}")
        
        # logfire.info("GitHub health check completed", health_status=health_status)
        return health_status
        
    except Exception as e:
        # logfire.error("GitHub health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_repositories")
async def list_repositories(
    org: Optional[str] = None,
    user: Optional[str] = None,
    type: str = "all",
    sort: str = "updated",
    per_page: int = 30
) -> List[Dict[str, Any]]:
    """List repositories for an organization or user."""
    target_org = org or github_client.default_org
    # logfire.info("Listing repositories", org=target_org, user=user, type=type)
    
    try:
        if user:
            endpoint = f"/users/{user}/repos"
        else:
            endpoint = f"/orgs/{target_org}/repos"
        
        params = {
            "type": type,
            "sort": sort,
            "per_page": per_page
        }
        
        result = await github_client.make_request("GET", endpoint, params=params)
        
        if not result["success"]:
            raise RuntimeError(f"Failed to list repositories: {result['data']}")
        
        repos = []
        for repo_data in result["data"]:
            repos.append({
                "name": repo_data.get("name"),
                "full_name": repo_data.get("full_name"),
                "description": repo_data.get("description"),
                "private": repo_data.get("private"),
                "fork": repo_data.get("fork"),
                "language": repo_data.get("language"),
                "stars": repo_data.get("stargazers_count"),
                "forks": repo_data.get("forks_count"),
                "open_issues": repo_data.get("open_issues_count"),
                "default_branch": repo_data.get("default_branch"),
                "created_at": repo_data.get("created_at"),
                "updated_at": repo_data.get("updated_at"),
                "clone_url": repo_data.get("clone_url"),
                "html_url": repo_data.get("html_url")
            })
        
        # logfire.info("Repositories listed", 
        #             org=target_org,
        #             user=user,
        #             count=len(repos))
        
        return repos
        
    except Exception as e:
        # logfire.error("Failed to list repositories", org=target_org, user=user, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_repository")
async def get_repository(repo: str, owner: Optional[str] = None) -> Dict[str, Any]:
    """Get detailed information about a repository."""
    repo_owner = owner or github_client.default_org
    # logfire.info("Getting repository info", repo=repo, owner=repo_owner)
    
    try:
        endpoint = f"/repos/{repo_owner}/{repo}"
        result = await github_client.make_request("GET", endpoint)
        
        if not result["success"]:
            raise RuntimeError(f"Failed to get repository: {result['data']}")
        
        repo_data = result["data"]
        repository_info = {
            "name": repo_data.get("name"),
            "full_name": repo_data.get("full_name"),
            "description": repo_data.get("description"),
            "private": repo_data.get("private"),
            "fork": repo_data.get("fork"),
            "language": repo_data.get("language"),
            "languages_url": repo_data.get("languages_url"),
            "size": repo_data.get("size"),
            "stars": repo_data.get("stargazers_count"),
            "watchers": repo_data.get("watchers_count"),
            "forks": repo_data.get("forks_count"),
            "open_issues": repo_data.get("open_issues_count"),
            "default_branch": repo_data.get("default_branch"),
            "topics": repo_data.get("topics", []),
            "license": repo_data.get("license", {}).get("name") if repo_data.get("license") else None,
            "created_at": repo_data.get("created_at"),
            "updated_at": repo_data.get("updated_at"),
            "pushed_at": repo_data.get("pushed_at"),
            "clone_url": repo_data.get("clone_url"),
            "ssh_url": repo_data.get("ssh_url"),
            "html_url": repo_data.get("html_url"),
            "homepage": repo_data.get("homepage"),
            "has_issues": repo_data.get("has_issues"),
            "has_projects": repo_data.get("has_projects"),
            "has_wiki": repo_data.get("has_wiki"),
            "has_pages": repo_data.get("has_pages"),
            "archived": repo_data.get("archived"),
            "disabled": repo_data.get("disabled")
        }
        
        # logfire.info("Repository info retrieved", repo=repo, owner=repo_owner)
        return repository_info
        
    except Exception as e:
        # logfire.error("Failed to get repository", repo=repo, owner=repo_owner, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_issues")
async def list_issues(
    repo: str,
    owner: Optional[str] = None,
    state: str = "open",
    labels: Optional[str] = None,
    assignee: Optional[str] = None,
    per_page: int = 30
) -> List[Dict[str, Any]]:
    """List issues for a repository."""
    repo_owner = owner or github_client.default_org
    # logfire.info("Listing issues", repo=repo, owner=repo_owner, state=state)
    
    try:
        endpoint = f"/repos/{repo_owner}/{repo}/issues"
        params = {
            "state": state,
            "per_page": per_page
        }
        
        if labels:
            params["labels"] = labels
        if assignee:
            params["assignee"] = assignee
        
        result = await github_client.make_request("GET", endpoint, params=params)
        
        if not result["success"]:
            raise RuntimeError(f"Failed to list issues: {result['data']}")
        
        issues = []
        for issue_data in result["data"]:
            # Skip pull requests (they appear in issues API)
            if issue_data.get("pull_request"):
                continue
                
            issues.append({
                "number": issue_data.get("number"),
                "title": issue_data.get("title"),
                "body": issue_data.get("body"),
                "state": issue_data.get("state"),
                "user": issue_data.get("user", {}).get("login"),
                "assignee": issue_data.get("assignee", {}).get("login") if issue_data.get("assignee") else None,
                "labels": [label.get("name") for label in issue_data.get("labels", [])],
                "milestone": issue_data.get("milestone", {}).get("title") if issue_data.get("milestone") else None,
                "comments": issue_data.get("comments"),
                "created_at": issue_data.get("created_at"),
                "updated_at": issue_data.get("updated_at"),
                "closed_at": issue_data.get("closed_at"),
                "html_url": issue_data.get("html_url")
            })
        
        # logfire.info("Issues listed", 
        #             repo=repo,
        #             owner=repo_owner,
        #             state=state,
        #             count=len(issues))
        
        return issues
        
    except Exception as e:
        # logfire.error("Failed to list issues", repo=repo, owner=repo_owner, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("create_issue")
async def create_issue(
    repo: str,
    title: str,
    body: Optional[str] = None,
    assignees: Optional[List[str]] = None,
    labels: Optional[List[str]] = None,
    owner: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new issue in a repository."""
    repo_owner = owner or github_client.default_org
    # logfire.info("Creating issue", repo=repo, owner=repo_owner, title=title)
    
    try:
        endpoint = f"/repos/{repo_owner}/{repo}/issues"
        
        issue_data = {
            "title": title
        }
        
        if body:
            issue_data["body"] = body
        if assignees:
            issue_data["assignees"] = assignees
        if labels:
            issue_data["labels"] = labels
        
        result = await github_client.make_request("POST", endpoint, json=issue_data)
        
        if not result["success"]:
            raise RuntimeError(f"Failed to create issue: {result['data']}")
        
        created_issue = result["data"]
        issue_info = {
            "number": created_issue.get("number"),
            "title": created_issue.get("title"),
            "body": created_issue.get("body"),
            "state": created_issue.get("state"),
            "user": created_issue.get("user", {}).get("login"),
            "html_url": created_issue.get("html_url"),
            "created_at": created_issue.get("created_at")
        }
        
        # logfire.info("Issue created successfully", 
        #             repo=repo,
        #             owner=repo_owner,
        #             issue_number=issue_info["number"])
        
        return issue_info
        
    except Exception as e:
        # logfire.error("Failed to create issue", repo=repo, owner=repo_owner, title=title, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_pull_requests")
async def list_pull_requests(
    repo: str,
    owner: Optional[str] = None,
    state: str = "open",
    base: Optional[str] = None,
    head: Optional[str] = None,
    per_page: int = 30
) -> List[Dict[str, Any]]:
    """List pull requests for a repository."""
    repo_owner = owner or github_client.default_org
    # logfire.info("Listing pull requests", repo=repo, owner=repo_owner, state=state)
    
    try:
        endpoint = f"/repos/{repo_owner}/{repo}/pulls"
        params = {
            "state": state,
            "per_page": per_page
        }
        
        if base:
            params["base"] = base
        if head:
            params["head"] = head
        
        result = await github_client.make_request("GET", endpoint, params=params)
        
        if not result["success"]:
            raise RuntimeError(f"Failed to list pull requests: {result['data']}")
        
        pull_requests = []
        for pr_data in result["data"]:
            pull_requests.append({
                "number": pr_data.get("number"),
                "title": pr_data.get("title"),
                "body": pr_data.get("body"),
                "state": pr_data.get("state"),
                "user": pr_data.get("user", {}).get("login"),
                "head_branch": pr_data.get("head", {}).get("ref"),
                "base_branch": pr_data.get("base", {}).get("ref"),
                "mergeable": pr_data.get("mergeable"),
                "merged": pr_data.get("merged"),
                "draft": pr_data.get("draft"),
                "labels": [label.get("name") for label in pr_data.get("labels", [])],
                "requested_reviewers": [user.get("login") for user in pr_data.get("requested_reviewers", [])],
                "created_at": pr_data.get("created_at"),
                "updated_at": pr_data.get("updated_at"),
                "merged_at": pr_data.get("merged_at"),
                "html_url": pr_data.get("html_url")
            })
        
        # logfire.info("Pull requests listed", 
        #             repo=repo,
        #             owner=repo_owner,
        #             state=state,
        #             count=len(pull_requests))
        
        return pull_requests
        
    except Exception as e:
        # logfire.error("Failed to list pull requests", repo=repo, owner=repo_owner, error=str(e))
        pass
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("GitHub MCP server starting up")
    
    # Test GitHub connectivity on startup
    try:
        await github_health_check()
        # logfire.info("GitHub connectivity verified on startup")
    except Exception as e:
        # logfire.warning("GitHub connectivity test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("GitHub MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting GitHub MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())