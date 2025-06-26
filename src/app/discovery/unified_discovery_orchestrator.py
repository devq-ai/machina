"""
Unified Discovery Orchestrator Module

This module provides a comprehensive orchestration layer that unifies all discovery methods
(Local, Docker, External Registries) into a single, coordinated service discovery system.
This is the main deliverable for Task 2.2: External Service Integration and Docker Discovery.
"""

import logging
import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from collections import defaultdict

from .local_scanner import LocalServiceScanner, ServiceInfo
from .docker_discovery import DockerServiceDiscovery, DockerServiceInfo
from .external_registry import ExternalRegistryAdapter, ExternalServiceInfo
from .health_probe import HealthProbeFactory, HealthResult
from .service_validator import ServiceValidator, ValidationResult
from .service_registry import ServiceRegistry, RegisteredService, RegistrationResult
from .metadata_extractor import ServiceMetadataExtractor, ExtractedMetadata

logger = logging.getLogger(__name__)


@dataclass
class UnifiedServiceInfo:
    """Unified service information combining all discovery sources"""
    id: str
    name: str
    type: str
    source: str  # 'local', 'docker', 'external'
    status: str
    health_status: Optional[str]
    endpoints: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    discovered_at: str
    validated: bool = False
    validation_result: Optional[ValidationResult] = None
    health_result: Optional[HealthResult] = None
    extracted_metadata: Optional[List[ExtractedMetadata]] = None
    location: Optional[str] = None
    tags: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None


@dataclass
class DiscoveryStats:
    """Statistics for discovery operations"""
    total_services_discovered: int = 0
    local_services: int = 0
    docker_services: int = 0
    external_services: int = 0
    healthy_services: int = 0
    unhealthy_services: int = 0
    validated_services: int = 0
    invalid_services: int = 0
    discovery_time_seconds: float = 0.0
    last_discovery: Optional[str] = None
    error_count: int = 0


class UnifiedDiscoveryOrchestrator:
    """
    Unified orchestrator that coordinates all service discovery methods
    and provides a single interface for comprehensive service discovery.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the unified discovery orchestrator.

        Args:
            config: Configuration dictionary with discovery settings
        """
        self.config = config or {}

        # Initialize discovery components
        self.local_scanner = None
        self.docker_discovery = None
        self.external_adapter = None
        self.health_probe_factory = HealthProbeFactory()
        self.service_validator = None
        self.service_registry = None
        self.metadata_extractor = None

        # Discovery state
        self.discovered_services: Dict[str, UnifiedServiceInfo] = {}
        self.discovery_stats = DiscoveryStats()
        self.is_running = False
        self.discovery_thread = None
        self.stop_event = threading.Event()

        # Event callbacks
        self.service_discovered_callback: Optional[Callable] = None
        self.service_updated_callback: Optional[Callable] = None
        self.service_removed_callback: Optional[Callable] = None

        # Initialize components based on configuration
        self._initialize_components()

    def _initialize_components(self):
        """Initialize discovery components based on configuration"""
        try:
            # Initialize local scanner
            local_config = self.config.get('local_scanner', {})
            if local_config.get('enabled', True):
                base_dirs = local_config.get('base_directories', [])
                max_depth = local_config.get('max_depth', 5)
                self.local_scanner = LocalServiceScanner(
                    base_directories=base_dirs if base_dirs else None,
                    max_depth=max_depth
                )
                logger.info("Initialized Local Service Scanner")

            # Initialize Docker discovery
            docker_config = self.config.get('docker_discovery', {})
            if docker_config.get('enabled', True):
                try:
                    include_stopped = docker_config.get('include_stopped', False)
                    label_filters = docker_config.get('label_filters', {})
                    self.docker_discovery = DockerServiceDiscovery(
                        include_stopped=include_stopped,
                        label_filters=label_filters
                    )
                    logger.info("Initialized Docker Service Discovery")
                except Exception as e:
                    logger.warning(f"Docker discovery not available: {e}")

            # Initialize external registry adapter
            external_config = self.config.get('external_registries', {})
            if external_config.get('enabled', False):
                self.external_adapter = ExternalRegistryAdapter()

                # Add configured registries
                registries = external_config.get('registries', [])
                for registry in registries:
                    name = registry.get('name')
                    registry_type = registry.get('type')
                    connection_params = registry.get('connection_params', {})

                    if name and registry_type:
                        success = self.external_adapter.add_registry(
                            name, registry_type, connection_params
                        )
                        if success:
                            logger.info(f"Added external registry: {name} ({registry_type})")
                        else:
                            logger.warning(f"Failed to add registry: {name}")

            # Initialize validation and health checking
            validation_config = self.config.get('validation', {})
            self.service_validator = ServiceValidator(
                enable_health_checks=validation_config.get('enable_health_checks', True),
                health_check_timeout=validation_config.get('health_check_timeout', 5.0),
                strict_validation=validation_config.get('strict_validation', False)
            )

            # Initialize service registry
            registry_config = self.config.get('service_registry', {})
            storage_path = registry_config.get('storage_path', './unified_service_registry.db')
            self.service_registry = ServiceRegistry(
                storage_path=storage_path,
                enable_persistence=registry_config.get('enable_persistence', True),
                enable_deduplication=registry_config.get('enable_deduplication', True)
            )

            # Initialize metadata extractor
            metadata_config = self.config.get('metadata_extraction', {})
            self.metadata_extractor = ServiceMetadataExtractor(
                deep_analysis=metadata_config.get('deep_analysis', True),
                include_dependencies=metadata_config.get('include_dependencies', True),
                analyze_security=metadata_config.get('analyze_security', True),
                extract_api_specs=metadata_config.get('extract_api_specs', True)
            )

            logger.info("Unified Discovery Orchestrator initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing discovery components: {e}")
            raise

    async def discover_all_services(self, include_validation: bool = True,
                                  include_health_checks: bool = True,
                                  include_metadata_extraction: bool = True) -> List[UnifiedServiceInfo]:
        """
        Perform comprehensive service discovery across all sources.

        Args:
            include_validation: Whether to validate discovered services
            include_health_checks: Whether to perform health checks
            include_metadata_extraction: Whether to extract metadata

        Returns:
            List of unified service information
        """
        start_time = time.time()
        logger.info("Starting unified service discovery...")

        try:
            # Reset stats
            self.discovery_stats = DiscoveryStats()

            # Discover from all sources concurrently
            discovery_tasks = []

            if self.local_scanner:
                task = asyncio.create_task(self._discover_local_services())
                discovery_tasks.append(('local', task))

            if self.docker_discovery:
                task = asyncio.create_task(self._discover_docker_services())
                discovery_tasks.append(('docker', task))

            if self.external_adapter:
                task = asyncio.create_task(self._discover_external_services())
                discovery_tasks.append(('external', task))

            # Wait for all discovery tasks to complete
            all_services = []
            for source, task in discovery_tasks:
                try:
                    services = await task
                    all_services.extend(services)
                    logger.info(f"Discovered {len(services)} services from {source}")
                except Exception as e:
                    logger.error(f"Error discovering from {source}: {e}")
                    self.discovery_stats.error_count += 1

            # Remove duplicates and unify services
            unified_services = self._unify_services(all_services)

            # Update discovery stats
            self.discovery_stats.total_services_discovered = len(unified_services)

            # Perform validation if requested
            if include_validation and self.service_validator:
                unified_services = await self._validate_services(unified_services)

            # Perform health checks if requested
            if include_health_checks:
                unified_services = await self._check_service_health(unified_services)

            # Extract metadata if requested
            if include_metadata_extraction and self.metadata_extractor:
                unified_services = await self._extract_service_metadata(unified_services)

            # Register services in the unified registry
            if self.service_registry:
                await self._register_services(unified_services)

            # Update discovered services cache
            for service in unified_services:
                self.discovered_services[service.id] = service

                # Trigger callbacks
                if self.service_discovered_callback:
                    try:
                        await self.service_discovered_callback(service)
                    except Exception as e:
                        logger.error(f"Error in discovery callback: {e}")

            # Finalize stats
            self.discovery_stats.discovery_time_seconds = time.time() - start_time
            self.discovery_stats.last_discovery = datetime.now().isoformat()

            logger.info(f"Unified discovery completed: {len(unified_services)} services in "
                       f"{self.discovery_stats.discovery_time_seconds:.2f}s")

            return unified_services

        except Exception as e:
            logger.error(f"Error in unified service discovery: {e}")
            self.discovery_stats.error_count += 1
            raise

    async def _discover_local_services(self) -> List[UnifiedServiceInfo]:
        """Discover services using local scanner"""
        services = []

        try:
            local_services = self.local_scanner.scan()

            for service in local_services:
                unified_service = UnifiedServiceInfo(
                    id=f"local_{service.id}",
                    name=service.name,
                    type=service.type,
                    source='local',
                    status='active',
                    health_status=None,
                    endpoints=[],
                    metadata=service.metadata,
                    discovered_at=service.discovered_at,
                    location=service.location,
                    tags=[]
                )

                # Add endpoints if available
                if service.health_endpoint:
                    unified_service.endpoints.append({
                        'type': 'health',
                        'url': service.health_endpoint,
                        'host': service.host,
                        'port': service.port
                    })

                services.append(unified_service)

            self.discovery_stats.local_services = len(services)

        except Exception as e:
            logger.error(f"Error discovering local services: {e}")

        return services

    async def _discover_docker_services(self) -> List[UnifiedServiceInfo]:
        """Discover services using Docker discovery"""
        services = []

        try:
            docker_services = await self.docker_discovery.discover_services()

            for service in docker_services:
                unified_service = UnifiedServiceInfo(
                    id=f"docker_{service.id}",
                    name=service.name,
                    type=service.type,
                    source='docker',
                    status=service.status,
                    health_status=service.health_status if hasattr(service, 'health_status') else None,
                    endpoints=service.endpoints,
                    metadata=service.metadata,
                    discovered_at=service.discovered_at,
                    tags=service.tags if hasattr(service, 'tags') else []
                )

                services.append(unified_service)

            self.discovery_stats.docker_services = len(services)

        except Exception as e:
            logger.error(f"Error discovering Docker services: {e}")

        return services

    async def _discover_external_services(self) -> List[UnifiedServiceInfo]:
        """Discover services from external registries"""
        services = []

        try:
            external_services = await self.external_adapter.discover_all_services()

            for service in external_services:
                unified_service = UnifiedServiceInfo(
                    id=f"external_{service.registry_type}_{service.id}",
                    name=service.name,
                    type=service.type,
                    source=f'external_{service.registry_type}',
                    status='active',
                    health_status=service.health_status,
                    endpoints=service.endpoints,
                    metadata=service.metadata,
                    discovered_at=service.discovered_at,
                    tags=service.tags or []
                )

                services.append(unified_service)

            self.discovery_stats.external_services = len(services)

        except Exception as e:
            logger.error(f"Error discovering external services: {e}")

        return services

    def _unify_services(self, all_services: List[UnifiedServiceInfo]) -> List[UnifiedServiceInfo]:
        """Remove duplicates and unify services from different sources"""
        service_map = {}

        for service in all_services:
            # Create a key for deduplication based on name and type
            key = f"{service.name}_{service.type}"

            if key not in service_map:
                service_map[key] = service
            else:
                # Merge services from different sources
                existing = service_map[key]
                merged = self._merge_service_info(existing, service)
                service_map[key] = merged

        return list(service_map.values())

    def _merge_service_info(self, existing: UnifiedServiceInfo,
                           new: UnifiedServiceInfo) -> UnifiedServiceInfo:
        """Merge two service info objects"""
        # Prefer Docker/external sources over local for certain fields
        if new.source in ['docker', 'external_consul', 'external_kubernetes']:
            if new.health_status:
                existing.health_status = new.health_status
            if new.endpoints:
                existing.endpoints.extend(new.endpoints)

        # Merge metadata
        existing.metadata.update(new.metadata)

        # Merge tags
        if new.tags:
            existing.tags = list(set((existing.tags or []) + new.tags))

        # Update status if new source has better information
        if new.status in ['running', 'healthy'] and existing.status in ['active', 'unknown']:
            existing.status = new.status

        return existing

    async def _validate_services(self, services: List[UnifiedServiceInfo]) -> List[UnifiedServiceInfo]:
        """Validate discovered services"""
        validated_services = []

        try:
            # Convert to validation format
            service_dicts = []
            for service in services:
                service_dict = {
                    'id': service.id,
                    'name': service.name,
                    'type': service.type,
                    'status': service.status,
                    'metadata': service.metadata,
                    'endpoints': service.endpoints
                }
                if service.location:
                    service_dict['location'] = service.location
                service_dicts.append(service_dict)

            # Validate in batches
            validation_results = await self._validate_service_batch_async(service_dicts)

            # Apply validation results
            for i, service in enumerate(services):
                if i < len(validation_results):
                    result = validation_results[i]
                    service.validated = result.is_valid
                    service.validation_result = result

                    if result.is_valid:
                        self.discovery_stats.validated_services += 1
                    else:
                        self.discovery_stats.invalid_services += 1
                        logger.warning(f"Service validation failed for {service.name}: {result.issues}")

                validated_services.append(service)

        except Exception as e:
            logger.error(f"Error validating services: {e}")
            validated_services = services

        return validated_services

    async def _validate_service_batch_async(self, services: List[Dict[str, Any]]) -> List:
        """Async wrapper for batch service validation"""
        tasks = [self.service_validator.validate_service(service) for service in services]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        validated_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_id = services[i].get('id', f'service_{i}')
                # Create a simple validation result
                validated_results.append(type('ValidationResult', (), {
                    'is_valid': False,
                    'service_id': service_id,
                    'validation_type': 'error',
                    'issues': [f"Validation error: {str(result)}"],
                    'warnings': []
                })())
            else:
                validated_results.append(result)

        return validated_results

    async def _check_service_health(self, services: List[UnifiedServiceInfo]) -> List[UnifiedServiceInfo]:
        """Check health of discovered services"""
        health_checked_services = []

        for service in services:
            try:
                # Create health probe based on service endpoints
                if service.endpoints:
                    probe_service = {
                        'health_endpoint': None,
                        'host': None,
                        'port': None
                    }

                    # Find suitable endpoint for health checking
                    for endpoint in service.endpoints:
                        if endpoint.get('type') in ['health', 'http', 'https']:
                            probe_service['health_endpoint'] = endpoint.get('url')
                            probe_service['host'] = endpoint.get('host')
                            probe_service['port'] = endpoint.get('port')
                            break

                    if probe_service['health_endpoint'] or (probe_service['host'] and probe_service['port']):
                        probe = self.health_probe_factory.create_probe(probe_service)
                        health_result = await probe.check_health(probe_service)

                        service.health_result = health_result
                        service.health_status = health_result.status

                        if health_result.status == 'healthy':
                            self.discovery_stats.healthy_services += 1
                        else:
                            self.discovery_stats.unhealthy_services += 1

                health_checked_services.append(service)

            except Exception as e:
                logger.error(f"Error checking health for {service.name}: {e}")
                health_checked_services.append(service)

        return health_checked_services

    async def _extract_service_metadata(self, services: List[UnifiedServiceInfo]) -> List[UnifiedServiceInfo]:
        """Extract metadata for discovered services"""
        metadata_extracted_services = []

        for service in services:
            try:
                if service.location:  # Only extract for services with locations
                    service_dict = {
                        'id': service.id,
                        'type': service.type,
                        'location': service.location,
                        'metadata': service.metadata
                    }

                    extracted_metadata = self.metadata_extractor.extract_metadata(service_dict)
                    service.extracted_metadata = extracted_metadata

                    # Merge extracted metadata into service metadata
                    for metadata in extracted_metadata:
                        if metadata.metadata_type == 'configuration':
                            service.metadata.update(metadata.data)

                metadata_extracted_services.append(service)

            except Exception as e:
                logger.error(f"Error extracting metadata for {service.name}: {e}")
                metadata_extracted_services.append(service)

        return metadata_extracted_services

    async def _register_services(self, services: List[UnifiedServiceInfo]):
        """Register services in the unified registry"""
        try:
            for service in services:
                service_data = {
                    'id': service.id,
                    'name': service.name,
                    'type': service.type,
                    'status': service.status,
                    'location': service.location,
                    'metadata': service.metadata,
                    'endpoints': service.endpoints,
                    'health_status': service.health_status,
                    'tags': service.tags,
                    'source': service.source
                }

                result = self.service_registry.register_service(service_data)
                if not result.success:
                    logger.warning(f"Failed to register service {service.name}: {result.message}")

        except Exception as e:
            logger.error(f"Error registering services: {e}")

    def start_continuous_discovery(self, interval_seconds: int = 300):
        """Start continuous service discovery"""
        if self.is_running:
            logger.warning("Continuous discovery already running")
            return

        self.is_running = True
        self.stop_event.clear()

        def discovery_loop():
            while not self.stop_event.wait(interval_seconds):
                try:
                    asyncio.run(self.discover_all_services())
                except Exception as e:
                    logger.error(f"Error in continuous discovery: {e}")

        self.discovery_thread = threading.Thread(target=discovery_loop, daemon=True)
        self.discovery_thread.start()
        logger.info(f"Started continuous discovery with {interval_seconds}s interval")

    def stop_continuous_discovery(self):
        """Stop continuous service discovery"""
        if not self.is_running:
            return

        self.is_running = False
        self.stop_event.set()

        if self.discovery_thread:
            self.discovery_thread.join(timeout=10.0)

        logger.info("Stopped continuous discovery")

    def get_discovery_stats(self) -> Dict[str, Any]:
        """Get discovery statistics"""
        return asdict(self.discovery_stats)

    def get_discovered_services(self, filters: Optional[Dict[str, Any]] = None) -> List[UnifiedServiceInfo]:
        """Get discovered services with optional filtering"""
        services = list(self.discovered_services.values())

        if not filters:
            return services

        filtered_services = []
        for service in services:
            match = True

            for key, value in filters.items():
                if key == 'source' and service.source != value:
                    match = False
                    break
                elif key == 'type' and service.type != value:
                    match = False
                    break
                elif key == 'status' and service.status != value:
                    match = False
                    break
                elif key == 'health_status' and service.health_status != value:
                    match = False
                    break
                elif key == 'validated' and service.validated != value:
                    match = False
                    break

            if match:
                filtered_services.append(service)

        return filtered_services

    def set_callbacks(self, discovered: Optional[Callable] = None,
                     updated: Optional[Callable] = None,
                     removed: Optional[Callable] = None):
        """Set event callbacks"""
        self.service_discovered_callback = discovered
        self.service_updated_callback = updated
        self.service_removed_callback = removed

    async def cleanup(self):
        """Cleanup resources"""
        try:
            self.stop_continuous_discovery()

            if self.external_adapter:
                await self.external_adapter.disconnect_all()

            if self.service_registry:
                self.service_registry.close()

            logger.info("Unified Discovery Orchestrator cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def get_component_status(self) -> Dict[str, bool]:
        """Get status of all discovery components"""
        return {
            'local_scanner': self.local_scanner is not None,
            'docker_discovery': self.docker_discovery is not None,
            'external_adapter': self.external_adapter is not None,
            'service_validator': self.service_validator is not None,
            'service_registry': self.service_registry is not None,
            'metadata_extractor': self.metadata_extractor is not None,
            'continuous_discovery': self.is_running
        }
