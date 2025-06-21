"""
External Registry Adapter Module

This module provides comprehensive integration with external service registries
including Consul, Kubernetes, Eureka, and other service discovery platforms.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from abc import ABC, abstractmethod
import aiohttp
import ssl

logger = logging.getLogger(__name__)


@dataclass
class ExternalServiceInfo:
    """Data class representing external service information"""
    id: str
    name: str
    type: str
    registry_type: str
    endpoints: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    health_status: Optional[str] = None
    tags: Optional[List[str]] = None
    address: Optional[str] = None
    port: Optional[int] = None
    discovered_at: Optional[str] = None

    def __post_init__(self):
        if self.discovered_at is None:
            self.discovered_at = datetime.now().isoformat()


class RegistryAdapter(ABC):
    """Abstract base class for external registry adapters"""

    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize registry adapter.

        Args:
            connection_params: Connection parameters specific to registry type
        """
        self.connection_params = connection_params
        self.client = None

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the registry"""
        pass

    @abstractmethod
    async def discover_services(self) -> List[ExternalServiceInfo]:
        """Discover services from the registry"""
        pass

    @abstractmethod
    async def register_service(self, service: Dict[str, Any]) -> bool:
        """Register a service in the registry"""
        pass

    @abstractmethod
    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from the registry"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the registry is healthy"""
        pass

    async def disconnect(self):
        """Close connection to the registry"""
        if hasattr(self.client, 'close'):
            await self.client.close()


class ConsulAdapter(RegistryAdapter):
    """Adapter for HashiCorp Consul service registry"""

    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize Consul adapter.

        Expected connection_params:
        - host: Consul host (default: localhost)
        - port: Consul port (default: 8500)
        - scheme: http or https (default: http)
        - token: Consul ACL token (optional)
        - datacenter: Consul datacenter (optional)
        """
        super().__init__(connection_params)
        self.host = connection_params.get('host', 'localhost')
        self.port = connection_params.get('port', 8500)
        self.scheme = connection_params.get('scheme', 'http')
        self.token = connection_params.get('token')
        self.datacenter = connection_params.get('datacenter')

        self.base_url = f"{self.scheme}://{self.host}:{self.port}/v1"
        self.headers = {}
        if self.token:
            self.headers['X-Consul-Token'] = self.token

    async def connect(self) -> bool:
        """Establish connection to Consul"""
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            self.client = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=10)
            )

            # Test connection
            async with self.client.get(f"{self.base_url}/status/leader") as response:
                if response.status == 200:
                    logger.info(f"Connected to Consul at {self.base_url}")
                    return True

        except Exception as e:
            logger.error(f"Failed to connect to Consul: {e}")

        return False

    async def discover_services(self) -> List[ExternalServiceInfo]:
        """Discover services from Consul catalog"""
        services = []

        if not self.client:
            await self.connect()

        if not self.client:
            return services

        try:
            # Get list of services
            params = {}
            if self.datacenter:
                params['dc'] = self.datacenter

            async with self.client.get(
                f"{self.base_url}/catalog/services",
                params=params
            ) as response:
                if response.status != 200:
                    logger.error(f"Failed to get Consul services: HTTP {response.status}")
                    return services

                services_data = await response.json()

                # Get detailed information for each service
                for service_name, tags in services_data.items():
                    service_details = await self._get_service_details(service_name)
                    services.extend(service_details)

        except Exception as e:
            logger.error(f"Error discovering Consul services: {e}")

        return services

    async def _get_service_details(self, service_name: str) -> List[ExternalServiceInfo]:
        """Get detailed information for a specific service"""
        service_instances = []

        try:
            params = {}
            if self.datacenter:
                params['dc'] = self.datacenter

            async with self.client.get(
                f"{self.base_url}/catalog/service/{service_name}",
                params=params
            ) as response:
                if response.status != 200:
                    return service_instances

                instances = await response.json()

                for instance in instances:
                    # Get health information
                    health_status = await self._get_service_health(
                        service_name,
                        instance.get('ServiceID')
                    )

                    # Build endpoints
                    endpoints = []
                    address = instance.get('ServiceAddress') or instance.get('Address')
                    port = instance.get('ServicePort')

                    if address and port:
                        endpoints.append({
                            'type': 'consul_service',
                            'protocol': 'tcp',
                            'host': address,
                            'port': port,
                            'url': f"tcp://{address}:{port}"
                        })

                    service_info = ExternalServiceInfo(
                        id=f"consul_{service_name}_{instance.get('ServiceID', 'unknown')}",
                        name=service_name,
                        type='consul_service',
                        registry_type='consul',
                        endpoints=endpoints,
                        metadata={
                            'node': instance.get('Node'),
                            'node_address': instance.get('Address'),
                            'service_id': instance.get('ServiceID'),
                            'service_meta': instance.get('ServiceMeta', {}),
                            'node_meta': instance.get('NodeMeta', {}),
                            'datacenter': instance.get('Datacenter')
                        },
                        health_status=health_status,
                        tags=instance.get('ServiceTags', []),
                        address=address,
                        port=port
                    )

                    service_instances.append(service_info)

        except Exception as e:
            logger.error(f"Error getting Consul service details for {service_name}: {e}")

        return service_instances

    async def _get_service_health(self, service_name: str, service_id: str) -> str:
        """Get health status for a service instance"""
        try:
            params = {}
            if self.datacenter:
                params['dc'] = self.datacenter

            async with self.client.get(
                f"{self.base_url}/health/service/{service_name}",
                params=params
            ) as response:
                if response.status != 200:
                    return 'unknown'

                health_data = await response.json()

                for instance in health_data:
                    if instance.get('Service', {}).get('ID') == service_id:
                        checks = instance.get('Checks', [])

                        # Determine overall health
                        if all(check.get('Status') == 'passing' for check in checks):
                            return 'healthy'
                        elif any(check.get('Status') == 'critical' for check in checks):
                            return 'critical'
                        else:
                            return 'warning'

        except Exception as e:
            logger.debug(f"Error getting health for {service_name}/{service_id}: {e}")

        return 'unknown'

    async def register_service(self, service: Dict[str, Any]) -> bool:
        """Register a service in Consul"""
        try:
            service_definition = {
                'ID': service.get('id'),
                'Name': service.get('name'),
                'Tags': service.get('tags', []),
                'Meta': service.get('metadata', {}),
                'EnableTagOverride': False
            }

            # Add address and port if available
            if service.get('host'):
                service_definition['Address'] = service['host']
            if service.get('port'):
                service_definition['Port'] = int(service['port'])

            # Add health check if available
            if service.get('health_endpoint'):
                service_definition['Check'] = {
                    'HTTP': service['health_endpoint'],
                    'Interval': '10s'
                }

            async with self.client.put(
                f"{self.base_url}/agent/service/register",
                json=service_definition
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error registering service in Consul: {e}")

        return False

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from Consul"""
        try:
            async with self.client.put(
                f"{self.base_url}/agent/service/deregister/{service_id}"
            ) as response:
                return response.status == 200

        except Exception as e:
            logger.error(f"Error deregistering service from Consul: {e}")

        return False

    async def health_check(self) -> bool:
        """Check Consul health"""
        try:
            async with self.client.get(f"{self.base_url}/status/leader") as response:
                return response.status == 200
        except Exception:
            return False


class KubernetesAdapter(RegistryAdapter):
    """Adapter for Kubernetes service discovery"""

    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize Kubernetes adapter.

        Expected connection_params:
        - kubeconfig_path: Path to kubeconfig file (optional)
        - api_server: Kubernetes API server URL
        - token: Service account token
        - namespace: Target namespace (default: default)
        - verify_ssl: Whether to verify SSL certificates
        """
        super().__init__(connection_params)
        self.api_server = connection_params.get('api_server')
        self.token = connection_params.get('token')
        self.namespace = connection_params.get('namespace', 'default')
        self.verify_ssl = connection_params.get('verify_ssl', True)

        self.headers = {}
        if self.token:
            self.headers['Authorization'] = f'Bearer {self.token}'

    async def connect(self) -> bool:
        """Establish connection to Kubernetes API"""
        try:
            # Configure SSL context
            ssl_context = None
            if not self.verify_ssl:
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.client = aiohttp.ClientSession(
                connector=connector,
                headers=self.headers,
                timeout=aiohttp.ClientTimeout(total=30)
            )

            # Test connection
            async with self.client.get(f"{self.api_server}/api/v1") as response:
                if response.status == 200:
                    logger.info(f"Connected to Kubernetes API at {self.api_server}")
                    return True

        except Exception as e:
            logger.error(f"Failed to connect to Kubernetes: {e}")

        return False

    async def discover_services(self) -> List[ExternalServiceInfo]:
        """Discover services from Kubernetes"""
        services = []

        if not self.client:
            await self.connect()

        if not self.client:
            return services

        try:
            # Get services
            k8s_services = await self._get_k8s_services()
            services.extend(k8s_services)

            # Get deployments
            deployments = await self._get_k8s_deployments()
            services.extend(deployments)

            # Get statefulsets
            statefulsets = await self._get_k8s_statefulsets()
            services.extend(statefulsets)

        except Exception as e:
            logger.error(f"Error discovering Kubernetes services: {e}")

        return services

    async def _get_k8s_services(self) -> List[ExternalServiceInfo]:
        """Get Kubernetes services"""
        services = []

        try:
            async with self.client.get(
                f"{self.api_server}/api/v1/namespaces/{self.namespace}/services"
            ) as response:
                if response.status != 200:
                    return services

                data = await response.json()

                for item in data.get('items', []):
                    service_info = self._parse_k8s_service(item)
                    if service_info:
                        services.append(service_info)

        except Exception as e:
            logger.error(f"Error getting Kubernetes services: {e}")

        return services

    def _parse_k8s_service(self, service_data: Dict[str, Any]) -> Optional[ExternalServiceInfo]:
        """Parse Kubernetes service data"""
        try:
            metadata = service_data.get('metadata', {})
            spec = service_data.get('spec', {})

            service_name = metadata.get('name')
            if not service_name:
                return None

            # Build endpoints
            endpoints = []
            ports = spec.get('ports', [])
            cluster_ip = spec.get('clusterIP')

            for port in ports:
                port_number = port.get('port')
                target_port = port.get('targetPort', port_number)
                protocol = port.get('protocol', 'TCP').lower()

                if cluster_ip and port_number:
                    endpoints.append({
                        'type': 'kubernetes_service',
                        'protocol': protocol,
                        'host': cluster_ip,
                        'port': port_number,
                        'target_port': target_port,
                        'url': f"{protocol}://{cluster_ip}:{port_number}"
                    })

            return ExternalServiceInfo(
                id=f"k8s_service_{service_name}_{metadata.get('uid', 'unknown')[:8]}",
                name=service_name,
                type='kubernetes_service',
                registry_type='kubernetes',
                endpoints=endpoints,
                metadata={
                    'namespace': metadata.get('namespace'),
                    'uid': metadata.get('uid'),
                    'labels': metadata.get('labels', {}),
                    'annotations': metadata.get('annotations', {}),
                    'cluster_ip': cluster_ip,
                    'type': spec.get('type'),
                    'selector': spec.get('selector', {}),
                    'session_affinity': spec.get('sessionAffinity')
                },
                tags=list(metadata.get('labels', {}).keys()),
                address=cluster_ip,
                port=ports[0].get('port') if ports else None
            )

        except Exception as e:
            logger.error(f"Error parsing Kubernetes service: {e}")
            return None

    async def _get_k8s_deployments(self) -> List[ExternalServiceInfo]:
        """Get Kubernetes deployments"""
        deployments = []

        try:
            async with self.client.get(
                f"{self.api_server}/apis/apps/v1/namespaces/{self.namespace}/deployments"
            ) as response:
                if response.status != 200:
                    return deployments

                data = await response.json()

                for item in data.get('items', []):
                    deployment_info = self._parse_k8s_deployment(item)
                    if deployment_info:
                        deployments.append(deployment_info)

        except Exception as e:
            logger.error(f"Error getting Kubernetes deployments: {e}")

        return deployments

    def _parse_k8s_deployment(self, deployment_data: Dict[str, Any]) -> Optional[ExternalServiceInfo]:
        """Parse Kubernetes deployment data"""
        try:
            metadata = deployment_data.get('metadata', {})
            spec = deployment_data.get('spec', {})
            status = deployment_data.get('status', {})

            deployment_name = metadata.get('name')
            if not deployment_name:
                return None

            return ExternalServiceInfo(
                id=f"k8s_deployment_{deployment_name}_{metadata.get('uid', 'unknown')[:8]}",
                name=deployment_name,
                type='kubernetes_deployment',
                registry_type='kubernetes',
                endpoints=[],  # Deployments don't expose endpoints directly
                metadata={
                    'namespace': metadata.get('namespace'),
                    'uid': metadata.get('uid'),
                    'labels': metadata.get('labels', {}),
                    'annotations': metadata.get('annotations', {}),
                    'replicas': spec.get('replicas'),
                    'ready_replicas': status.get('readyReplicas'),
                    'available_replicas': status.get('availableReplicas'),
                    'selector': spec.get('selector', {}),
                    'template': spec.get('template', {})
                },
                health_status='healthy' if status.get('readyReplicas', 0) > 0 else 'unhealthy',
                tags=list(metadata.get('labels', {}).keys())
            )

        except Exception as e:
            logger.error(f"Error parsing Kubernetes deployment: {e}")
            return None

    async def _get_k8s_statefulsets(self) -> List[ExternalServiceInfo]:
        """Get Kubernetes statefulsets"""
        statefulsets = []

        try:
            async with self.client.get(
                f"{self.api_server}/apis/apps/v1/namespaces/{self.namespace}/statefulsets"
            ) as response:
                if response.status != 200:
                    return statefulsets

                data = await response.json()

                for item in data.get('items', []):
                    statefulset_info = self._parse_k8s_statefulset(item)
                    if statefulset_info:
                        statefulsets.append(statefulset_info)

        except Exception as e:
            logger.error(f"Error getting Kubernetes statefulsets: {e}")

        return statefulsets

    def _parse_k8s_statefulset(self, statefulset_data: Dict[str, Any]) -> Optional[ExternalServiceInfo]:
        """Parse Kubernetes statefulset data"""
        try:
            metadata = statefulset_data.get('metadata', {})
            spec = statefulset_data.get('spec', {})
            status = statefulset_data.get('status', {})

            statefulset_name = metadata.get('name')
            if not statefulset_name:
                return None

            return ExternalServiceInfo(
                id=f"k8s_statefulset_{statefulset_name}_{metadata.get('uid', 'unknown')[:8]}",
                name=statefulset_name,
                type='kubernetes_statefulset',
                registry_type='kubernetes',
                endpoints=[],
                metadata={
                    'namespace': metadata.get('namespace'),
                    'uid': metadata.get('uid'),
                    'labels': metadata.get('labels', {}),
                    'annotations': metadata.get('annotations', {}),
                    'replicas': spec.get('replicas'),
                    'ready_replicas': status.get('readyReplicas'),
                    'current_replicas': status.get('currentReplicas'),
                    'selector': spec.get('selector', {}),
                    'service_name': spec.get('serviceName')
                },
                health_status='healthy' if status.get('readyReplicas', 0) > 0 else 'unhealthy',
                tags=list(metadata.get('labels', {}).keys())
            )

        except Exception as e:
            logger.error(f"Error parsing Kubernetes statefulset: {e}")
            return None

    async def register_service(self, service: Dict[str, Any]) -> bool:
        """Register a service in Kubernetes (create service resource)"""
        # This would typically involve creating a Kubernetes Service resource
        # Implementation depends on specific requirements
        logger.warning("Service registration in Kubernetes not implemented")
        return False

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from Kubernetes"""
        # This would typically involve deleting a Kubernetes Service resource
        logger.warning("Service deregistration in Kubernetes not implemented")
        return False

    async def health_check(self) -> bool:
        """Check Kubernetes API health"""
        try:
            async with self.client.get(f"{self.api_server}/healthz") as response:
                return response.status == 200
        except Exception:
            return False


class EurekaAdapter(RegistryAdapter):
    """Adapter for Netflix Eureka service registry"""

    def __init__(self, connection_params: Dict[str, Any]):
        """
        Initialize Eureka adapter.

        Expected connection_params:
        - eureka_url: Eureka server URL
        - app_name: Application name for registration
        - instance_id: Instance ID for registration
        """
        super().__init__(connection_params)
        self.eureka_url = connection_params.get('eureka_url')
        self.app_name = connection_params.get('app_name')
        self.instance_id = connection_params.get('instance_id')

    async def connect(self) -> bool:
        """Establish connection to Eureka"""
        try:
            self.client = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )

            # Test connection
            async with self.client.get(f"{self.eureka_url}/apps") as response:
                if response.status == 200:
                    logger.info(f"Connected to Eureka at {self.eureka_url}")
                    return True

        except Exception as e:
            logger.error(f"Failed to connect to Eureka: {e}")

        return False

    async def discover_services(self) -> List[ExternalServiceInfo]:
        """Discover services from Eureka"""
        services = []

        if not self.client:
            await self.connect()

        if not self.client:
            return services

        try:
            async with self.client.get(
                f"{self.eureka_url}/apps",
                headers={'Accept': 'application/json'}
            ) as response:
                if response.status != 200:
                    return services

                data = await response.json()
                applications = data.get('applications', {}).get('application', [])

                if not isinstance(applications, list):
                    applications = [applications]

                for app in applications:
                    app_services = self._parse_eureka_application(app)
                    services.extend(app_services)

        except Exception as e:
            logger.error(f"Error discovering Eureka services: {e}")

        return services

    def _parse_eureka_application(self, app_data: Dict[str, Any]) -> List[ExternalServiceInfo]:
        """Parse Eureka application data"""
        services = []

        try:
            app_name = app_data.get('name')
            instances = app_data.get('instance', [])

            if not isinstance(instances, list):
                instances = [instances]

            for instance in instances:
                instance_id = instance.get('instanceId')
                host_name = instance.get('hostName')
                ip_addr = instance.get('ipAddr')
                port = instance.get('port', {}).get('$', 0)
                secure_port = instance.get('securePort', {}).get('$', 0)
                status = instance.get('status')

                # Build endpoints
                endpoints = []
                if port and port != 0:
                    endpoints.append({
                        'type': 'eureka_http',
                        'protocol': 'http',
                        'host': ip_addr or host_name,
                        'port': int(port),
                        'url': f"http://{ip_addr or host_name}:{port}"
                    })

                if secure_port and secure_port != 0:
                    endpoints.append({
                        'type': 'eureka_https',
                        'protocol': 'https',
                        'host': ip_addr or host_name,
                        'port': int(secure_port),
                        'url': f"https://{ip_addr or host_name}:{secure_port}"
                    })

                service_info = ExternalServiceInfo(
                    id=f"eureka_{app_name}_{instance_id}",
                    name=app_name,
                    type='eureka_service',
                    registry_type='eureka',
                    endpoints=endpoints,
                    metadata={
                        'instance_id': instance_id,
                        'host_name': host_name,
                        'ip_addr': ip_addr,
                        'vip_address': instance.get('vipAddress'),
                        'secure_vip_address': instance.get('secureVipAddress'),
                        'app': instance.get('app'),
                        'datacenter_info': instance.get('dataCenterInfo', {}),
                        'lease_info': instance.get('leaseInfo', {}),
                        'metadata': instance.get('metadata', {})
                    },
                    health_status='healthy' if status == 'UP' else 'unhealthy',
                    address=ip_addr or host_name,
                    port=int(port) if port else None
                )

                services.append(service_info)

        except Exception as e:
            logger.error(f"Error parsing Eureka application: {e}")

        return services

    async def register_service(self, service: Dict[str, Any]) -> bool:
        """Register a service in Eureka"""
        # Implementation for Eureka service registration
        logger.warning("Service registration in Eureka not fully implemented")
        return False

    async def deregister_service(self, service_id: str) -> bool:
        """Deregister a service from Eureka"""
        logger.warning("Service deregistration in Eureka not fully implemented")
        return False

    async def health_check(self) -> bool:
        """Check Eureka health"""
        try:
            async with self.client.get(f"{self.eureka_url}/apps") as response:
                return response.status == 200
        except Exception:
            return False


class ExternalRegistryAdapter:
    """
    Main adapter class that manages multiple external registry connections.
    """

    def __init__(self):
        """Initialize the external registry adapter"""
        self.adapters: Dict[str, RegistryAdapter] = {}

    def add_registry(self, name: str, registry_type: str, connection_params: Dict[str, Any]) -> bool:
        """
        Add a registry adapter.

        Args:
            name: Unique name for the registry
            registry_type: Type of registry (consul, kubernetes, eureka)
            connection_params: Connection parameters

        Returns:
            True if adapter was added successfully
        """
        try:
            if registry_type.lower() == 'consul':
                adapter = ConsulAdapter(connection_params)
            elif registry_type.lower() == 'kubernetes':
                adapter = KubernetesAdapter(connection_params)
            elif registry_type.lower() == 'eureka':
                adapter = EurekaAdapter(connection_params)
            else:
                logger.error(f"Unsupported registry type: {registry_type}")
                return False

            self.adapters[name] = adapter
            logger.info(f"Added {registry_type} registry adapter: {name}")
            return True

        except Exception as e:
            logger.error(f"Error adding registry adapter {name}: {e}")
            return False

    async def discover_all_services(self) -> List[ExternalServiceInfo]:
        """Discover services from all configured registries"""
        all_services = []

        for name, adapter in self.adapters.items():
            try:
                logger.info(f"Discovering services from {name}")
                services = await adapter.discover_services()
                all_services.extend(services)
                logger.info(f"Discovered {len(services)} services from {name}")

            except Exception as e:
                logger.error(f"Error discovering services from {name}: {e}")

        return all_services

    async def connect_all(self) -> Dict[str, bool]:
        """Connect to all configured registries"""
        connection_results = {}

        for name, adapter in self.adapters.items():
            try:
                connected = await adapter.connect()
                connection_results[name] = connected

                if connected:
                    logger.info(f"Successfully connected to {name}")
                else:
                    logger.warning(f"Failed to connect to {name}")

            except Exception as e:
                logger.error(f"Error connecting to {name}: {e}")
                connection_results[name] = False

        return connection_results

    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all configured registries"""
        health_results = {}

        for name, adapter in self.adapters.items():
            try:
                healthy = await adapter.health_check()
                health_results[name] = healthy

            except Exception as e:
                logger.error(f"Error checking health of {name}: {e}")
                health_results[name] = False

        return health_results

    async def disconnect_all(self):
        """Disconnect from all registries"""
        for name, adapter in self.adapters.items():
            try:
                await adapter.disconnect()
                logger.info(f"Disconnected from {name}")

            except Exception as e:
                logger.error(f"Error disconnecting from {name}: {e}")

    def get_registry_info(self) -> Dict[str, Any]:
        """Get information about configured registries"""
        return {
            'total_registries': len(self.adapters),
            'registry_names': list(self.adapters.keys()),
            'registry_types': [
                type(adapter).__name__.replace('Adapter', '').lower()
                for adapter in self.adapters.values()
            ]
        }
