"""
Docker Service Discovery Module

This module provides comprehensive Docker-based service discovery capabilities,
including container inspection, service extraction, and Docker Compose analysis.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import docker
import yaml
import os
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DockerServiceInfo:
    """Data class representing Docker service information"""
    id: str
    name: str
    type: str
    status: str
    endpoints: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    container_id: Optional[str] = None
    image: Optional[str] = None
    ports: Optional[List[str]] = None
    networks: Optional[List[str]] = None
    environment: Optional[Dict[str, str]] = None
    discovered_at: Optional[str] = None

    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.now().isoformat()


class DockerServiceDiscovery:
    """
    Docker-based service discovery that inspects running containers
    and Docker Compose configurations to identify services.
    """

    def __init__(self, docker_client=None, include_stopped: bool = False,
                 label_filters: Optional[Dict[str, str]] = None):
        """
        Initialize Docker service discovery.

        Args:
            docker_client: Docker client instance (will create if None)
            include_stopped: Whether to include stopped containers
            label_filters: Dictionary of label filters to apply
        """
        try:
            self.docker_client = docker_client or docker.from_env()
        except docker.errors.DockerException as e:
            logger.error(f"Failed to connect to Docker: {e}")
            self.docker_client = None

        self.include_stopped = include_stopped
        self.label_filters = label_filters or {}

        # Service detection patterns for Docker containers
        self.service_indicators = {
            'web_server': ['nginx', 'apache', 'httpd', 'caddy'],
            'database': ['postgres', 'mysql', 'mongodb', 'redis', 'elasticsearch'],
            'message_queue': ['rabbitmq', 'kafka', 'activemq', 'nats'],
            'cache': ['redis', 'memcached', 'hazelcast'],
            'api_server': ['fastapi', 'flask', 'express', 'node', 'python', 'go'],
            'proxy': ['nginx', 'traefik', 'envoy', 'haproxy'],
            'monitoring': ['prometheus', 'grafana', 'jaeger', 'zipkin'],
            'search': ['elasticsearch', 'solr', 'sphinx']
        }

        # Common service ports
        self.service_ports = {
            80: 'http',
            443: 'https',
            3000: 'node/express',
            8000: 'fastapi/django',
            5000: 'flask',
            8080: 'tomcat/jetty',
            9000: 'php-fpm',
            3306: 'mysql',
            5432: 'postgresql',
            6379: 'redis',
            9200: 'elasticsearch',
            5672: 'rabbitmq',
            9092: 'kafka',
            8086: 'influxdb',
            3001: 'grafana'
        }

    async def discover_services(self) -> List[DockerServiceInfo]:
        """
        Discover services from Docker containers.

        Returns:
            List of discovered Docker services
        """
        if not self.docker_client:
            logger.error("Docker client not available")
            return []

        services = []

        try:
            # Discover from running containers
            container_services = await self._discover_container_services()
            services.extend(container_services)

            # Discover from Docker Compose files
            compose_services = await self._discover_compose_services()
            services.extend(compose_services)

            # Discover from Docker Swarm services (if available)
            swarm_services = await self._discover_swarm_services()
            services.extend(swarm_services)

            logger.info(f"Discovered {len(services)} Docker services")

        except Exception as e:
            logger.error(f"Error during Docker service discovery: {e}")

        return services

    async def _discover_container_services(self) -> List[DockerServiceInfo]:
        """Discover services from Docker containers."""
        services = []

        try:
            containers = self.docker_client.containers.list(all=self.include_stopped)

            for container in containers:
                service_info = await self._analyze_container(container)
                if service_info:
                    services.append(service_info)

        except docker.errors.DockerException as e:
            logger.error(f"Error listing Docker containers: {e}")

        return services

    async def _analyze_container(self, container) -> Optional[DockerServiceInfo]:
        """
        Analyze a Docker container to extract service information.

        Args:
            container: Docker container object

        Returns:
            DockerServiceInfo if service is detected, None otherwise
        """
        try:
            # Get container details
            container.reload()
            attrs = container.attrs

            # Extract basic information
            container_id = container.id[:12]
            container_name = container.name
            image_name = container.image.tags[0] if container.image.tags else 'unknown'
            status = container.status

            # Extract labels
            labels = attrs.get('Config', {}).get('Labels') or {}

            # Apply label filters
            if self.label_filters:
                for key, value in self.label_filters.items():
                    if labels.get(key) != value:
                        return None

            # Check if this is a service container
            if not self._is_service_container(container, labels):
                return None

            # Extract service information
            service_name = (
                labels.get('service.name') or
                labels.get('com.docker.compose.service') or
                container_name
            )

            service_type = self._determine_service_type(image_name, labels, attrs)

            # Extract networking information
            endpoints = self._extract_endpoints(container)
            ports = self._extract_ports(attrs)
            networks = self._extract_networks(attrs)

            # Extract environment variables
            env_vars = self._extract_environment(attrs)

            # Build metadata
            metadata = {
                'container_name': container_name,
                'image': image_name,
                'image_id': container.image.id[:12],
                'created': attrs.get('Created'),
                'started_at': attrs.get('State', {}).get('StartedAt'),
                'labels': labels,
                'command': attrs.get('Config', {}).get('Cmd'),
                'entrypoint': attrs.get('Config', {}).get('Entrypoint'),
                'working_dir': attrs.get('Config', {}).get('WorkingDir'),
                'exposed_ports': list(attrs.get('Config', {}).get('ExposedPorts', {}).keys()),
                'restart_policy': attrs.get('HostConfig', {}).get('RestartPolicy', {}),
                'memory_limit': attrs.get('HostConfig', {}).get('Memory'),
                'cpu_limit': attrs.get('HostConfig', {}).get('CpuShares')
            }

            # Add health check information if available
            health_check = attrs.get('Config', {}).get('Healthcheck')
            if health_check:
                metadata['health_check'] = health_check

            # Generate service ID
            service_id = f"docker_{service_name}_{container_id}"

            return DockerServiceInfo(
                id=service_id,
                name=service_name,
                type=service_type,
                status=status,
                endpoints=endpoints,
                metadata=metadata,
                container_id=container_id,
                image=image_name,
                ports=ports,
                networks=networks,
                environment=env_vars
            )

        except Exception as e:
            logger.error(f"Error analyzing container {container.name}: {e}")
            return None

    def _is_service_container(self, container, labels: Dict[str, str]) -> bool:
        """
        Determine if a container represents a service.

        Args:
            container: Docker container object
            labels: Container labels

        Returns:
            True if container is a service, False otherwise
        """
        # Check for explicit service labels
        if labels.get('service.name') or labels.get('service.type'):
            return True

        # Check for Docker Compose service
        if labels.get('com.docker.compose.service'):
            return True

        # Check for common service indicators in image name
        image_name = container.image.tags[0] if container.image.tags else ''
        image_name = image_name.lower()

        for category, indicators in self.service_indicators.items():
            if any(indicator in image_name for indicator in indicators):
                return True

        # Check for exposed ports (services typically expose ports)
        try:
            attrs = container.attrs
            exposed_ports = attrs.get('Config', {}).get('ExposedPorts', {})
            if exposed_ports:
                return True
        except Exception:
            pass

        # Check for health checks (services often have health checks)
        try:
            health_check = container.attrs.get('Config', {}).get('Healthcheck')
            if health_check:
                return True
        except Exception:
            pass

        return False

    def _determine_service_type(self, image_name: str, labels: Dict[str, str],
                               attrs: Dict[str, Any]) -> str:
        """
        Determine the type of service based on image and configuration.

        Args:
            image_name: Docker image name
            labels: Container labels
            attrs: Container attributes

        Returns:
            Service type string
        """
        # Check explicit service type label
        if labels.get('service.type'):
            return labels['service.type']

        # Determine from image name
        image_lower = image_name.lower()

        for service_type, indicators in self.service_indicators.items():
            if any(indicator in image_lower for indicator in indicators):
                return service_type

        # Check for specific frameworks
        if any(framework in image_lower for framework in ['fastapi', 'uvicorn']):
            return 'fastapi'
        elif any(framework in image_lower for framework in ['flask', 'gunicorn']):
            return 'flask'
        elif any(framework in image_lower for framework in ['express', 'node']):
            return 'express'
        elif 'python' in image_lower:
            return 'python'
        elif 'node' in image_lower:
            return 'node'

        # Default to generic service
        return 'container_service'

    def _extract_endpoints(self, container) -> List[Dict[str, Any]]:
        """Extract service endpoints from container port mappings."""
        endpoints = []

        try:
            attrs = container.attrs
            port_bindings = attrs.get('HostConfig', {}).get('PortBindings', {})

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
                            'type': self.service_ports.get(port_num, 'unknown'),
                            'protocol': protocol,
                            'host': host_ip if host_ip != '0.0.0.0' else 'localhost',
                            'port': int(host_port),
                            'container_port': port_num,
                            'url': self._build_endpoint_url(host_ip, host_port, port_num)
                        }
                        endpoints.append(endpoint)

        except Exception as e:
            logger.debug(f"Error extracting endpoints: {e}")

        return endpoints

    def _build_endpoint_url(self, host_ip: str, host_port: str, port_num: int) -> str:
        """Build endpoint URL from host and port information."""
        host = 'localhost' if host_ip == '0.0.0.0' else host_ip

        # Determine protocol
        if port_num in [443, 8443]:
            protocol = 'https'
        elif port_num in [80, 8080, 3000, 5000, 8000]:
            protocol = 'http'
        else:
            protocol = 'tcp'

        if protocol in ['http', 'https']:
            return f"{protocol}://{host}:{host_port}"
        else:
            return f"{protocol}://{host}:{host_port}"

    def _extract_ports(self, attrs: Dict[str, Any]) -> List[str]:
        """Extract port information from container attributes."""
        ports = []

        try:
            # Extract exposed ports
            exposed_ports = attrs.get('Config', {}).get('ExposedPorts', {})
            ports.extend(list(exposed_ports.keys()))

            # Extract port bindings
            port_bindings = attrs.get('HostConfig', {}).get('PortBindings', {})
            for container_port, host_bindings in port_bindings.items():
                if host_bindings:
                    for binding in host_bindings:
                        host_port = binding.get('HostPort')
                        if host_port:
                            ports.append(f"{host_port}:{container_port}")

        except Exception as e:
            logger.debug(f"Error extracting ports: {e}")

        return list(set(ports))  # Remove duplicates

    def _extract_networks(self, attrs: Dict[str, Any]) -> List[str]:
        """Extract network information from container attributes."""
        networks = []

        try:
            network_settings = attrs.get('NetworkSettings', {})
            container_networks = network_settings.get('Networks', {})
            networks = list(container_networks.keys())

        except Exception as e:
            logger.debug(f"Error extracting networks: {e}")

        return networks

    def _extract_environment(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        """Extract environment variables from container attributes."""
        env_vars = {}

        try:
            env_list = attrs.get('Config', {}).get('Env', [])
            for env_var in env_list:
                if '=' in env_var:
                    key, value = env_var.split('=', 1)
                    env_vars[key] = value

        except Exception as e:
            logger.debug(f"Error extracting environment: {e}")

        return env_vars

    async def _discover_compose_services(self) -> List[DockerServiceInfo]:
        """Discover services from Docker Compose files."""
        services = []

        # Common Docker Compose file locations
        compose_files = [
            'docker-compose.yml',
            'docker-compose.yaml',
            'compose.yml',
            'compose.yaml'
        ]

        for compose_file in compose_files:
            if os.path.exists(compose_file):
                try:
                    compose_services = await self._analyze_compose_file(compose_file)
                    services.extend(compose_services)
                except Exception as e:
                    logger.error(f"Error analyzing {compose_file}: {e}")

        return services

    async def _analyze_compose_file(self, compose_file: str) -> List[DockerServiceInfo]:
        """Analyze Docker Compose file to extract service definitions."""
        services = []

        try:
            with open(compose_file, 'r') as f:
                compose_data = yaml.safe_load(f)

            compose_services = compose_data.get('services', {})

            for service_name, service_config in compose_services.items():
                service_info = self._parse_compose_service(service_name, service_config, compose_file)
                if service_info:
                    services.append(service_info)

        except Exception as e:
            logger.error(f"Error parsing compose file {compose_file}: {e}")

        return services

    def _parse_compose_service(self, service_name: str, service_config: Dict[str, Any],
                              compose_file: str) -> Optional[DockerServiceInfo]:
        """Parse individual Docker Compose service configuration."""
        try:
            # Extract basic information
            image = service_config.get('image', '')
            build_config = service_config.get('build')

            # Determine service type
            service_type = self._determine_service_type(image, {}, {})

            # Extract ports
            ports = service_config.get('ports', [])
            endpoints = []

            for port_mapping in ports:
                if isinstance(port_mapping, str):
                    if ':' in port_mapping:
                        host_port, container_port = port_mapping.split(':', 1)
                        container_port = container_port.split('/')[0]
                    else:
                        host_port = container_port = port_mapping.split('/')[0]
                elif isinstance(port_mapping, dict):
                    host_port = port_mapping.get('published')
                    container_port = port_mapping.get('target')
                    protocol = port_mapping.get('protocol', 'tcp')
                else:
                    continue

                if host_port and container_port:
                    endpoint = {
                        'type': self.service_ports.get(int(container_port), 'unknown'),
                        'protocol': 'tcp',
                        'host': 'localhost',
                        'port': int(host_port),
                        'container_port': int(container_port),
                        'url': self._build_endpoint_url('localhost', str(host_port), int(container_port))
                    }
                    endpoints.append(endpoint)

            # Extract environment variables
            environment = {}
            env_config = service_config.get('environment', [])
            if isinstance(env_config, list):
                for env_var in env_config:
                    if '=' in env_var:
                        key, value = env_var.split('=', 1)
                        environment[key] = value
            elif isinstance(env_config, dict):
                environment = env_config

            # Extract networks
            networks = list(service_config.get('networks', {}).keys())

            # Build metadata
            metadata = {
                'compose_file': compose_file,
                'service_name': service_name,
                'image': image,
                'build': build_config,
                'volumes': service_config.get('volumes', []),
                'depends_on': service_config.get('depends_on', []),
                'restart': service_config.get('restart'),
                'command': service_config.get('command'),
                'entrypoint': service_config.get('entrypoint'),
                'working_dir': service_config.get('working_dir'),
                'user': service_config.get('user'),
                'healthcheck': service_config.get('healthcheck')
            }

            service_id = f"compose_{service_name}_{abs(hash(compose_file)) % 10000}"

            return DockerServiceInfo(
                id=service_id,
                name=service_name,
                type=service_type,
                status='defined',  # Compose services are defined, not necessarily running
                endpoints=endpoints,
                metadata=metadata,
                image=image,
                ports=[str(p) for p in ports],
                networks=networks,
                environment=environment
            )

        except Exception as e:
            logger.error(f"Error parsing compose service {service_name}: {e}")
            return None

    async def _discover_swarm_services(self) -> List[DockerServiceInfo]:
        """Discover services from Docker Swarm."""
        services = []

        try:
            # Check if Docker is in swarm mode
            swarm_info = self.docker_client.api.inspect_swarm()
            if not swarm_info:
                return services

            # Get swarm services
            swarm_services = self.docker_client.services.list()

            for service in swarm_services:
                service_info = self._parse_swarm_service(service)
                if service_info:
                    services.append(service_info)

        except docker.errors.APIError:
            # Not in swarm mode or no permission
            logger.debug("Docker not in swarm mode or insufficient permissions")
        except Exception as e:
            logger.error(f"Error discovering swarm services: {e}")

        return services

    def _parse_swarm_service(self, service) -> Optional[DockerServiceInfo]:
        """Parse Docker Swarm service configuration."""
        try:
            attrs = service.attrs
            spec = attrs.get('Spec', {})

            service_name = spec.get('Name', 'unknown')
            image = spec.get('TaskTemplate', {}).get('ContainerSpec', {}).get('Image', '')

            # Determine service type
            service_type = self._determine_service_type(image, {}, {})

            # Extract endpoints
            endpoints = []
            endpoint_spec = spec.get('EndpointSpec', {})
            ports = endpoint_spec.get('Ports', [])

            for port in ports:
                published_port = port.get('PublishedPort')
                target_port = port.get('TargetPort')
                protocol = port.get('Protocol', 'tcp')

                if published_port and target_port:
                    endpoint = {
                        'type': self.service_ports.get(target_port, 'unknown'),
                        'protocol': protocol,
                        'host': 'localhost',
                        'port': published_port,
                        'container_port': target_port,
                        'url': self._build_endpoint_url('localhost', str(published_port), target_port)
                    }
                    endpoints.append(endpoint)

            # Extract other information
            labels = spec.get('Labels', {})
            networks = [net.get('Target') for net in spec.get('Networks', [])]

            metadata = {
                'service_name': service_name,
                'image': image,
                'labels': labels,
                'replicas': spec.get('Mode', {}).get('Replicated', {}).get('Replicas', 1),
                'task_template': spec.get('TaskTemplate', {}),
                'update_config': spec.get('UpdateConfig', {}),
                'rollback_config': spec.get('RollbackConfig', {})
            }

            service_id = f"swarm_{service_name}_{service.id[:12]}"

            return DockerServiceInfo(
                id=service_id,
                name=service_name,
                type=service_type,
                status='running',  # Swarm services are typically running
                endpoints=endpoints,
                metadata=metadata,
                image=image,
                ports=[f"{p.get('PublishedPort')}:{p.get('TargetPort')}" for p in ports],
                networks=networks
            )

        except Exception as e:
            logger.error(f"Error parsing swarm service: {e}")
            return None

    def get_docker_info(self) -> Dict[str, Any]:
        """Get Docker daemon information."""
        if not self.docker_client:
            return {'error': 'Docker client not available'}

        try:
            info = self.docker_client.info()
            return {
                'docker_version': info.get('ServerVersion'),
                'api_version': self.docker_client.api.api_version,
                'containers': info.get('Containers'),
                'running_containers': info.get('ContainersRunning'),
                'paused_containers': info.get('ContainersPaused'),
                'stopped_containers': info.get('ContainersStopped'),
                'images': info.get('Images'),
                'swarm_mode': info.get('Swarm', {}).get('LocalNodeState') == 'active'
            }
        except Exception as e:
            logger.error(f"Error getting Docker info: {e}")
            return {'error': str(e)}

    async def monitor_container_events(self, callback=None):
        """
        Monitor Docker container events for real-time service discovery.

        Args:
            callback: Function to call when container events occur
        """
        if not self.docker_client:
            logger.error("Docker client not available for event monitoring")
            return

        try:
            events = self.docker_client.events(decode=True)

            for event in events:
                if event.get('Type') == 'container':
                    action = event.get('Action')
                    container_id = event.get('id')

                    if action in ['start', 'stop', 'die', 'create', 'destroy']:
                        logger.info(f"Container event: {action} for {container_id[:12]}")

                        if callback:
                            await callback(event)

        except Exception as e:
            logger.error(f"Error monitoring Docker events: {e}")
