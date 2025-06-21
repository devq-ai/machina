"""
Health Probe System Module

This module provides comprehensive health checking capabilities for discovered services
through various probe types including HTTP endpoints, TCP connections, and custom checks.
"""

import asyncio
import socket
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp
import ssl

logger = logging.getLogger(__name__)


@dataclass
class HealthResult:
    """Data class representing health check results"""
    status: str  # 'healthy', 'unhealthy', 'unknown', 'timeout'
    response_time: Optional[float] = None
    reason: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    checked_at: Optional[str] = None
    probe_type: Optional[str] = None

    def __post_init__(self):
        if self.checked_at is None:
            self.checked_at = datetime.now().isoformat()


class HealthProbe(ABC):
    """
    Abstract base class for health probes.
    """

    def __init__(self, timeout: float = 5.0, retries: int = 3, retry_delay: float = 1.0):
        """
        Initialize the health probe.

        Args:
            timeout: Timeout in seconds for health checks
            retries: Number of retry attempts
            retry_delay: Delay between retries in seconds
        """
        self.timeout = timeout
        self.retries = retries
        self.retry_delay = retry_delay

    @abstractmethod
    async def check_health(self, service: Dict[str, Any]) -> HealthResult:
        """
        Check the health of a service.

        Args:
            service: Service information dictionary

        Returns:
            HealthResult object with check results
        """
        pass

    def _create_result(self, status: str, response_time: Optional[float] = None,
                      reason: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> HealthResult:
        """Create a standardized HealthResult."""
        return HealthResult(
            status=status,
            response_time=response_time,
            reason=reason,
            details=details,
            probe_type=self.__class__.__name__
        )


class HttpHealthProbe(HealthProbe):
    """
    HTTP-based health probe for services with HTTP endpoints.
    """

    def __init__(self, timeout: float = 5.0, retries: int = 3, retry_delay: float = 1.0,
                 verify_ssl: bool = False, follow_redirects: bool = True):
        """
        Initialize HTTP health probe.

        Args:
            timeout: HTTP request timeout
            retries: Number of retry attempts
            retry_delay: Delay between retries
            verify_ssl: Whether to verify SSL certificates
            follow_redirects: Whether to follow HTTP redirects
        """
        super().__init__(timeout, retries, retry_delay)
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects

    async def check_health(self, service: Dict[str, Any]) -> HealthResult:
        """
        Check service health via HTTP endpoint.

        Args:
            service: Service information containing health_endpoint

        Returns:
            HealthResult with HTTP check results
        """
        health_endpoint = service.get('health_endpoint')
        if not health_endpoint:
            return self._create_result(
                'unknown',
                reason='No health endpoint defined'
            )

        # Ensure the endpoint is a valid URL
        if not health_endpoint.startswith(('http://', 'https://')):
            # Try to construct URL from service info
            host = service.get('host', 'localhost')
            port = service.get('port')
            if port:
                health_endpoint = f"http://{host}:{port}{health_endpoint}"
            else:
                return self._create_result(
                    'unknown',
                    reason='Invalid health endpoint format'
                )

        # Configure SSL context
        ssl_context = None
        if not self.verify_ssl:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        # Configure connector
        connector = aiohttp.TCPConnector(ssl=ssl_context)

        for attempt in range(self.retries):
            start_time = time.time()

            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                ) as session:
                    async with session.get(
                        health_endpoint,
                        allow_redirects=self.follow_redirects
                    ) as response:
                        end_time = time.time()
                        response_time = end_time - start_time

                        # Read response content (limited)
                        try:
                            content = await response.text()
                            content = content[:500]  # Limit response size
                        except Exception:
                            content = ""

                        details = {
                            'url': health_endpoint,
                            'status_code': response.status,
                            'headers': dict(response.headers),
                            'content_preview': content,
                            'attempt': attempt + 1
                        }

                        if response.status < 400:
                            return self._create_result(
                                'healthy',
                                response_time=response_time,
                                reason=f'HTTP {response.status}',
                                details=details
                            )
                        else:
                            if attempt == self.retries - 1:
                                return self._create_result(
                                    'unhealthy',
                                    response_time=response_time,
                                    reason=f'HTTP {response.status}',
                                    details=details
                                )

            except asyncio.TimeoutError:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'timeout',
                        reason=f'Request timeout after {self.timeout}s',
                        details={'url': health_endpoint, 'timeout': self.timeout}
                    )
            except aiohttp.ClientError as e:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'unhealthy',
                        reason=f'HTTP client error: {str(e)}',
                        details={'url': health_endpoint, 'error': str(e)}
                    )
            except Exception as e:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'unhealthy',
                        reason=f'Unexpected error: {str(e)}',
                        details={'url': health_endpoint, 'error': str(e)}
                    )

            # Wait before retry
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)

        return self._create_result('unknown', reason='All retries exhausted')


class TcpHealthProbe(HealthProbe):
    """
    TCP-based health probe for services with TCP endpoints.
    """

    async def check_health(self, service: Dict[str, Any]) -> HealthResult:
        """
        Check service health via TCP connection.

        Args:
            service: Service information containing host and port

        Returns:
            HealthResult with TCP check results
        """
        host = service.get('host')
        port = service.get('port')

        if not host or not port:
            return self._create_result(
                'unknown',
                reason='Missing host or port information'
            )

        for attempt in range(self.retries):
            start_time = time.time()

            try:
                # Use asyncio for non-blocking socket operations
                future = asyncio.open_connection(host, port)
                reader, writer = await asyncio.wait_for(future, timeout=self.timeout)

                end_time = time.time()
                response_time = end_time - start_time

                # Close the connection
                writer.close()
                await writer.wait_closed()

                return self._create_result(
                    'healthy',
                    response_time=response_time,
                    reason='TCP connection successful',
                    details={
                        'host': host,
                        'port': port,
                        'attempt': attempt + 1
                    }
                )

            except asyncio.TimeoutError:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'timeout',
                        reason=f'TCP connection timeout after {self.timeout}s',
                        details={'host': host, 'port': port, 'timeout': self.timeout}
                    )
            except (OSError, ConnectionRefusedError, socket.gaierror) as e:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'unhealthy',
                        reason=f'TCP connection failed: {str(e)}',
                        details={'host': host, 'port': port, 'error': str(e)}
                    )
            except Exception as e:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'unhealthy',
                        reason=f'Unexpected error: {str(e)}',
                        details={'host': host, 'port': port, 'error': str(e)}
                    )

            # Wait before retry
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)

        return self._create_result('unknown', reason='All retries exhausted')


class ProcessHealthProbe(HealthProbe):
    """
    Process-based health probe that checks if a process is running.
    """

    async def check_health(self, service: Dict[str, Any]) -> HealthResult:
        """
        Check service health by verifying process existence.

        Args:
            service: Service information containing process information

        Returns:
            HealthResult with process check results
        """
        import psutil

        process_name = service.get('process_name')
        pid = service.get('pid')

        if not process_name and not pid:
            return self._create_result(
                'unknown',
                reason='No process name or PID specified'
            )

        try:
            if pid:
                # Check specific PID
                if psutil.pid_exists(pid):
                    process = psutil.Process(pid)
                    if process.is_running():
                        return self._create_result(
                            'healthy',
                            reason=f'Process {pid} is running',
                            details={
                                'pid': pid,
                                'name': process.name(),
                                'status': process.status(),
                                'memory_percent': process.memory_percent(),
                                'cpu_percent': process.cpu_percent()
                            }
                        )
                return self._create_result(
                    'unhealthy',
                    reason=f'Process {pid} not found or not running'
                )

            elif process_name:
                # Check by process name
                for proc in psutil.process_iter(['pid', 'name', 'status']):
                    try:
                        if proc.info['name'] == process_name:
                            return self._create_result(
                                'healthy',
                                reason=f'Process {process_name} found',
                                details={
                                    'pid': proc.info['pid'],
                                    'name': proc.info['name'],
                                    'status': proc.info['status']
                                }
                            )
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue

                return self._create_result(
                    'unhealthy',
                    reason=f'Process {process_name} not found'
                )

        except Exception as e:
            return self._create_result(
                'unhealthy',
                reason=f'Process check error: {str(e)}',
                details={'error': str(e)}
            )


class CustomScriptProbe(HealthProbe):
    """
    Custom script-based health probe that executes user-defined scripts.
    """

    def __init__(self, timeout: float = 10.0, retries: int = 1, retry_delay: float = 1.0):
        super().__init__(timeout, retries, retry_delay)

    async def check_health(self, service: Dict[str, Any]) -> HealthResult:
        """
        Check service health by executing a custom script.

        Args:
            service: Service information containing script path

        Returns:
            HealthResult with script execution results
        """
        script_path = service.get('health_script')
        script_args = service.get('health_script_args', [])

        if not script_path:
            return self._create_result(
                'unknown',
                reason='No health script specified'
            )

        for attempt in range(self.retries):
            start_time = time.time()

            try:
                # Execute the script
                cmd = [script_path] + script_args
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout
                )

                end_time = time.time()
                response_time = end_time - start_time

                # Decode output
                stdout_text = stdout.decode('utf-8', errors='ignore')
                stderr_text = stderr.decode('utf-8', errors='ignore')

                details = {
                    'script_path': script_path,
                    'exit_code': process.returncode,
                    'stdout': stdout_text[:500],  # Limit output
                    'stderr': stderr_text[:500],
                    'attempt': attempt + 1
                }

                if process.returncode == 0:
                    return self._create_result(
                        'healthy',
                        response_time=response_time,
                        reason='Script executed successfully',
                        details=details
                    )
                else:
                    if attempt == self.retries - 1:
                        return self._create_result(
                            'unhealthy',
                            response_time=response_time,
                            reason=f'Script failed with exit code {process.returncode}',
                            details=details
                        )

            except asyncio.TimeoutError:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'timeout',
                        reason=f'Script timeout after {self.timeout}s',
                        details={'script_path': script_path, 'timeout': self.timeout}
                    )
            except Exception as e:
                if attempt == self.retries - 1:
                    return self._create_result(
                        'unhealthy',
                        reason=f'Script execution error: {str(e)}',
                        details={'script_path': script_path, 'error': str(e)}
                    )

            # Wait before retry
            if attempt < self.retries - 1:
                await asyncio.sleep(self.retry_delay)

        return self._create_result('unknown', reason='All retries exhausted')


class CompositeHealthProbe(HealthProbe):
    """
    Composite health probe that combines multiple probe types.
    """

    def __init__(self, probes: List[HealthProbe], require_all: bool = False):
        """
        Initialize composite probe.

        Args:
            probes: List of health probes to execute
            require_all: If True, all probes must pass; if False, any probe passing is sufficient
        """
        super().__init__()
        self.probes = probes
        self.require_all = require_all

    async def check_health(self, service: Dict[str, Any]) -> HealthResult:
        """
        Check service health using multiple probe types.

        Args:
            service: Service information

        Returns:
            HealthResult aggregating all probe results
        """
        results = []
        total_response_time = 0.0

        for probe in self.probes:
            try:
                result = await probe.check_health(service)
                results.append(result)
                if result.response_time:
                    total_response_time += result.response_time
            except Exception as e:
                logger.error(f"Error in probe {probe.__class__.__name__}: {e}")
                results.append(HealthResult(
                    status='unhealthy',
                    reason=f'Probe error: {str(e)}',
                    probe_type=probe.__class__.__name__
                ))

        if not results:
            return self._create_result('unknown', reason='No probes executed')

        # Determine overall status
        healthy_count = sum(1 for r in results if r.status == 'healthy')

        if self.require_all:
            overall_status = 'healthy' if healthy_count == len(results) else 'unhealthy'
        else:
            overall_status = 'healthy' if healthy_count > 0 else 'unhealthy'

        # If no healthy results, check for timeouts
        if healthy_count == 0:
            timeout_count = sum(1 for r in results if r.status == 'timeout')
            if timeout_count > 0:
                overall_status = 'timeout'

        return self._create_result(
            overall_status,
            response_time=total_response_time,
            reason=f'{healthy_count}/{len(results)} probes healthy',
            details={
                'probe_results': [
                    {
                        'probe_type': r.probe_type,
                        'status': r.status,
                        'reason': r.reason,
                        'response_time': r.response_time
                    }
                    for r in results
                ],
                'require_all': self.require_all
            }
        )


class HealthProbeFactory:
    """
    Factory class for creating appropriate health probes based on service configuration.
    """

    @staticmethod
    def create_probe(service: Dict[str, Any], probe_config: Optional[Dict[str, Any]] = None) -> HealthProbe:
        """
        Create an appropriate health probe for a service.

        Args:
            service: Service information
            probe_config: Optional probe configuration

        Returns:
            Configured health probe instance
        """
        probe_config = probe_config or {}

        # Determine probe type based on service configuration
        if service.get('health_endpoint'):
            return HttpHealthProbe(
                timeout=probe_config.get('timeout', 5.0),
                retries=probe_config.get('retries', 3),
                retry_delay=probe_config.get('retry_delay', 1.0),
                verify_ssl=probe_config.get('verify_ssl', False)
            )

        elif service.get('host') and service.get('port'):
            return TcpHealthProbe(
                timeout=probe_config.get('timeout', 5.0),
                retries=probe_config.get('retries', 3),
                retry_delay=probe_config.get('retry_delay', 1.0)
            )

        elif service.get('health_script'):
            return CustomScriptProbe(
                timeout=probe_config.get('timeout', 10.0),
                retries=probe_config.get('retries', 1),
                retry_delay=probe_config.get('retry_delay', 1.0)
            )

        elif service.get('process_name') or service.get('pid'):
            return ProcessHealthProbe(
                timeout=probe_config.get('timeout', 5.0),
                retries=probe_config.get('retries', 1),
                retry_delay=probe_config.get('retry_delay', 1.0)
            )

        else:
            # Return a basic TCP probe as fallback
            return TcpHealthProbe(
                timeout=probe_config.get('timeout', 5.0),
                retries=probe_config.get('retries', 3),
                retry_delay=probe_config.get('retry_delay', 1.0)
            )

    @staticmethod
    def create_composite_probe(service: Dict[str, Any],
                              probe_configs: List[Dict[str, Any]],
                              require_all: bool = False) -> CompositeHealthProbe:
        """
        Create a composite probe with multiple probe types.

        Args:
            service: Service information
            probe_configs: List of probe configurations
            require_all: Whether all probes must pass

        Returns:
            Configured composite health probe
        """
        probes = []

        for config in probe_configs:
            probe_type = config.get('type')

            if probe_type == 'http':
                probes.append(HttpHealthProbe(**config.get('options', {})))
            elif probe_type == 'tcp':
                probes.append(TcpHealthProbe(**config.get('options', {})))
            elif probe_type == 'process':
                probes.append(ProcessHealthProbe(**config.get('options', {})))
            elif probe_type == 'script':
                probes.append(CustomScriptProbe(**config.get('options', {})))

        return CompositeHealthProbe(probes, require_all)
