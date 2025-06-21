"""
Core Package for Machina Registry Service

This package contains the core configuration, utilities, and foundational
components for the Machina Registry Service, implementing DevQ.ai's
standard architecture patterns.

Components:
- config.py: Application configuration and settings management
- exceptions.py: Custom exception classes and error handling
- database.py: Database connection and session management
- redis.py: Redis cache and pub/sub system integration
- dependencies.py: FastAPI dependency injection system
"""

from .config import settings
from .exceptions import MachinaException

__all__ = ["settings", "MachinaException"]
