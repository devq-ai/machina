"""
FastMCP Health Monitoring Module
Provides health monitoring and metrics collection for FastMCP servers.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logfire


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """Represents a health check"""
    name: str
    check_function: Callable
    interval: int = 30  # seconds
    timeout: int = 10   # seconds
    failure_threshold: int = 3
    success_threshold: int = 1
    enabled: bool = True
    last_checked: Optional[datetime] = None
    last_result: Optional[bool] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    total_checks: int = 0
    total_failures: int = 0


@dataclass
class ServerMetrics:
    """Server performance metrics"""
    start_time: datetime = field(default_factory=datetime.now)
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    average_response_time: float = 0.0
    last_request_time: Optional[datetime] = None
    peak_memory_usage: float = 0.0
    current_memory_usage: float = 0.0
    cpu_usage: float = 0.0


class HealthMonitor:
    """
    Health monitoring system for FastMCP servers

    Provides:
    - Continuous health checks
    - Performance metrics collection
    - Status reporting
    - Alerting capabilities
    """

    def __init__(self, server_name: str):
        self.server_name = server_name
        self.health_checks: Dict[str, HealthCheck] = {}
        self.metrics = ServerMetrics()
        self.logger = logfire
        self.monitoring_active = False
        self._monitoring_task: Optional[asyncio.Task] = None
        self._request_times: List[float] = []
        self.max_request_history = 1000

    def add_health_check(
        self,
        name: str,
        check_function: Callable,
        interval: int = 30,
        timeout: int = 10,
        failure_threshold: int = 3,
        success_threshold: int = 1
    ):
        """
        Add a health check

        Args:
            name: Unique name for the health check
            check_function: Function that returns True/False for health status
            interval: Check interval in seconds
            timeout: Timeout for each check in seconds
            failure_threshold: Number of consecutive failures before marking unhealthy
            success_threshold: Number of consecutive successes before marking healthy
        """
        self.health_checks[name] = HealthCheck(
            name=name,
            check_function=check_function,
            interval=interval,
            timeout=timeout,
            failure_threshold=failure_threshold,
            success_threshold=success_threshold
        )

        self.logger.info(f"Added health check: {name}")

    def remove_health_check(self, name: str):
        """Remove a health check"""
        if name in self.health_checks:
            del self.health_checks[name]
            self.logger.info(f"Removed health check: {name}")

    async def run_health_check(self, check: HealthCheck) -> bool:
        """
        Run a single health check

        Args:
            check: HealthCheck to execute

        Returns:
            True if healthy, False if unhealthy
        """
        if not check.enabled:
            return True

        try:
            # Run the check with timeout
            result = await asyncio.wait_for(
                self._execute_check(check.check_function),
                timeout=check.timeout
            )

            check.last_checked = datetime.now()
            check.last_result = result
            check.total_checks += 1

            if result:
                check.consecutive_successes += 1
                check.consecutive_failures = 0
            else:
                check.consecutive_failures += 1
                check.consecutive_successes = 0
                check.total_failures += 1

            return result

        except asyncio.TimeoutError:
            self.logger.warning(f"Health check '{check.name}' timed out")
            check.consecutive_failures += 1
            check.consecutive_successes = 0
            check.total_failures += 1
            check.last_result = False
            return False

        except Exception as e:
            self.logger.error(f"Health check '{check.name}' failed", error=str(e))
            check.consecutive_failures += 1
            check.consecutive_successes = 0
            check.total_failures += 1
            check.last_result = False
            return False

    async def _execute_check(self, check_function: Callable) -> bool:
        """Execute a health check function safely"""
        if asyncio.iscoroutinefunction(check_function):
            return await check_function()
        else:
            return await asyncio.get_event_loop().run_in_executor(None, check_function)

    def get_health_status(self) -> HealthStatus:
        """
        Get overall health status

        Returns:
            HealthStatus enum value
        """
        if not self.health_checks:
            return HealthStatus.UNKNOWN

        unhealthy_checks = 0
        degraded_checks = 0

        for check in self.health_checks.values():
            if not check.enabled:
                continue

            if check.consecutive_failures >= check.failure_threshold:
                unhealthy_checks += 1
            elif check.consecutive_failures > 0:
                degraded_checks += 1

        if unhealthy_checks > 0:
            return HealthStatus.UNHEALTHY
        elif degraded_checks > 0:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY

    def record_request(self, response_time: float, success: bool = True):
        """
        Record a request for metrics collection

        Args:
            response_time: Response time in seconds
            success: Whether the request was successful
        """
        self.metrics.total_requests += 1
        self.metrics.last_request_time = datetime.now()

        if success:
            self.metrics.successful_requests += 1
        else:
            self.metrics.failed_requests += 1

        # Track response times
        self._request_times.append(response_time)
        if len(self._request_times) > self.max_request_history:
            self._request_times.pop(0)

        # Update average response time
        self.metrics.average_response_time = sum(self._request_times) / len(self._request_times)

    def get_detailed_status(self) -> Dict[str, Any]:
        """
        Get detailed health and performance status

        Returns:
            Dictionary with comprehensive status information
        """
        uptime = datetime.now() - self.metrics.start_time

        return {
            "server_name": self.server_name,
            "status": self.get_health_status().value,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "health_checks": {
                check.name: {
                    "enabled": check.enabled,
                    "last_checked": check.last_checked.isoformat() if check.last_checked else None,
                    "last_result": check.last_result,
                    "consecutive_failures": check.consecutive_failures,
                    "consecutive_successes": check.consecutive_successes,
                    "total_checks": check.total_checks,
                    "total_failures": check.total_failures,
                    "failure_rate": check.total_failures / max(check.total_checks, 1),
                    "status": "unhealthy" if check.consecutive_failures >= check.failure_threshold
                             else "degraded" if check.consecutive_failures > 0
                             else "healthy"
                }
                for check in self.health_checks.values()
            },
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "successful_requests": self.metrics.successful_requests,
                "failed_requests": self.metrics.failed_requests,
                "success_rate": self.metrics.successful_requests / max(self.metrics.total_requests, 1),
                "average_response_time": self.metrics.average_response_time,
                "last_request_time": self.metrics.last_request_time.isoformat() if self.metrics.last_request_time else None
            }
        }

    def get_simple_status(self) -> Dict[str, Any]:
        """
        Get simple health status for quick checks

        Returns:
            Dictionary with basic status information
        """
        return {
            "status": self.get_health_status().value,
            "server_name": self.server_name,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": (datetime.now() - self.metrics.start_time).total_seconds(),
            "total_requests": self.metrics.total_requests,
            "success_rate": self.metrics.successful_requests / max(self.metrics.total_requests, 1)
        }

    async def start_monitoring(self):
        """Start the health monitoring background task"""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        self.logger.info(f"Started health monitoring for {self.server_name}")

    async def stop_monitoring(self):
        """Stop the health monitoring background task"""
        self.monitoring_active = False
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        self.logger.info(f"Stopped health monitoring for {self.server_name}")

    async def _monitoring_loop(self):
        """Main monitoring loop that runs health checks"""
        self.logger.info("Health monitoring loop started")

        while self.monitoring_active:
            try:
                # Run health checks that are due
                for check in self.health_checks.values():
                    if not check.enabled:
                        continue

                    # Check if it's time to run this health check
                    if (check.last_checked is None or
                        (datetime.now() - check.last_checked).total_seconds() >= check.interval):

                        await self.run_health_check(check)

                # Sleep for a short interval before next iteration
                await asyncio.sleep(5)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in health monitoring loop", error=str(e))
                await asyncio.sleep(5)

    def add_default_health_checks(self):
        """Add default health checks"""

        def basic_health_check():
            """Basic health check that always returns True"""
            return True

        def memory_health_check():
            """Memory usage health check"""
            try:
                import psutil
                memory_percent = psutil.virtual_memory().percent
                return memory_percent < 90.0  # Unhealthy if over 90% memory usage
            except ImportError:
                return True  # If psutil not available, assume healthy

        self.add_health_check("basic", basic_health_check, interval=30)
        self.add_health_check("memory", memory_health_check, interval=60)
