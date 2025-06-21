"""
Repositories Package for Machina Registry Service

This package contains the data access layer for the Machina Registry Service,
implementing the repository pattern with async SQLAlchemy support for clean
separation of data access logic from business logic.

Components:
- base.py: Base repository class with common CRUD operations
- registry_item.py: Repository for registry item data access
- service.py: Repository for service configuration data access
- health_check.py: Repository for health monitoring data access
"""

from .base import BaseRepository

__all__ = ["BaseRepository"]
