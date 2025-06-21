"""
API v1 Package for Machina Registry Service

This package contains the REST API endpoints for version 1 of the Machina Registry
Service API, implementing DevQ.ai's standard API patterns with comprehensive
TaskMaster AI integration, health monitoring, and observability.

Components:
- taskmaster.py: TaskMaster AI endpoints for task management
- health.py: Health check and monitoring endpoints
- registry.py: MCP registry management endpoints (future)
- auth.py: Authentication and authorization endpoints (future)
"""

from .taskmaster import router as taskmaster_router

__all__ = ["taskmaster_router"]
