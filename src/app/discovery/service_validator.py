"""
Service Validator Module

This module provides comprehensive validation capabilities for discovered services,
including structure validation, dependency checking, and integration with health probes.
"""

import logging
import re
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import json
import asyncio

from .health_probe import HealthProbeFactory, HealthResult

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Data class representing service validation results"""
    is_valid: bool
    service_id: str
    validation_type: str
    issues: List[str]
    warnings: List[str]
    health_result: Optional[HealthResult] = None
    validated_at: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.validated_at is None:
            self.validated_at = datetime.now().isoformat()


class ServiceValidator:
    """
    Comprehensive service validator that checks service structure, configuration,
    and health status.
    """

    def __init__(self, enable_health_checks: bool = True,
                 health_check_timeout: float = 5.0,
                 strict_validation: bool = False):
        """
        Initialize the service validator.

        Args:
            enable_health_checks: Whether to perform health checks during validation
            health_check_timeout: Timeout for health checks
            strict_validation: Whether to apply strict validation rules
        """
        self.enable_health_checks = enable_health_checks
        self.health_check_timeout = health_check_timeout
        self.strict_validation = strict_validation

        # Required fields for different service types
        self.required_fields = {
            'base': ['id', 'name', 'type', 'location'],
            'node': ['name', 'version', 'main'],
            'python': ['name', 'type'],
            'docker': ['name', 'type'],
            'mcp': ['name', 'protocol', 'command'],
            'fastapi': ['name', 'type', 'location'],
            'flask': ['name', 'type', 'location'],
            'express': ['name', 'type', 'location']
        }

        # Optional but recommended fields
        self.recommended_fields = {
            'base': ['description', 'version', 'tags'],
            'node': ['description', 'scripts', 'dependencies'],
            'python': ['description', 'version', 'dependencies'],
            'docker': ['description', 'exposed_ports'],
            'mcp': ['description', 'args', 'env'],
            'fastapi': ['description', 'version', 'host', 'port'],
            'flask': ['description', 'version', 'host', 'port'],
            'express': ['description', 'version', 'host', 'port']
        }

        # Validation patterns
        self.validation_patterns = {
            'name': r'^[a-zA-Z0-9_-]+$',
            'version': r'^\d+\.\d+\.\d+',
            'port': r'^\d{1,5}$',
            'host': r'^[a-zA-Z0-9.-]+$',
            'protocol': r'^(stdio|http|https|tcp|udp)$'
        }

        # Dangerous configurations to flag
        self.security_checks = [
            'password',
            'secret',
            'token',
            'key',
            'private',
            'credential'
        ]

    async def validate_service(self, service: Dict[str, Any]) -> ValidationResult:
        """
        Validate a discovered service comprehensively.

        Args:
            service: Service information dictionary

        Returns:
            ValidationResult with validation details
        """
        service_id = service.get('id', 'unknown')
        service_type = service.get('type', 'unknown')

        issues = []
        warnings = []
        health_result = None

        logger.info(f"Validating service: {service_id} (type: {service_type})")

        # 1. Structure validation
        structure_issues = self._validate_structure(service)
        issues.extend(structure_issues)

        # 2. Type-specific validation
        type_issues, type_warnings = self._validate_service_type(service)
        issues.extend(type_issues)
        warnings.extend(type_warnings)

        # 3. Configuration validation
        config_issues, config_warnings = self._validate_configuration(service)
        issues.extend(config_issues)
        warnings.extend(config_warnings)

        # 4. Security validation
        security_warnings = self._validate_security(service)
        warnings.extend(security_warnings)

        # 5. Dependency validation
        dependency_issues = self._validate_dependencies(service)
        issues.extend(dependency_issues)

        # 6. Health check validation
        if self.enable_health_checks:
            try:
                health_result = await self._perform_health_check(service)
                if health_result.status == 'unhealthy':
                    issues.append(f"Health check failed: {health_result.reason}")
                elif health_result.status == 'timeout':
                    warnings.append(f"Health check timeout: {health_result.reason}")
            except Exception as e:
                warnings.append(f"Health check error: {str(e)}")

        # Determine overall validation result
        is_valid = len(issues) == 0
        if self.strict_validation:
            is_valid = is_valid and len(warnings) == 0

        return ValidationResult(
            is_valid=is_valid,
            service_id=service_id,
            validation_type='comprehensive',
            issues=issues,
            warnings=warnings,
            health_result=health_result,
            metadata={
                'service_type': service_type,
                'strict_mode': self.strict_validation,
                'health_checks_enabled': self.enable_health_checks
            }
        )

    def _validate_structure(self, service: Dict[str, Any]) -> List[str]:
        """Validate basic service structure."""
        issues = []

        # Check required base fields
        required = self.required_fields.get('base', [])
        for field in required:
            if field not in service:
                issues.append(f"Missing required field: {field}")
            elif not service[field]:
                issues.append(f"Empty required field: {field}")

        # Validate field types
        if 'id' in service and not isinstance(service['id'], str):
            issues.append("Field 'id' must be a string")

        if 'name' in service and not isinstance(service['name'], str):
            issues.append("Field 'name' must be a string")

        if 'type' in service and not isinstance(service['type'], str):
            issues.append("Field 'type' must be a string")

        # Validate metadata structure if present
        if 'metadata' in service:
            if not isinstance(service['metadata'], dict):
                issues.append("Field 'metadata' must be a dictionary")

        return issues

    def _validate_service_type(self, service: Dict[str, Any]) -> tuple:
        """Validate service-type specific requirements."""
        issues = []
        warnings = []

        service_type = service.get('type', '')

        # Check type-specific required fields
        if service_type in self.required_fields:
            type_required = self.required_fields[service_type]
            for field in type_required:
                if field not in service and field not in service.get('metadata', {}):
                    issues.append(f"Missing required field for {service_type}: {field}")

        # Check recommended fields
        if service_type in self.recommended_fields:
            type_recommended = self.recommended_fields[service_type]
            for field in type_recommended:
                if field not in service and field not in service.get('metadata', {}):
                    warnings.append(f"Missing recommended field for {service_type}: {field}")

        # Type-specific validations
        if service_type == 'node':
            issues.extend(self._validate_node_service(service))
        elif service_type == 'python':
            issues.extend(self._validate_python_service(service))
        elif service_type == 'docker':
            issues.extend(self._validate_docker_service(service))
        elif service_type == 'mcp':
            issues.extend(self._validate_mcp_service(service))
        elif service_type in ['fastapi', 'flask', 'express']:
            issues.extend(self._validate_web_service(service))

        return issues, warnings

    def _validate_node_service(self, service: Dict[str, Any]) -> List[str]:
        """Validate Node.js service specific requirements."""
        issues = []
        metadata = service.get('metadata', {})

        # Check package.json requirements
        if 'main' in metadata:
            main_file = metadata['main']
            if not main_file.endswith('.js'):
                warnings = []  # Convert to warning instead of issue

        # Validate scripts
        if 'scripts' in metadata:
            scripts = metadata['scripts']
            if not isinstance(scripts, dict):
                issues.append("Node.js scripts must be a dictionary")
            elif 'start' not in scripts:
                issues.append("Node.js service missing 'start' script")

        # Check dependencies
        if 'dependencies' in metadata:
            deps = metadata['dependencies']
            if not isinstance(deps, (list, dict)):
                issues.append("Node.js dependencies must be a list or dictionary")

        return issues

    def _validate_python_service(self, service: Dict[str, Any]) -> List[str]:
        """Validate Python service specific requirements."""
        issues = []
        metadata = service.get('metadata', {})

        # Check for Python-specific files
        location = service.get('location', '')
        config_files = service.get('config_files', [])

        has_python_config = any(
            file.endswith(('.py', '.toml', 'requirements.txt', 'Pipfile'))
            for file in config_files
        )

        if not has_python_config:
            issues.append("Python service missing configuration files")

        # Validate dependencies format
        if 'dependencies' in metadata:
            deps = metadata['dependencies']
            if not isinstance(deps, list):
                issues.append("Python dependencies must be a list")

        return issues

    def _validate_docker_service(self, service: Dict[str, Any]) -> List[str]:
        """Validate Docker service specific requirements."""
        issues = []
        metadata = service.get('metadata', {})

        # Check for exposed ports
        if 'exposed_ports' in metadata:
            ports = metadata['exposed_ports']
            if not isinstance(ports, list):
                issues.append("Docker exposed_ports must be a list")
            else:
                for port in ports:
                    if not self._validate_port(str(port).split('/')[0]):
                        issues.append(f"Invalid port number: {port}")

        # Check for Docker-specific files
        config_files = service.get('config_files', [])
        has_docker_config = any(
            'dockerfile' in file.lower() or 'docker-compose' in file.lower()
            for file in config_files
        )

        if not has_docker_config:
            issues.append("Docker service missing Dockerfile or docker-compose file")

        return issues

    def _validate_mcp_service(self, service: Dict[str, Any]) -> List[str]:
        """Validate MCP service specific requirements."""
        issues = []
        metadata = service.get('metadata', {})

        # Validate protocol
        protocol = metadata.get('protocol', service.get('protocol'))
        if protocol and not re.match(self.validation_patterns['protocol'], protocol):
            issues.append(f"Invalid MCP protocol: {protocol}")

        # Validate command
        command = metadata.get('command', service.get('command'))
        if not command:
            issues.append("MCP service missing command")

        # Validate args
        args = metadata.get('args', service.get('args', []))
        if not isinstance(args, list):
            issues.append("MCP args must be a list")

        return issues

    def _validate_web_service(self, service: Dict[str, Any]) -> List[str]:
        """Validate web service (FastAPI, Flask, Express) requirements."""
        issues = []

        # Validate port if present
        port = service.get('port') or service.get('metadata', {}).get('port')
        if port and not self._validate_port(str(port)):
            issues.append(f"Invalid port number: {port}")

        # Validate host if present
        host = service.get('host') or service.get('metadata', {}).get('host')
        if host and not re.match(self.validation_patterns['host'], host):
            issues.append(f"Invalid host format: {host}")

        return issues

    def _validate_configuration(self, service: Dict[str, Any]) -> tuple:
        """Validate service configuration."""
        issues = []
        warnings = []

        # Validate name format
        name = service.get('name', '')
        if name and not re.match(self.validation_patterns['name'], name):
            issues.append(f"Invalid service name format: {name}")

        # Validate version format if present
        version = service.get('version') or service.get('metadata', {}).get('version')
        if version and not re.match(self.validation_patterns['version'], str(version)):
            warnings.append(f"Non-standard version format: {version}")

        # Check for required configuration files
        config_files = service.get('config_files', [])
        if not config_files:
            warnings.append("No configuration files detected")

        # Validate location exists
        location = service.get('location', '')
        if location:
            import os
            if not os.path.exists(location):
                issues.append(f"Service location does not exist: {location}")

        return issues, warnings

    def _validate_security(self, service: Dict[str, Any]) -> List[str]:
        """Perform security validation checks."""
        warnings = []

        # Check for potentially sensitive information in metadata
        metadata = service.get('metadata', {})

        def check_sensitive_data(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(sensitive in key.lower() for sensitive in self.security_checks):
                        warnings.append(f"Potentially sensitive configuration found: {current_path}")
                    check_sensitive_data(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    check_sensitive_data(item, f"{path}[{i}]")
            elif isinstance(obj, str):
                if any(sensitive in obj.lower() for sensitive in self.security_checks):
                    warnings.append(f"Potentially sensitive value found in: {path}")

        check_sensitive_data(metadata)

        # Check for insecure configurations
        if service.get('host') == '0.0.0.0':
            warnings.append("Service bound to all interfaces (0.0.0.0) - consider security implications")

        return warnings

    def _validate_dependencies(self, service: Dict[str, Any]) -> List[str]:
        """Validate service dependencies."""
        issues = []

        dependencies = service.get('dependencies', [])
        if not isinstance(dependencies, list):
            issues.append("Dependencies must be a list")
            return issues

        # Check for circular dependencies (basic check)
        service_id = service.get('id', '')
        if service_id in dependencies:
            issues.append("Service cannot depend on itself")

        # Validate dependency format
        for dep in dependencies:
            if not isinstance(dep, str):
                issues.append(f"Invalid dependency format: {dep}")

        return issues

    async def _perform_health_check(self, service: Dict[str, Any]) -> HealthResult:
        """Perform health check on the service."""
        probe_config = {
            'timeout': self.health_check_timeout,
            'retries': 1,
            'retry_delay': 1.0
        }

        probe = HealthProbeFactory.create_probe(service, probe_config)
        return await probe.check_health(service)

    def _validate_port(self, port_str: str) -> bool:
        """Validate port number format and range."""
        try:
            port = int(port_str)
            return 1 <= port <= 65535
        except (ValueError, TypeError):
            return False

    def validate_service_batch(self, services: List[Dict[str, Any]]) -> List[ValidationResult]:
        """
        Validate multiple services in batch.

        Args:
            services: List of service dictionaries

        Returns:
            List of ValidationResult objects
        """
        async def validate_all():
            tasks = [self.validate_service(service) for service in services]
            return await asyncio.gather(*tasks, return_exceptions=True)

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        results = loop.run_until_complete(validate_all())

        # Handle exceptions in results
        validated_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                service_id = services[i].get('id', f'service_{i}')
                validated_results.append(ValidationResult(
                    is_valid=False,
                    service_id=service_id,
                    validation_type='error',
                    issues=[f"Validation error: {str(result)}"],
                    warnings=[]
                ))
            else:
                validated_results.append(result)

        return validated_results

    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """
        Generate a summary of validation results.

        Args:
            results: List of ValidationResult objects

        Returns:
            Summary dictionary with statistics
        """
        total = len(results)
        valid = sum(1 for r in results if r.is_valid)
        invalid = total - valid

        total_issues = sum(len(r.issues) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        health_checks = [r for r in results if r.health_result is not None]
        healthy_services = sum(1 for r in health_checks if r.health_result.status == 'healthy')

        return {
            'total_services': total,
            'valid_services': valid,
            'invalid_services': invalid,
            'validation_rate': round(valid / total * 100, 2) if total > 0 else 0,
            'total_issues': total_issues,
            'total_warnings': total_warnings,
            'health_checks_performed': len(health_checks),
            'healthy_services': healthy_services,
            'health_check_rate': round(healthy_services / len(health_checks) * 100, 2) if health_checks else 0,
            'summary_generated_at': datetime.now().isoformat()
        }
