"""
HTTP API Package for Machina Registry Service

This package contains the FastAPI REST API implementation for the Machina
Registry Service, providing HTTP endpoints for service discovery, health
monitoring, and configuration management.

Components:
- routes/: API route definitions and endpoint handlers
- controllers/: Business logic controllers for API operations
"""

from .routes import router

__all__ = ["router"]
