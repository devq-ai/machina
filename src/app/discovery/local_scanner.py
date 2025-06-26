"""
Local Service Scanner Module

This module provides comprehensive scanning capabilities for discovering services
in local directories by analyzing configuration files, service definitions,
and executable components.
"""

import os
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
import yaml
import toml
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ServiceInfo:
    """Data class representing discovered service information"""
    id: str
    name: str
    type: str
    location: str
    metadata: Dict[str, Any]
    config_files: List[str]
    discovered_at: str
    health_endpoint: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None


class LocalServiceScanner:
    """
    Scanner for discovering services in local directories by analyzing
    configuration files and service definitions.
    """

    def __init__(self, base_directories: Optional[List[str]] = None, max_depth: int = 5):
        """
        Initialize the LocalServiceScanner.

        Args:
            base_directories: List of directories to scan
            max_depth: Maximum directory traversal depth
        """
        self.base_directories = base_directories or [
            '/opt/services',
            './services',
            './mcp/mcp-servers',
            '/usr/local/services',
            '~/.local/services'
        ]
        self.max_depth = max_depth

        # Service detection patterns
        self.service_patterns = {
            'node': {
                'files': ['package.json'],
                'indicators': ['scripts', 'main', 'bin'],
                'health_paths': ['/health', '/status', '/ping']
            },
            'python': {
                'files': ['setup.py', 'pyproject.toml', 'requirements.txt', 'Pipfile'],
                'indicators': ['__main__.py', 'main.py', 'app.py', 'server.py'],
                'health_paths': ['/health', '/healthz', '/status']
            },
            'docker': {
                'files': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
                'indicators': ['EXPOSE', 'CMD', 'ENTRYPOINT'],
                'health_paths': ['/health', '/healthcheck']
            },
            'systemd': {
                'files': ['.service'],
                'indicators': ['ExecStart', 'Type=forking'],
                'health_paths': []
            },
            'mcp': {
                'files': ['service.json', 'mcp.json', 'mcp-config.json'],
                'indicators': ['protocol', 'command', 'args'],
                'health_paths': []
            },
            'fastapi': {
                'files': ['main.py', 'app.py'],
                'indicators': ['FastAPI', 'uvicorn', '@app.'],
                'health_paths': ['/health', '/docs', '/openapi.json']
            },
            'flask': {
                'files': ['app.py', 'run.py', 'wsgi.py'],
                'indicators': ['Flask', 'app.run', '@app.route'],
                'health_paths': ['/health', '/ping']
            },
            'express': {
                'files': ['server.js', 'app.js', 'index.js'],
                'indicators': ['express', 'app.listen', 'app.get'],
                'health_paths': ['/health', '/status']
            }
        }

        # Expand home directory paths
        self.base_directories = [
            os.path.expanduser(path) for path in self.base_directories
        ]

    def scan(self) -> List[ServiceInfo]:
        """
        Scan all configured directories for services.

        Returns:
            List of discovered ServiceInfo objects
        """
        discovered_services = []
        scan_stats = {
            'directories_scanned': 0,
            'files_analyzed': 0,
            'services_found': 0,
            'errors': 0
        }

        logger.info(f"Starting service discovery scan across {len(self.base_directories)} directories")

        for directory in self.base_directories:
            if not os.path.exists(directory):
                logger.debug(f"Directory does not exist: {directory}")
                continue

            logger.info(f"Scanning directory: {directory}")
            try:
                services = self._scan_directory(directory, depth=0, stats=scan_stats)
                discovered_services.extend(services)
                scan_stats['services_found'] += len(services)
            except Exception as e:
                logger.error(f"Error scanning directory {directory}: {e}")
                scan_stats['errors'] += 1

        logger.info(f"Scan completed. Stats: {scan_stats}")
        return discovered_services

    def _scan_directory(self, directory: str, depth: int = 0, stats: Dict = None) -> List[ServiceInfo]:
        """
        Recursively scan a directory for services.

        Args:
            directory: Directory path to scan
            depth: Current recursion depth
            stats: Statistics tracking dictionary

        Returns:
            List of discovered services in this directory
        """
        if depth > self.max_depth:
            logger.debug(f"Maximum depth reached, skipping: {directory}")
            return []

        if stats:
            stats['directories_scanned'] += 1

        services = []

        try:
            items = os.listdir(directory)
        except (PermissionError, FileNotFoundError, OSError) as e:
            logger.debug(f"Cannot access directory {directory}: {e}")
            return []

        # Check if current directory contains a service
        service_info = self._identify_service_in_directory(directory, items, stats)
        if service_info:
            services.append(service_info)
            logger.info(f"Discovered service: {service_info.name} at {service_info.location}")

        # Recursively scan subdirectories
        for item in items:
            if item.startswith('.'):  # Skip hidden directories
                continue

            full_path = os.path.join(directory, item)
            if os.path.isdir(full_path):
                sub_services = self._scan_directory(full_path, depth + 1, stats)
                services.extend(sub_services)

        return services

    def _identify_service_in_directory(self, directory: str, items: List[str], stats: Dict = None) -> Optional[ServiceInfo]:
        """
        Analyze a directory to determine if it contains a service.

        Args:
            directory: Directory path to analyze
            items: List of items in the directory
            stats: Statistics tracking dictionary

        Returns:
            ServiceInfo if a service is detected, None otherwise
        """
        detected_types = []
        config_files = []
        metadata = {}

        # Check for service patterns
        for service_type, patterns in self.service_patterns.items():
            type_score = 0
            type_files = []

            # Check for configuration files
            for pattern_file in patterns['files']:
                matching_files = [item for item in items if self._matches_pattern(item, pattern_file)]
                if matching_files:
                    type_score += 2
                    type_files.extend([os.path.join(directory, f) for f in matching_files])

            # Check file contents for indicators
            if type_files:
                content_score = self._analyze_file_contents(type_files, patterns['indicators'], stats)
                type_score += content_score

            if type_score > 0:
                detected_types.append((service_type, type_score, type_files))

        if not detected_types:
            return None

        # Select the service type with highest confidence score
        detected_types.sort(key=lambda x: x[1], reverse=True)
        primary_type, score, primary_files = detected_types[0]

        # For JavaScript-based services, include package.json if it exists
        all_config_files = list(primary_files)
        if primary_type in ['express', 'node'] and 'package.json' in items:
            package_json_path = os.path.join(directory, 'package.json')
            if package_json_path not in all_config_files:
                all_config_files.append(package_json_path)

        # For Python-based services, include Python config files if they exist
        if primary_type in ['fastapi', 'flask', 'python']:
            python_config_files = ['pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile']
            for config_file in python_config_files:
                if config_file in items:
                    config_path = os.path.join(directory, config_file)
                    if config_path not in all_config_files:
                        all_config_files.append(config_path)

        # Build final config files list
        config_files = all_config_files

        # Extract service metadata
        try:
            metadata = self._extract_service_metadata(primary_type, all_config_files, directory)
        except Exception as e:
            logger.warning(f"Error extracting metadata for {directory}: {e}")
            metadata = {}

        # Generate service info
        service_name = metadata.get('name') or os.path.basename(directory)
        service_id = f"{primary_type}_{service_name}_{abs(hash(directory)) % 10000}"

        # Attempt to determine health endpoint
        health_endpoint = self._determine_health_endpoint(metadata, primary_type)
        host, port = self._extract_host_port(metadata, primary_type)

        return ServiceInfo(
            id=service_id,
            name=service_name,
            type=primary_type,
            location=directory,
            metadata=metadata,
            config_files=config_files,
            discovered_at=datetime.now().isoformat(),
            health_endpoint=health_endpoint,
            host=host,
            port=port
        )

    def _matches_pattern(self, filename: str, pattern: str) -> bool:
        """Check if a filename matches a service pattern."""
        if pattern.startswith('.') and pattern.endswith('.'):
            # Extension pattern like .service
            return filename.endswith(pattern)
        elif '*' in pattern:
            # Wildcard pattern
            import fnmatch
            return fnmatch.fnmatch(filename, pattern)
        else:
            # Exact match
            return filename == pattern

    def _analyze_file_contents(self, files: List[str], indicators: List[str], stats: Dict = None) -> int:
        """
        Analyze file contents for service indicators.

        Args:
            files: List of file paths to analyze
            indicators: List of text indicators to search for
            stats: Statistics tracking dictionary

        Returns:
            Confidence score based on found indicators
        """
        score = 0

        for file_path in files:
            if stats:
                stats['files_analyzed'] += 1

            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for indicator in indicators:
                    if indicator.lower() in content.lower():
                        score += 1
                        logger.debug(f"Found indicator '{indicator}' in {file_path}")

            except (IOError, UnicodeDecodeError) as e:
                logger.debug(f"Cannot read file {file_path}: {e}")
                continue

        return score

    def _extract_service_metadata(self, service_type: str, config_files: List[str], directory: str) -> Dict[str, Any]:
        """
        Extract detailed metadata from service configuration files.

        Args:
            service_type: Type of service detected
            config_files: List of configuration file paths
            directory: Service directory path

        Returns:
            Dictionary containing extracted metadata
        """
        metadata = {
            'service_type': service_type,
            'directory': directory,
            'config_files': config_files
        }

        for config_file in config_files:
            filename = os.path.basename(config_file)

            try:
                if filename == 'package.json':
                    metadata.update(self._parse_package_json(config_file))
                elif filename in ['pyproject.toml']:
                    metadata.update(self._parse_pyproject_toml(config_file))
                elif filename == 'setup.py':
                    metadata.update(self._parse_setup_py(config_file))
                elif filename in ['docker-compose.yml', 'docker-compose.yaml']:
                    metadata.update(self._parse_docker_compose(config_file))
                elif filename == 'Dockerfile':
                    metadata.update(self._parse_dockerfile(config_file))
                elif filename.endswith('.service'):
                    metadata.update(self._parse_systemd_service(config_file))
                elif filename in ['service.json', 'mcp.json', 'mcp-config.json']:
                    metadata.update(self._parse_mcp_config(config_file))

            except Exception as e:
                logger.warning(f"Error parsing {config_file}: {e}")

        # Extract additional metadata from source code analysis
        source_metadata = self._analyze_source_code(config_files, service_type, directory)
        metadata.update(source_metadata)

        return metadata

    def _parse_package_json(self, file_path: str) -> Dict[str, Any]:
        """Parse Node.js package.json file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Extract framework indicators from dependencies
        dependencies = data.get('dependencies', {})
        dev_dependencies = data.get('devDependencies', {})
        all_deps = list(dependencies.keys()) + list(dev_dependencies.keys())

        framework_indicators = []
        if 'express' in all_deps:
            framework_indicators.append('express')
        if 'fastify' in all_deps:
            framework_indicators.append('fastify')
        if 'koa' in all_deps:
            framework_indicators.append('koa')
        if 'next' in all_deps or 'next.js' in all_deps:
            framework_indicators.append('next.js')
        if 'typescript' in all_deps:
            framework_indicators.append('typescript')

        # Combine regular and dev dependencies
        all_deps = list(dependencies.keys()) + list(dev_dependencies.keys())

        result = {
            'name': data.get('name'),
            'version': data.get('version'),
            'description': data.get('description'),
            'main': data.get('main'),
            'scripts': data.get('scripts', {}),
            'dependencies': all_deps,
            'engines': data.get('engines', {}),
            'keywords': data.get('keywords', []),
            'framework_indicators': framework_indicators,
            'license': data.get('license')
        }

        # Add author information if available
        author = data.get('author')
        if author:
            if isinstance(author, str):
                result['author'] = author
            elif isinstance(author, dict):
                result['author'] = author.get('name', str(author))

        return result

    def _parse_pyproject_toml(self, file_path: str) -> Dict[str, Any]:
        """Parse Python pyproject.toml file."""
        with open(file_path, 'r') as f:
            data = toml.load(f)

        project = data.get('project', {})
        dependencies = project.get('dependencies', [])

        # Extract framework indicators
        framework_indicators = []
        dep_str = ' '.join(dependencies)
        if 'fastapi' in dep_str.lower():
            framework_indicators.append('fastapi')
        if 'flask' in dep_str.lower():
            framework_indicators.append('flask')
        if 'django' in dep_str.lower():
            framework_indicators.append('django')
        if 'uvicorn' in dep_str.lower():
            framework_indicators.append('uvicorn')

        result = {
            'name': project.get('name'),
            'version': project.get('version'),
            'description': project.get('description'),
            'dependencies': dependencies,
            'keywords': project.get('keywords', []),
            'entry_points': data.get('project', {}).get('entry-points', {}),
            'framework_indicators': framework_indicators
        }

        # Add author information
        authors = project.get('authors', [])
        if authors and len(authors) > 0:
            result['author'] = authors[0].get('name', str(authors[0]))

        return result

    def _parse_setup_py(self, file_path: str) -> Dict[str, Any]:
        """Parse Python setup.py file (basic extraction)."""
        metadata = {}
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Simple regex-based extraction (not executing the file)
            import re

            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match:
                metadata['name'] = name_match.group(1)

            version_match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
            if version_match:
                metadata['version'] = version_match.group(1)

        except Exception as e:
            logger.debug(f"Error parsing setup.py: {e}")

        return metadata

    def _parse_docker_compose(self, file_path: str) -> Dict[str, Any]:
        """Parse Docker Compose file."""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        services = data.get('services', {})
        metadata = {
            'docker_services': list(services.keys()),
            'compose_version': data.get('version'),
            'service_count': len(services),
            'ports': []
        }

        # Extract port mappings
        for service_name, service_config in services.items():
            ports = service_config.get('ports', [])
            metadata['ports'].extend(ports)

        return metadata

    def _parse_dockerfile(self, file_path: str) -> Dict[str, Any]:
        """Parse Dockerfile for service information."""
        metadata = {'exposed_ports': [], 'commands': []}

        try:
            with open(file_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('EXPOSE'):
                        ports = line.split()[1:]
                        metadata['exposed_ports'].extend(ports)
                    elif line.startswith(('CMD', 'ENTRYPOINT')):
                        metadata['commands'].append(line)
        except Exception as e:
            logger.debug(f"Error parsing Dockerfile: {e}")

        return metadata

    def _parse_systemd_service(self, file_path: str) -> Dict[str, Any]:
        """Parse systemd service file."""
        metadata = {}
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            # Extract key systemd directives
            import re
            exec_start = re.search(r'ExecStart=(.+)', content)
            if exec_start:
                metadata['exec_start'] = exec_start.group(1).strip()

            service_type = re.search(r'Type=(.+)', content)
            if service_type:
                metadata['service_type'] = service_type.group(1).strip()

        except Exception as e:
            logger.debug(f"Error parsing systemd service: {e}")

        return metadata

    def _parse_mcp_config(self, file_path: str) -> Dict[str, Any]:
        """Parse MCP service configuration file."""
        with open(file_path, 'r') as f:
            data = json.load(f)

        return {
            'name': data.get('name'),
            'protocol': data.get('protocol', 'stdio'),
            'command': data.get('command'),
            'args': data.get('args', []),
            'env': data.get('env', {}),
            'description': data.get('description', ''),
            'tags': data.get('tags', []),
            'mcp_version': data.get('version', '1.0')
        }

    def _determine_health_endpoint(self, metadata: Dict[str, Any], service_type: str) -> Optional[str]:
        """Determine likely health check endpoint for the service."""
        # Check if health endpoint is explicitly configured
        if 'health_endpoint' in metadata:
            return metadata['health_endpoint']

        # Extract host and port
        host = metadata.get('host', 'localhost')
        port = metadata.get('port')

        if not port:
            # Use default port for service type
            default_ports = {
                'fastapi': 8000,
                'flask': 5000,
                'express': 3000,
                'node': 3000,
                'python': 8000
            }
            port = default_ports.get(service_type, 8000)

        # Check for detected health paths from source code analysis first
        detected_health_paths = metadata.get('detected_health_paths', [])
        if detected_health_paths:
            return f"http://{host}:{port}{detected_health_paths[0]}"

        # Fall back to default health paths for service type
        health_paths = self.service_patterns.get(service_type, {}).get('health_paths', [])
        if health_paths:
            return f"http://{host}:{port}{health_paths[0]}"

        return None

    def _extract_host_port(self, metadata: Dict[str, Any], service_type: str) -> tuple:
        """Extract host and port information from service metadata."""
        host = metadata.get('host', 'localhost')
        port = None

        # Try various ways to determine port
        if 'port' in metadata:
            port = int(metadata['port'])
        elif 'exposed_ports' in metadata and metadata['exposed_ports']:
            try:
                port = int(metadata['exposed_ports'][0].split('/')[0])
            except (ValueError, IndexError):
                pass
        elif 'ports' in metadata and metadata['ports']:
            try:
                port_mapping = metadata['ports'][0]
                if ':' in str(port_mapping):
                    port = int(str(port_mapping).split(':')[0])
                else:
                    port = int(port_mapping)
            except (ValueError, IndexError):
                pass

        # Default ports by service type
        if port is None:
            default_ports = {
                'fastapi': 8000,
                'flask': 5000,
                'express': 3000,
                'node': 3000,
                'python': 8000
            }
            port = default_ports.get(service_type)

        return host, port

    def _analyze_source_code(self, config_files: List[str], service_type: str, directory: str) -> Dict[str, Any]:
        """
        Analyze source code files to extract additional metadata like ports and health endpoints.

        Args:
            config_files: List of configuration file paths
            service_type: Type of service detected
            directory: Service directory path

        Returns:
            Dictionary containing extracted metadata from source analysis
        """
        metadata = {}

        # Find source files to analyze
        source_files = []
        common_source_patterns = {
            'python': ['*.py'],
            'fastapi': ['main.py', 'app.py', '*.py'],
            'flask': ['app.py', 'run.py', 'wsgi.py', '*.py'],
            'node': ['*.js', '*.ts'],
            'express': ['server.js', 'app.js', 'index.js', '*.js']
        }

        patterns = common_source_patterns.get(service_type, ['*.*'])

        for pattern in patterns:
            if '*' in pattern:
                # Use glob for wildcard patterns
                import glob
                files = glob.glob(os.path.join(directory, pattern))
                source_files.extend(files)
            else:
                # Direct file check
                file_path = os.path.join(directory, pattern)
                if os.path.exists(file_path):
                    source_files.append(file_path)

        # Analyze source files
        detected_port = None
        detected_health_paths = []
        framework_indicators = metadata.get('framework_indicators', [])

        for source_file in source_files[:10]:  # Limit to first 10 files for performance
            try:
                with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Port detection patterns
                port_patterns = [
                    r'port\s*[=:]\s*(\d+)',
                    r'PORT\s*[=:]\s*(\d+)',
                    r'\.listen\s*\(\s*(\d+)',
                    r'uvicorn\.run\s*\([^)]*port\s*=\s*(\d+)',
                    r'app\.run\s*\([^)]*port\s*=\s*(\d+)',
                    r'server\.listen\s*\(\s*(\d+)'
                ]

                for pattern in port_patterns:
                    import re
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    if matches:
                        try:
                            detected_port = int(matches[0])
                            break
                        except ValueError:
                            continue

                # Health endpoint detection
                health_patterns = [
                    r'@app\.route\s*\(\s*["\']([^"\']*health[^"\']*)["\']',
                    r'@app\.get\s*\(\s*["\']([^"\']*health[^"\']*)["\']',
                    r'app\.get\s*\(\s*["\']([^"\']*health[^"\']*)["\']',
                    r'router\.get\s*\(\s*["\']([^"\']*health[^"\']*)["\']',
                    r'["\']([^"\']*(?:health|status|ping|healthz)[^"\']*)["\']'
                ]

                for pattern in health_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        if match.startswith('/') and len(match) > 1:
                            detected_health_paths.append(match)

                # Framework detection from imports and usage
                if 'fastapi' in content.lower() or 'FastAPI' in content:
                    if 'fastapi' not in framework_indicators:
                        framework_indicators.append('fastapi')
                if 'flask' in content.lower() or 'Flask' in content:
                    if 'flask' not in framework_indicators:
                        framework_indicators.append('flask')
                if 'express' in content.lower():
                    if 'express' not in framework_indicators:
                        framework_indicators.append('express')

            except Exception as e:
                logger.debug(f"Error analyzing source file {source_file}: {e}")
                continue

        # Update metadata with findings
        if detected_port:
            metadata['port'] = detected_port

        if detected_health_paths:
            metadata['detected_health_paths'] = list(set(detected_health_paths))

        if framework_indicators:
            metadata['framework_indicators'] = framework_indicators

        return metadata

    def scan_specific_directory(self, directory: str) -> List[ServiceInfo]:
        """
        Scan a specific directory for services.

        Args:
            directory: Directory path to scan

        Returns:
            List of discovered services
        """
        if not os.path.exists(directory):
            logger.warning(f"Directory does not exist: {directory}")
            return []

        logger.info(f"Scanning specific directory: {directory}")
        stats = {'directories_scanned': 0, 'files_analyzed': 0}

        return self._scan_directory(directory, depth=0, stats=stats)

    def get_scan_summary(self) -> Dict[str, Any]:
        """
        Get a summary of scanning capabilities and configuration.

        Returns:
            Dictionary containing scanner configuration and capabilities
        """
        return {
            'base_directories': self.base_directories,
            'max_depth': self.max_depth,
            'supported_service_types': list(self.service_patterns.keys()),
            'service_patterns': {
                stype: {
                    'files': patterns['files'],
                    'health_paths': patterns['health_paths']
                }
                for stype, patterns in self.service_patterns.items()
            }
        }
