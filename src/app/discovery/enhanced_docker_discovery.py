"""
Enhanced Docker Service Discovery Module

This module provides advanced Docker-based service discovery capabilities with real-time monitoring,
event-driven updates, advanced container analysis, and comprehensive service extraction.
"""

import logging
import json
import asyncio
import time
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import docker
import threading
from collections import defaultdict
import re

logger = logging.getLogger(__name__)


@dataclass
class EnhancedDockerServiceInfo:
    """Enhanced data class for Docker service information with advanced metadata"""
    id: str
    name: str
    type: str
    status: str
    health_status: str
    endpoints: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    container_id: Optional[str] = None
    image: Optional[str] = None
    image_digest: Optional[str] = None
    ports: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    volumes: Optional[List[str]] = None
    labels: Optional[Dict[str, str]] = None
    resource_limits: Optional[Dict[str, Any]] = None
    discovered_at: Optional[str] = None
    last_updated: Optional[str] = None
    dependencies: Optional[List[str]] = None
    service_mesh_info: Optional[Dict[str, Any]] = None
    security_context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.now().isoformat()
        if self.last_updated is None:
            self.last_updated = self.discovered_at


@dataclass
class DockerEvent:
    """Data class for Docker events"""
    event_type: str
    action: str
    container_id: str
    container_name: str
    image: str
    timestamp: str
    metadata: Dict[str, Any]


class EnhancedDockerServiceDiscovery:
    """
    Enhanced Docker-based service discovery with real-time monitoring,
    event processing, and advanced container analysis capabilities.
    """

    def __init__(self, docker_client=None, include_stopped: bool = False,
                 label_filters: Optional[Dict[str, str]] = None,
                 enable_real_time: bool = True,
                 event_callback: Optional[Callable] = None):
        """
        Initialize enhanced Docker service discovery.

        Args:
            docker_client: Docker client instance
            include_stopped: Whether to include stopped containers
            label_filters: Dictionary of label filters
            enable_real_time: Enable real-time event monitoring
            event_callback: Callback function for Docker events
        """
        try:
            self.docker_client = docker_client or docker.from_env()
            self.api_client = docker.APIClient()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None
            self.api_client = None

        self.include_stopped = include_stopped
        self.label_filters = label_filters or {}
        self.enable_real_time = enable_real_time
        self.event_callback = event_callback

        # Service discovery state
        self.discovered_services: Dict[str, EnhancedDockerServiceInfo] = {}
        self.service_stats = defaultdict(int)
        self.event_history: List[DockerEvent] = []
        self.monitoring_thread = None
        self.stop_monitoring = threading.Event()

        # Enhanced service detection patterns
        self.service_indicators = {
            'web_server': {
                'images': ['nginx', 'apache', 'httpd', 'caddy', 'traefik'],
                'ports': [80, 443, 8080, 8443],
                'labels': ['web', 'frontend', 'proxy']
            },
            'database': {
                'images': ['postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'mariadb'],
                'ports': [3306, 5432, 27017, 6379, 9200, 9300],
                'labels': ['database', 'db', 'storage']
            },
            'message_queue': {
                'images': ['rabbitmq', 'kafka', 'activemq', 'nats', 'pulsar'],
                'ports': [5672, 9092, 61616, 4222, 6650],
                'labels': ['queue', 'messaging', 'broker']
            },
            'cache': {
                'images': ['redis', 'memcached', 'hazelcast', 'varnish'],
                'ports': [6379, 11211, 5701, 6081],
                'labels': ['cache', 'memory', 'store']
            },
            'api_server': {
                'images': ['node', 'python', 'go', 'java', 'dotnet'],
                'ports': [3000, 8000, 8080, 9000, 5000],
                'labels': ['api', 'service', 'backend']
            },
            'monitoring': {
                'images': ['prometheus', 'grafana', 'jaeger', 'zipkin', 'elasticsearch'],
                'ports': [9090, 3000, 14268, 9411, 9200],
                'labels': ['monitoring', 'metrics', 'observability']
            },
            'service_mesh': {
                'images': ['istio', 'envoy', 'linkerd', 'consul-connect'],
                'ports': [15000, 15001, 8080, 8500],
                'labels': ['istio', 'envoy', 'mesh', 'sidecar']
            }
        }

        # Port mappings for service identification
        self.well_known_ports = {
            20: 'ftp-data', 21: 'ftp', 22: 'ssh', 23: 'telnet', 25: 'smtp',
            53: 'dns', 80: 'http', 110: 'pop3', 143: 'imap', 443: 'https',
            993: 'imaps', 995: 'pop3s', 1433: 'mssql', 1521: 'oracle',
            3000: 'node/express', 3306: 'mysql', 5000: 'flask', 5432: 'postgresql',
            6379: 'redis', 8000: 'django/fastapi', 8080: 'tomcat/jetty',
            8443: 'https-alt', 9000: 'php-fpm', 9090: 'prometheus',
            9200: 'elasticsearch', 11211: 'memcached', 27017: 'mongodb'
        }

        # Initialize real-time monitoring if enabled
        if self.enable_real_time and self.docker_client:
            self.start_real_time_monitoring()

    def start_real_time_monitoring(self):
        """Start real-time Docker event monitoring"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            return

        self.stop_monitoring.clear()
        self.monitoring_thread = threading.Thread(
            target=self._monitor_docker_events,
            daemon=True
        )
        self.monitoring_thread.start()
        logger.info("Started real-time Docker event monitoring")

    def stop_real_time_monitoring(self):
        """Stop real-time Docker event monitoring"""
        if self.monitoring_thread:
            self.stop_monitoring.set()
            self.monitoring_thread.join(timeout=5.0)
            logger.info("Stopped real-time Docker event monitoring")

    def _monitor_docker_events(self):
        """Monitor Docker events in a separate thread"""
        try:
            events = self.docker_client.events(decode=True)
            for event in events:
                if self.stop_monitoring.is_set():
                    break

                if event.get('Type') == 'container':
                    self._process_container_event(event)

        except Exception as e:
            logger.error(f"Error in Docker event monitoring: {e}")

    def _process_container_event(self, event: Dict[str, Any]):
        """Process individual container events"""
        try:
            action = event.get('Action', '')
            container_id = event.get('id', '')
            container_name = event.get('Actor', {}).get('Attributes', {}).get('name', '')

            # Create Docker event object
            docker_event = DockerEvent(
                event_type='container',
                action=action,
                container_id=container_id[:12],
                container_name=container_name,
                image=event.get('Actor', {}).get('Attributes', {}).get('image', ''),
                timestamp=datetime.now().isoformat(),
                metadata=event
            )

            # Add to event history
            self.event_history.append(docker_event)
            if len(self.event_history) > 1000:  # Keep only recent events
                self.event_history = self.event_history[-1000:]

            # Process based on action
            if action in ['start', 'restart']:
                self._handle_container_start(container_id)
            elif action in ['stop', 'die', 'kill']:
                self._handle_container_stop(container_id)
            elif action in ['destroy', 'remove']:
                self._handle_container_remove(container_id)

            # Call user callback if provided
            if self.event_callback:
                try:
                    self.event_callback(docker_event)
                except Exception as e:
                    logger.error(f"Error in event callback: {e}")

            logger.debug(f"Processed container event: {action} for {container_name}")

        except Exception as e:
            logger.error(f"Error processing container event: {e}")

    def _handle_container_start(self, container_id: str):
        """Handle container start event"""
        try:
            container = self.docker_client.containers.get(container_id)
            service_info = self._analyze_container_enhanced(container)

            if service_info:
                self.discovered_services[container_id] = service_info
                self.service_stats['started'] += 1
                logger.info(f"Discovered new service: {service_info.name}")

        except Exception as e:
            logger.error(f"Error handling container start: {e}")

    def _handle_container_stop(self, container_id: str):
        """Handle container stop event"""
        if container_id in self.discovered_services:
            service = self.discovered_services[container_id]
            service.status = 'stopped'
            service.health_status = 'unhealthy'
            service.last_updated = datetime.now().isoformat()
            self.service_stats['stopped'] += 1
            logger.info(f"Service stopped: {service.name}")

    def _handle_container_remove(self, container_id: str):
        """Handle container remove event"""
        if container_id in self.discovered_services:
            service = self.discovered_services.pop(container_id)
            self.service_stats['removed'] += 1
            logger.info(f"Service removed: {service.name}")

    async def discover_services(self) -> List[EnhancedDockerServiceInfo]:
        """
        Discover services from Docker containers with enhanced analysis.

        Returns:
            List of discovered Docker services with enhanced metadata
        """
        if not self.docker_client:
            logger.error("Docker client not available")
            return []

        services = []

        try:
            # Discover from running containers
            container_services = await self._discover_container_services_enhanced()
            services.extend(container_services)

            # Discover from Docker Compose files
            compose_services = await self._discover_compose_services_enhanced()
            services.extend(compose_services)

            # Discover from Docker Swarm services
            swarm_services = await self._discover_swarm_services_enhanced()
            services.extend(swarm_services)

            # Analyze service dependencies
            services = self._analyze_service_dependencies(services)

            # Update discovery statistics
            self.service_stats['total_discovered'] = len(services)
            self.service_stats['last_discovery'] = datetime.now().isoformat()

            logger.info(f"Enhanced discovery completed: {len(services)} services found")

        except Exception as e:
            logger.error(f"Error during enhanced Docker service discovery: {e}")

        return services

    async def _discover_container_services_enhanced(self) -> List[EnhancedDockerServiceInfo]:
        """Discover services from Docker containers with enhanced analysis"""
        services = []

        try:
            containers = self.docker_client.containers.list(all=self.include_stopped)

            # Process containers in batches for better performance
            batch_size = 10
            for i in range(0, len(containers), batch_size):
                batch = containers[i:i + batch_size]

                # Process batch concurrently
                tasks = []
                for container in batch:
                    task = asyncio.create_task(self._analyze_container_async(container))
                    tasks.append(task)

                batch_results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in batch_results:
                    if isinstance(result, EnhancedDockerServiceInfo):
                        services.append(result)
                        # Cache in discovered services
                        self.discovered_services[result.container_id] = result

        except docker.errors.DockerException as e:
            logger.error(f"Error listing Docker containers: {e}")

        return services

    async def _analyze_container_async(self, container) -> Optional[EnhancedDockerServiceInfo]:
        """Asynchronously analyze a container for service information"""
        return await asyncio.to_thread(self._analyze_container_enhanced, container)

    def _analyze_container_enhanced(self, container) -> Optional[EnhancedDockerServiceInfo]:
        """
        Enhanced container analysis with comprehensive metadata extraction.

        Args:
            container: Docker container object

        Returns:
            EnhancedDockerServiceInfo if service is detected, None otherwise
        """
        try:
            # Get fresh container details
            container.reload()
            attrs = container.attrs

            # Extract basic information
            container_id = container.id[:12]
            container_name = container.name
            image_name = container.image.tags[0] if container.image.tags else 'unknown'
            status = container.status

            # Extract labels and apply filters
            labels = attrs.get('Config', {}).get('Labels') or {}
            if not self._passes_label_filters(labels):
                return None

            # Check if this is a service container
            if not self._is_service_container_enhanced(container, labels, attrs):
                return None

            # Extract comprehensive service information
            service_name = self._extract_service_name(labels, container_name, attrs)
            service_type = self._determine_service_type_enhanced(image_name, labels, attrs)
            health_status = self._determine_health_status(container, attrs)

            # Extract networking information
            endpoints = self._extract_endpoints_enhanced(container, attrs)
            ports = self._extract_ports_enhanced(attrs)
            networks = self._extract_networks_enhanced(attrs)

            # Extract environment and volumes
            environment = self._extract_environment_enhanced(attrs)
            volumes = self._extract_volumes(attrs)

            # Extract resource limits and security context
            resource_limits = self._extract_resource_limits(attrs)
            security_context = self._extract_security_context(attrs)

            # Extract service mesh information
            service_mesh_info = self._extract_service_mesh_info(labels, attrs)

            # Build comprehensive metadata
            metadata = self._build_enhanced_metadata(container, attrs, labels)

            # Generate service ID
            service_id = f"docker_{service_name}_{container_id}"

            return EnhancedDockerServiceInfo(
                id=service_id,
                name=service_name,
                type=service_type,
                status=status,
                health_status=health_status,
                endpoints=endpoints,
                metadata=metadata,
                container_id=container_id,
                image=image_name,
                image_digest=self._extract_image_digest(attrs),
                ports=ports,
                networks=networks,
                environment=environment,
                volumes=volumes,
                labels=labels,
                resource_limits=resource_limits,
                security_context=security_context,
                service_mesh_info=service_mesh_info
            )

        except Exception as e:
            logger.error(f"Error analyzing container {container.name}: {e}")
            return None

    def _passes_label_filters(self, labels: Dict[str, str]) -> bool:
        """Check if container passes label filters"""
        if not self.label_filters:
            return True

        for key, value in self.label_filters.items():
            if labels.get(key) != value:
                return False
        return True

    def _is_service_container_enhanced(self, container, labels: Dict[str, str],
                                     attrs: Dict[str, Any]) -> bool:
        """Enhanced service container detection with multiple criteria"""

        # Explicit service labels
        service_labels = [
            'service.name', 'service.type', 'com.docker.compose.service',
            'app', 'app.kubernetes.io/name', 'io.kubernetes.container.name'
        ]

        if any(label in labels for label in service_labels):
            return True

        # Check for service mesh sidecars
        if any(mesh in labels.get('app', '').lower() for mesh in ['istio', 'envoy', 'linkerd']):
            return True

        # Check image patterns
        image_name = container.image.tags[0] if container.image.tags else ''
        for category, indicators in self.service_indicators.items():
            if any(indicator in image_name.lower() for indicator in indicators['images']):
                return True

        # Check exposed ports
        exposed_ports = attrs.get('Config', {}).get('ExposedPorts', {})
        if exposed_ports:
            return True

        # Check for health checks
        if attrs.get('Config', {}).get('Healthcheck'):
            return True

        # Check for non-standard patterns
        if self._has_service_patterns(container, attrs):
            return True

        return False

    def _has_service_patterns(self, container, attrs: Dict[str, Any]) -> bool:
        """Check for additional service patterns"""

        # Check command patterns
        cmd = attrs.get('Config', {}).get('Cmd', [])
        if cmd:
            cmd_str = ' '.join(cmd).lower()
            service_commands = ['serve', 'server', 'start', 'run', 'exec', 'daemon']
            if any(command in cmd_str for command in service_commands):
                return True

        # Check environment variables for service indicators
        env_vars = attrs.get('Config', {}).get('Env', [])
        service_env_patterns = ['PORT=', 'HOST=', 'SERVER_', 'SERVICE_', 'API_']
        for env_var in env_vars:
            if any(pattern in env_var for pattern in service_env_patterns):
                return True

        return False

    def _extract_service_name(self, labels: Dict[str, str], container_name: str,
                            attrs: Dict[str, Any]) -> str:
        """Extract service name with priority order"""

        # Priority order for service name extraction
        name_sources = [
            labels.get('service.name'),
            labels.get('com.docker.compose.service'),
            labels.get('app'),
            labels.get('app.kubernetes.io/name'),
            labels.get('io.kubernetes.container.name'),
            container_name
        ]

        for name in name_sources:
            if name and name.strip():
                return name.strip()

        return container_name

    def _determine_service_type_enhanced(self, image_name: str, labels: Dict[str, str],
                                       attrs: Dict[str, Any]) -> str:
        """Enhanced service type determination with multiple detection methods"""

        # Check explicit type label
        if labels.get('service.type'):
            return labels['service.type']

        # Analyze image name with enhanced patterns
        image_lower = image_name.lower()

        # Check against enhanced service indicators
        for service_type, indicators in self.service_indicators.items():
            # Check image patterns
            if any(indicator in image_lower for indicator in indicators['images']):
                return service_type

            # Check labels
            for label_key, label_value in labels.items():
                if any(indicator in label_value.lower() for indicator in indicators['labels']):
                    return service_type

        # Check ports against service indicators
        exposed_ports = attrs.get('Config', {}).get('ExposedPorts', {})
        for port_spec in exposed_ports.keys():
            try:
                port_num = int(port_spec.split('/')[0])
                for service_type, indicators in self.service_indicators.items():
                    if port_num in indicators['ports']:
                        return service_type
            except (ValueError, IndexError):
                continue

        # Framework-specific detection
        framework_type = self._detect_framework_type(image_name, labels, attrs)
        if framework_type:
            return framework_type

        # Default classification
        return 'container_service'

    def _detect_framework_type(self, image_name: str, labels: Dict[str, str],
                             attrs: Dict[str, Any]) -> Optional[str]:
        """Detect specific framework types"""

        image_lower = image_name.lower()

        # Framework patterns
        frameworks = {
            'fastapi': ['fastapi', 'uvicorn'],
            'flask': ['flask', 'gunicorn'],
            'express': ['express', 'node'],
            'spring': ['spring', 'openjdk'],
            'django': ['django'],
            'rails': ['rails', 'ruby'],
            'asp_net': ['aspnet', 'dotnet'],
            'laravel': ['laravel', 'php'],
            'react': ['react', 'create-react-app'],
            'vue': ['vue', 'nuxt'],
            'angular': ['angular', 'ng']
        }

        for framework, patterns in frameworks.items():
            if any(pattern in image_lower for pattern in patterns):
                return framework

        return None

    def _determine_health_status(self, container, attrs: Dict[str, Any]) -> str:
        """Determine container health status"""

        # Check container state
        state = attrs.get('State', {})
        if not state.get('Running', False):
            return 'unhealthy'

        # Check health check results
        health = state.get('Health', {})
        if health:
            status = health.get('Status', '')
            if status == 'healthy':
                return 'healthy'
            elif status in ['unhealthy', 'starting']:
                return status

        # Check exit code
        exit_code = state.get('ExitCode', 0)
        if exit_code != 0:
            return 'unhealthy'

        # Default to healthy for running containers
        return 'healthy' if state.get('Running') else 'unknown'

    def _extract_endpoints_enhanced(self, container, attrs: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract enhanced endpoint information"""
        endpoints = []

        try:
            # Get port bindings
            port_bindings = attrs.get('HostConfig', {}).get('PortBindings', {})
            network_settings = attrs.get('NetworkSettings', {})

            for container_port, host_bindings in port_bindings.items():
                if not host_bindings:
                    continue

                port_num = int(container_port.split('/')[0])
                protocol = container_port.split('/')[1] if '/' in container_port else 'tcp'

                for binding in host_bindings:
                    host_ip = binding.get('HostIp', '0.0.0.0')
                    host_port = binding.get('HostPort')

                    if host_port:
                        endpoint = {
                            'type': self.well_known_ports.get(port_num, f'port-{port_num}'),
                            'protocol': protocol,
                            'host': host_ip if host_ip != '0.0.0.0' else 'localhost',
                            'port': int(host_port),
                            'container_port': port_num,
                            'url': self._build_endpoint_url(host_ip, host_port, port_num, protocol),
                            'health_check': self._build_health_check_endpoint(host_ip, host_port, port_num)
                        }
                        endpoints.append(endpoint)

            # Add network-specific endpoints
            networks = network_settings.get('Networks', {})
            for network_name, network_info in networks.items():
                ip_address = network_info.get('IPAddress')
                if ip_address:
                    # Add internal network endpoints
                    exposed_ports = attrs.get('Config', {}).get('ExposedPorts', {})
                    for port_spec in exposed_ports.keys():
                        try:
                            port_num = int(port_spec.split('/')[0])
                            protocol = port_spec.split('/')[1] if '/' in port_spec else 'tcp'

                            endpoint = {
                                'type': f'internal-{self.well_known_ports.get(port_num, f"port-{port_num}")}',
                                'protocol': protocol,
                                'host': ip_address,
                                'port': port_num,
                                'container_port': port_num,
                                'network': network_name,
                                'url': self._build_endpoint_url(ip_address, str(port_num), port_num, protocol),
                                'scope': 'internal'
                            }
                            endpoints.append(endpoint)
                        except (ValueError, IndexError):
                            continue

        except Exception as e:
            logger.debug(f"Error extracting enhanced endpoints: {e}")

        return endpoints

    def _build_endpoint_url(self, host_ip: str, host_port: str, port_num: int, protocol: str = 'tcp') -> str:
        """Build endpoint URL with protocol detection"""
        host = 'localhost' if host_ip == '0.0.0.0' else host_ip

        # Determine URL scheme
        if port_num in [443, 8443] or protocol == 'https':
            scheme = 'https'
        elif port_num in [80, 8080, 3000, 5000, 8000] or protocol == 'http':
            scheme = 'http'
        elif protocol in ['tcp', 'udp']:
            scheme = protocol
        else:
            scheme = 'tcp'

        if scheme in ['http', 'https']:
            return f"{scheme}://{host}:{host_port}"
        else:
            return f"{scheme}://{host}:{host_port}"

    def _build_health_check_endpoint(self, host_ip: str, host_port: str, port_num: int) -> Optional[str]:
        """Build health check endpoint URL"""
        if port_num in [80, 443, 8080, 8443, 3000, 5000, 8000, 9000]:
            scheme = 'https' if port_num in [443, 8443] else 'http'
            host = 'localhost' if host_ip == '0.0.0.0' else host_ip

            # Common health check paths
            health_paths = ['/health', '/healthz', '/status', '/ping', '/api/health']
            return f"{scheme}://{host}:{host_port}{health_paths[0]}"

        return None

    def _extract_resource_limits(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract resource limits and constraints"""
        host_config = attrs.get('HostConfig', {})

        return {
            'memory_limit': host_config.get('Memory'),
            'memory_reservation': host_config.get('MemoryReservation'),
            'memory_swap': host_config.get('MemorySwap'),
            'cpu_shares': host_config.get('CpuShares'),
            'cpu_quota': host_config.get('CpuQuota'),
            'cpu_period': host_config.get('CpuPeriod'),
            'cpuset_cpus': host_config.get('CpusetCpus'),
            'cpuset_mems': host_config.get('CpusetMems'),
            'blkio_weight': host_config.get('BlkioWeight'),
            'ulimits': host_config.get('Ulimits', [])
        }

    def _extract_security_context(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Extract security context information"""
        config = attrs.get('Config', {})
        host_config = attrs.get('HostConfig', {})

        return {
            'user': config.get('User'),
            'privileged': host_config.get('Privileged', False),
            'read_only_rootfs': host_config.get('ReadonlyRootfs', False),
            'security_opt': host_config.get('SecurityOpt', []),
            'cap_add': host_config.get('CapAdd', []),
            'cap_drop': host_config.get('CapDrop', []),
            'apparmor_profile': next((opt.split(':')[1] for opt in host_config.get('SecurityOpt', [])
                                    if opt.startswith('apparmor:')), None),
            'seccomp_profile': next((opt.split(':')[1] for opt in host_config.get('SecurityOpt', [])
                                   if opt.startswith('seccomp:')), None)
        }

    def _extract_service_mesh_info(self, labels: Dict[str, str], attrs: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract service mesh information"""
        mesh_info = {}

        # Istio detection
        if any('istio' in key.lower() or 'istio' in value.lower()
               for key, value in labels.items()):
            mesh_info['type'] = 'istio'
            mesh_info['sidecar'] = 'istio-proxy' in str(attrs.get('Config', {}).get('Image', ''))
            mesh_info['annotations'] = {k: v for k, v in labels.items() if 'istio' in k.lower()}

        # Linkerd detection
        elif any('linkerd' in key.lower() or 'linkerd' in value.lower()
                 for key, value in labels.items()):
            mesh_info['type'] = 'linkerd'
            mesh_info['sidecar'] = 'linkerd-proxy' in str(attrs.get('Config', {}).get('Image', ''))

        # Consul Connect detection
        elif any('consul' in key.lower() for key, value in labels.items()):
            mesh_info['type'] = 'consul-connect'
            mesh_info['connect_enabled'] = labels.get('consul.hashicorp.com/connect-inject', 'false') == 'true'

        return mesh_info if mesh_info else None

    def _build_enhanced_metadata(self, container, attrs: Dict[str, Any],
                                labels: Dict[str, str]) -> Dict[str, Any]:
        """Build comprehensive metadata dictionary"""
        config = attrs.get('Config', {})
        host_config = attrs.get('HostConfig', {})
        state = attrs.get('State', {})

        return {
            'container_name': container.name,
            'image': container.image.tags[0] if container.image.tags else 'unknown',
            'image_id': container.image.id[:12],
            'image_digest': self._extract_image_digest(attrs),
            'created': attrs.
