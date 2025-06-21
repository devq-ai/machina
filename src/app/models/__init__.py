"""
Models Package for Machina Registry Service

This package contains the database models and domain objects for the Machina
Registry Service, implementing SQLAlchemy ORM patterns with async support
and following DevQ.ai's standard data modeling practices.

Components:
- base.py: Base model class with common fields and functionality
- domain/: Domain-specific models for registry items, services, and configurations
"""

from .base import BaseModel

__all__ = ["BaseModel"]
