"""
Domain Models Package for Machina Registry Service

This package contains domain-specific models for the Machina Registry Service,
representing the core business entities and data structures for MCP server
registry, service discovery, and configuration management.

Models:
- registry_item.py: Core registry item model for MCP servers and services
- service.py: Service configuration and metadata model
- health_check.py: Health monitoring and status tracking model
- configuration.py: Service configuration and settings model
"""

from .registry_item import RegistryItem

__all__ = ["RegistryItem"]
