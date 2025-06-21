"""
Service Discovery Module

This module provides comprehensive service discovery capabilities for the Machina Registry Service.
It includes local scanning, external service integration, Docker discovery, and health probing.
"""

from .local_scanner import LocalServiceScanner
from .docker_discovery import DockerServiceDiscovery
from .external_registry import ExternalRegistryAdapter
from .health_probe import HealthProbe, HttpHealthProbe, TcpHealthProbe
from .service_validator import ServiceValidator
from .service_registry import ServiceRegistry
from .metadata_extractor import ServiceMetadataExtractor

__all__ = [
    "LocalServiceScanner",
    "DockerServiceDiscovery",
    "ExternalRegistryAdapter",
    "HealthProbe",
    "HttpHealthProbe",
    "TcpHealthProbe",
    "ServiceValidator",
    "ServiceRegistry",
    "ServiceMetadataExtractor",
]
