"""
Service Metadata Extractor Module

This module provides comprehensive metadata extraction capabilities for discovered services,
analyzing configuration files, code patterns, and runtime information to build rich service profiles.
"""

import logging
import os
import json
import re
import ast
import toml
import yaml
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import subprocess
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class ExtractedMetadata:
    """Data class representing extracted service metadata"""
    service_id: str
    metadata_type: str
    data: Dict[str, Any]
    confidence: float  # 0.0 to 1.0
    extraction_method: str
    extracted_at: str
    file_sources: List[str]

    def __post_init__(self):
        if not hasattr(self, 'extracted_at') or not self.extracted_at:
            self.extracted_at = datetime.now().isoformat()


class ServiceMetadataExtractor:
    """
    Comprehensive metadata extractor that analyzes service configurations,
    code patterns, and runtime information to build rich service profiles.
    """

    def __init__(self, deep_analysis: bool = True, include_dependencies: bool = True,
                 analyze_security: bool = True, extract_api_specs: bool = True):
        """
        Initialize the metadata extractor.

        Args:
            deep_analysis: Whether to perform deep code analysis
            include_dependencies: Whether to extract dependency information
            analyze_security: Whether to analyze security configurations
            extract_api_specs: Whether to extract API specifications
        """
        self.deep_analysis = deep_analysis
        self.include_dependencies = include_dependencies
        self.analyze_security = analyze_security
        self.extract_api_specs = extract_api_specs

        # File patterns for different service types
        self.config_patterns = {
            'node': {
                'primary': ['package.json', 'package-lock.json'],
                'secondary': ['yarn.lock', '.nvmrc', 'tsconfig.json', 'jest.config.js'],
                'runtime': ['server.js', 'app.js', 'index.js', 'main.js']
            },
            'python': {
                'primary': ['requirements.txt', 'setup.py', 'pyproject.toml', 'Pipfile'],
                'secondary': ['setup.cfg', 'tox.ini', 'pytest.ini', '.python-version'],
                'runtime': ['main.py', 'app.py', 'server.py', 'run.py', '__main__.py']
            },
            'docker': {
                'primary': ['Dockerfile', 'docker-compose.yml', 'docker-compose.yaml'],
                'secondary': ['.dockerignore', 'docker-compose.override.yml'],
                'runtime': []
            },
            'go': {
                'primary': ['go.mod', 'go.sum'],
                'secondary': ['Makefile', 'go.work'],
                'runtime': ['main.go', 'cmd/main.go']
            },
            'java': {
                'primary': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
                'secondary': ['gradle.properties', 'settings.gradle'],
                'runtime': ['Application.java', 'Main.java']
            },
            'rust': {
                'primary': ['Cargo.toml', 'Cargo.lock'],
                'secondary': ['rust-toolchain.toml'],
                'runtime': ['main.rs', 'lib.rs']
            }
        }

        # Security-related patterns to detect
        self.security_patterns = {
            'secrets': [
                r'password\s*=\s*["\'][^"\']+["\']',
                r'api_key\s*=\s*["\'][^"\']+["\']',
                r'secret\s*=\s*["\'][^"\']+["\']',
                r'token\s*=\s*["\'][^"\']+["\']',
                r'private_key\s*=\s*["\'][^"\']+["\']'
            ],
            'vulnerabilities': [
                r'eval\s*\(',
                r'exec\s*\(',
                r'shell_exec\s*\(',
                r'system\s*\(',
                r'subprocess\.call\s*\('
            ],
            'insecure_protocols': [
                r'http://',
                r'ftp://',
                r'telnet://'
            ]
        }

        # API documentation patterns
        self.api_patterns = {
            'openapi': ['openapi.json', 'openapi.yaml', 'swagger.json', 'swagger.yaml'],
            'fastapi': ['docs', 'redoc', 'openapi.json'],
            'flask': ['apidoc', 'swagger'],
            'express': ['api-docs', 'swagger']
        }

    def extract_metadata(self, service: Dict[str, Any]) -> List[ExtractedMetadata]:
        """
        Extract comprehensive metadata for a service.

        Args:
            service: Service information dictionary

        Returns:
            List of ExtractedMetadata objects
        """
        service_id = service.get('id', 'unknown')
        service_type = service.get('type', 'unknown')
        location = service.get('location', '')

        metadata_results = []

        logger.info(f"Extracting metadata for service: {service_id} (type: {service_type})")

        try:
            # 1. Basic service information
            basic_metadata = self._extract_basic_metadata(service)
            if basic_metadata:
                metadata_results.append(basic_metadata)

            # 2. Configuration file analysis
            config_metadata = self._extract_configuration_metadata(service, location)
            metadata_results.extend(config_metadata)

            # 3. Dependency analysis
            if self.include_dependencies:
                dependency_metadata = self._extract_dependency_metadata(service, location)
                if dependency_metadata:
                    metadata_results.append(dependency_metadata)

            # 4. Code analysis
            if self.deep_analysis:
                code_metadata = self._extract_code_metadata(service, location)
                metadata_results.extend(code_metadata)

            # 5. Security analysis
            if self.analyze_security:
                security_metadata = self._extract_security_metadata(service, location)
                if security_metadata:
                    metadata_results.append(security_metadata)

            # 6. API specification extraction
            if self.extract_api_specs:
                api_metadata = self._extract_api_metadata(service, location)
                if api_metadata:
                    metadata_results.append(api_metadata)

            # 7. Runtime metadata
            runtime_metadata = self._extract_runtime_metadata(service)
            if runtime_metadata:
                metadata_results.append(runtime_metadata)

            # 8. Environment analysis
            env_metadata = self._extract_environment_metadata(service, location)
            if env_metadata:
                metadata_results.append(env_metadata)

        except Exception as e:
            logger.error(f"Error extracting metadata for {service_id}: {e}")

        logger.info(f"Extracted {len(metadata_results)} metadata entries for {service_id}")
        return metadata_results

    def _extract_basic_metadata(self, service: Dict[str, Any]) -> Optional[ExtractedMetadata]:
        """Extract basic service metadata"""
        try:
            basic_data = {
                'service_name': service.get('name'),
                'service_type': service.get('type'),
                'service_location': service.get('location'),
                'discovered_at': service.get('discovered_at'),
                'config_files': service.get('config_files', []),
                'host': service.get('host'),
                'port': service.get('port'),
                'health_endpoint': service.get('health_endpoint')
            }

            # Calculate service fingerprint
            service_content = json.dumps(basic_data, sort_keys=True)
            fingerprint = hashlib.md5(service_content.encode()).hexdigest()
            basic_data['service_fingerprint'] = fingerprint

            return ExtractedMetadata(
                service_id=service.get('id', 'unknown'),
                metadata_type='basic',
                data=basic_data,
                confidence=1.0,
                extraction_method='direct',
                extracted_at=datetime.now().isoformat(),
                file_sources=[]
            )

        except Exception as e:
            logger.error(f"Error extracting basic metadata: {e}")
            return None

    def _extract_configuration_metadata(self, service: Dict[str, Any], location: str) -> List[ExtractedMetadata]:
        """Extract metadata from configuration files"""
        metadata_results = []
        service_type = service.get('type', 'unknown')

        if not location or not os.path.exists(location):
            return metadata_results

        try:
            # Get config patterns for service type
            patterns = self.config_patterns.get(service_type, {})
            all_patterns = patterns.get('primary', []) + patterns.get('secondary', [])

            for pattern in all_patterns:
                config_files = self._find_files_by_pattern(location, pattern)

                for config_file in config_files:
                    try:
                        metadata = self._extract_file_metadata(config_file, service_type)
                        if metadata:
                            metadata_results.append(ExtractedMetadata(
                                service_id=service.get('id', 'unknown'),
                                metadata_type='configuration',
                                data=metadata,
                                confidence=0.9,
                                extraction_method='file_analysis',
                                extracted_at=datetime.now().isoformat(),
                                file_sources=[config_file]
                            ))

                    except Exception as e:
                        logger.debug(f"Error extracting metadata from {config_file}: {e}")

        except Exception as e:
            logger.error(f"Error in configuration metadata extraction: {e}")

        return metadata_results

    def _extract_file_metadata(self, file_path: str, service_type: str) -> Optional[Dict[str, Any]]:
        """Extract metadata from a specific file"""
        try:
            filename = os.path.basename(file_path)

            # Route to appropriate parser based on file type
            if filename == 'package.json':
                return self._parse_package_json(file_path)
            elif filename in ['requirements.txt', 'Pipfile']:
                return self._parse_python_requirements(file_path)
            elif filename == 'pyproject.toml':
                return self._parse_pyproject_toml(file_path)
            elif filename == 'setup.py':
                return self._parse_setup_py(file_path)
            elif filename in ['docker-compose.yml', 'docker-compose.yaml']:
                return self._parse_docker_compose(file_path)
            elif filename == 'Dockerfile':
                return self._parse_dockerfile(file_path)
            elif filename in ['go.mod', 'go.sum']:
                return self._parse_go_module(file_path)
            elif filename in ['pom.xml', 'build.gradle']:
                return self._parse_java_build(file_path)
            elif filename in ['Cargo.toml', 'Cargo.lock']:
                return self._parse_rust_cargo(file_path)
            else:
                return self._parse_generic_config(file_path)

        except Exception as e:
            logger.debug(f"Error parsing file {file_path}: {e}")
            return None

    def _parse_package_json(self, file_path: str) -> Dict[str, Any]:
        """Parse Node.js package.json file"""
        with open(file_path, 'r') as f:
            data = json.load(f)

        metadata = {
            'name': data.get('name'),
            'version': data.get('version'),
            'description': data.get('description'),
            'main': data.get('main'),
            'scripts': data.get('scripts', {}),
            'dependencies': data.get('dependencies', {}),
            'devDependencies': data.get('devDependencies', {}),
            'engines': data.get('engines', {}),
            'keywords': data.get('keywords', []),
            'author': data.get('author'),
            'license': data.get('license'),
            'repository': data.get('repository'),
            'homepage': data.get('homepage'),
            'bugs': data.get('bugs')
        }

        # Extract Node.js specific information
        if 'scripts' in data:
            scripts = data['scripts']
            metadata['has_start_script'] = 'start' in scripts
            metadata['has_test_script'] = 'test' in scripts
            metadata['has_build_script'] = 'build' in scripts

        # Analyze dependencies
        all_deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
        metadata['dependency_count'] = len(all_deps)
        metadata['framework_indicators'] = self._detect_node_frameworks(all_deps)

        return metadata

    def _parse_python_requirements(self, file_path: str) -> Dict[str, Any]:
        """Parse Python requirements.txt or Pipfile"""
        metadata = {'dependencies': [], 'dependency_count': 0}

        try:
            filename = os.path.basename(file_path)

            if filename == 'Pipfile':
                # Parse Pipfile (TOML format)
                with open(file_path, 'r') as f:
                    pipfile_data = toml.load(f)

                dependencies = {
                    **pipfile_data.get('packages', {}),
                    **pipfile_data.get('dev-packages', {})
                }
                metadata['dependencies'] = list(dependencies.keys())
                metadata['python_version'] = pipfile_data.get('requires', {}).get('python_version')

            else:
                # Parse requirements.txt
                with open(file_path, 'r') as f:
                    lines = f.readlines()

                deps = []
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        # Extract package name (before version specifiers)
                        package = re.split(r'[<>=!]', line)[0].strip()
                        if package:
                            deps.append(package)

                metadata['dependencies'] = deps

            metadata['dependency_count'] = len(metadata['dependencies'])
            metadata['framework_indicators'] = self._detect_python_frameworks(metadata['dependencies'])

        except Exception as e:
            logger.debug(f"Error parsing Python requirements: {e}")

        return metadata

    def _parse_pyproject_toml(self, file_path: str) -> Dict[str, Any]:
        """Parse Python pyproject.toml file"""
        with open(file_path, 'r') as f:
            data = toml.load(f)

        project = data.get('project', {})
        build_system = data.get('build-system', {})

        metadata = {
            'name': project.get('name'),
            'version': project.get('version'),
            'description': project.get('description'),
            'dependencies': project.get('dependencies', []),
            'optional_dependencies': project.get('optional-dependencies', {}),
            'keywords': project.get('keywords', []),
            'authors': project.get('authors', []),
            'maintainers': project.get('maintainers', []),
            'license': project.get('license'),
            'urls': project.get('urls', {}),
            'scripts': project.get('scripts', {}),
            'entry_points': project.get('entry-points', {}),
            'build_backend': build_system.get('build-backend'),
            'build_requires': build_system.get('requires', [])
        }

        # Extract Python version requirements
        if 'requires-python' in project:
            metadata['python_version_requirement'] = project['requires-python']

        # Analyze tool configurations
        tool_configs = data.get('tool', {})
        metadata['configured_tools'] = list(tool_configs.keys())

        return metadata

    def _parse_docker_compose(self, file_path: str) -> Dict[str, Any]:
        """Parse Docker Compose file"""
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)

        metadata = {
            'version': data.get('version'),
            'services': {},
            'networks': list(data.get('networks', {}).keys()),
            'volumes': list(data.get('volumes', {}).keys())
        }

        # Analyze services
        services = data.get('services', {})
        for service_name, service_config in services.items():
            service_metadata = {
                'image': service_config.get('image'),
                'build': service_config.get('build'),
                'ports': service_config.get('ports', []),
                'volumes': service_config.get('volumes', []),
                'environment': service_config.get('environment', []),
                'depends_on': service_config.get('depends_on', []),
                'networks': list(service_config.get('networks', {}).keys()),
                'restart': service_config.get('restart'),
                'healthcheck': service_config.get('healthcheck')
            }
            metadata['services'][service_name] = service_metadata

        metadata['service_count'] = len(services)

        return metadata

    def _parse_dockerfile(self, file_path: str) -> Dict[str, Any]:
        """Parse Dockerfile"""
        metadata = {
            'base_images': [],
            'exposed_ports': [],
            'volumes': [],
            'env_vars': {},
            'commands': [],
            'workdir': None,
            'user': None
        }

        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                if line.startswith('FROM'):
                    image = line.split()[1]
                    metadata['base_images'].append(image)

                elif line.startswith('EXPOSE'):
                    ports = line.split()[1:]
                    metadata['exposed_ports'].extend(ports)

                elif line.startswith('VOLUME'):
                    volumes = line.split()[1:]
                    metadata['volumes'].extend(volumes)

                elif line.startswith('ENV'):
                    env_parts = line.split(None, 2)[1:]
                    if len(env_parts) >= 2:
                        key, value = env_parts[0], env_parts[1]
                        metadata['env_vars'][key] = value

                elif line.startswith(('RUN', 'CMD', 'ENTRYPOINT')):
                    metadata['commands'].append(line)

                elif line.startswith('WORKDIR'):
                    metadata['workdir'] = line.split()[1]

                elif line.startswith('USER'):
                    metadata['user'] = line.split()[1]

        except Exception as e:
            logger.debug(f"Error parsing Dockerfile: {e}")

        return metadata

    def _detect_node_frameworks(self, dependencies: Dict[str, str]) -> List[str]:
        """Detect Node.js frameworks from dependencies"""
        frameworks = []

        framework_indicators = {
            'express': ['express'],
            'fastify': ['fastify'],
            'koa': ['koa'],
            'nest': ['@nestjs/core'],
            'next': ['next'],
            'react': ['react'],
            'vue': ['vue'],
            'angular': ['@angular/core'],
            'typescript': ['typescript'],
            'webpack': ['webpack'],
            'babel': ['@babel/core']
        }

        for framework, indicators in framework_indicators.items():
            if any(indicator in dependencies for indicator in indicators):
                frameworks.append(framework)

        return frameworks

    def _detect_python_frameworks(self, dependencies: List[str]) -> List[str]:
        """Detect Python frameworks from dependencies"""
        frameworks = []

        framework_indicators = {
            'django': ['django'],
            'flask': ['flask'],
            'fastapi': ['fastapi'],
            'tornado': ['tornado'],
            'pyramid': ['pyramid'],
            'bottle': ['bottle'],
            'cherrypy': ['cherrypy'],
            'aiohttp': ['aiohttp'],
            'starlette': ['starlette'],
            'quart': ['quart']
        }

        for framework, indicators in framework_indicators.items():
            if any(indicator.lower() in [dep.lower() for dep in dependencies] for indicator in indicators):
                frameworks.append(framework)

        return frameworks

    def _extract_dependency_metadata(self, service: Dict[str, Any], location: str) -> Optional[ExtractedMetadata]:
        """Extract dependency information and vulnerability analysis"""
        if not self.include_dependencies or not location:
            return None

        try:
            dependency_data = {
                'total_dependencies': 0,
                'direct_dependencies': 0,
                'dev_dependencies': 0,
                'outdated_dependencies': [],
                'vulnerable_dependencies': [],
                'license_issues': [],
                'dependency_tree_depth': 0
            }

            service_type = service.get('type', 'unknown')

            # Analyze based on service type
            if service_type == 'node':
                node_deps = self._analyze_node_dependencies(location)
                dependency_data.update(node_deps)

            elif service_type == 'python':
                python_deps = self._analyze_python_dependencies(location)
                dependency_data.update(python_deps)

            return ExtractedMetadata(
                service_id=service.get('id', 'unknown'),
                metadata_type='dependencies',
                data=dependency_data,
                confidence=0.8,
                extraction_method='dependency_analysis',
                extracted_at=datetime.now().isoformat(),
                file_sources=[]
            )

        except Exception as e:
            logger.error(f"Error extracting dependency metadata: {e}")
            return None

    def _extract_security_metadata(self, service: Dict[str, Any], location: str) -> Optional[ExtractedMetadata]:
        """Extract security-related metadata"""
        if not self.analyze_security or not location:
            return None

        try:
            security_data = {
                'potential_secrets': [],
                'vulnerability_patterns': [],
                'insecure_protocols': [],
                'security_headers': [],
                'authentication_methods': [],
                'encryption_usage': [],
                'input_validation': [],
                'security_score': 0.0
            }

            # Scan for security patterns in code files
            code_files = self._find_code_files(location)
            for code_file in code_files:
                file_security = self._analyze_file_security(code_file)
                self._merge_security_data(security_data, file_security)

            # Calculate security score
            security_data['security_score'] = self._calculate_security_score(security_data)

            return ExtractedMetadata(
                service_id=service.get('id', 'unknown'),
                metadata_type='security',
                data=security_data,
                confidence=0.7,
                extraction_method='security_analysis',
                extracted_at=datetime.now().isoformat(),
                file_sources=code_files
            )

        except Exception as e:
            logger.error(f"Error extracting security metadata: {e}")
            return None

    def _extract_api_metadata(self, service: Dict[str, Any], location: str) -> Optional[ExtractedMetadata]:
        """Extract API specification and documentation metadata"""
        if not self.extract_api_specs or not location:
            return None

        try:
            api_data = {
                'api_specifications': [],
                'endpoints': [],
                'documentation_urls': [],
                'api_versions': [],
                'authentication_schemes': [],
                'response_formats': [],
                'rate_limiting': {}
            }

            # Look for API specification files
            api_files = []
            for pattern_list in self.api_patterns.values():
                for pattern in pattern_list:
                    found_files = self._find_files_by_pattern(location, pattern)
                    api_files.extend(found_files)

            # Analyze each API file
            for api_file in api_files:
                api_spec = self._parse_api_specification(api_file)
                if api_spec:
                    api_data['api_specifications'].append(api_spec)

            # Extract endpoints from code
            if self.deep_analysis:
                code_endpoints = self._extract_endpoints_from_code(location, service.get('type'))
                api_data['endpoints'].extend(code_endpoints)

            return ExtractedMetadata(
                service_id=service.get('id', 'unknown'),
                metadata_type='api',
                data=api_data,
                confidence=0.8,
                extraction_method='api_analysis',
                extracted_at=datetime.now().isoformat(),
                file_sources=api_files
            )

        except Exception as e:
            logger.error(f"Error extracting API metadata: {e}")
            return None

    def _extract_runtime_metadata(self, service: Dict[str, Any]) -> Optional[ExtractedMetadata]:
        """Extract runtime and environment metadata"""
        try:
            runtime_data = {
                'container_info': {},
                'process_info': {},
                'resource_usage': {},
                'environment_variables': {},
                'network_interfaces': {},
                'mounted_volumes': [],
                'running_processes': []
            }

            # Extract container information if available
            if 'container_id' in service:
                container_info = self._get_container_runtime_info(service['container_id'])
                runtime_data['container_info'] = container_info

            # Extract environment variables from service metadata
            env_vars = service.get('environment', {})
            if env_vars:
                # Filter sensitive information
                filtered_env = self._filter_sensitive_env_vars(env_vars)
                runtime_data['environment_variables'] = filtered_env

            return ExtractedMetadata(
                service_id=service.get('id', 'unknown'),
                metadata_type='runtime',
                data=runtime_data,
                confidence=0.9,
                extraction_method='runtime_analysis',
                extracted_at=datetime.now().isoformat(),
                file_sources=[]
            )

        except Exception as e:
            logger.error(f"Error extracting runtime metadata: {e}")
            return None

    def _extract_environment_metadata(self, service: Dict[str, Any], location: str) -> Optional[ExtractedMetadata]:
        """Extract environment and configuration metadata"""
        try:
            env_data = {
                'config_files': [],
                'environment_configs': {},
                'secrets_management': [],
                'logging_configuration': {},
                'monitoring_setup': {},
                'deployment_configs': []
            }

            if location and os.path.exists(location):
                # Look for environment files
                env_files = [
                    '.env', '.env.local', '.env.development', '.env.production',
                    'config.json', 'config.yaml', 'config.yml',
                    'app.config', 'application.properties'
                ]

                for env_file in env_files:
                    env_path = os.path.join(location, env_file)
                    if os.path.exists(env_path):
                        env_config = self._parse_environment_file(env_path)
                        env_data['environment_configs'][env_file] = env_config
                        env_data['config_files'].append(env_path)

            return ExtractedMetadata(
                service_id=service.get('id', 'unknown'),
                metadata_type='environment',
                data=env_data,
                confidence=0.8,
                extraction_method='environment_analysis',
                extracted_at=datetime.now().isoformat(),
                file_sources=env_data['config_files']
            )

        except Exception as e:
            logger.error(f"Error extracting environment metadata: {e}")
            return None

    def _find_files_by_pattern(self, directory: str, pattern: str) -> List[str]:
        """Find files matching a pattern in directory"""
        found_files = []
        try:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if file == pattern or file.endswith(pattern):
                        found_files.append(os.path.join(root, file))
        except Exception as e:
            logger.debug(f"Error finding files by pattern {pattern}: {e}")

        return found_files

    def _find_code_files(self, directory: str) -> List[str]:
        """Find code files for security analysis"""
        code_extensions = ['.py', '.js', '.ts', '.java', '.go', '.rs', '.php', '.rb']
        code_files = []

        try:
            for root, dirs, files in os.walk(directory):
                # Skip common non-code directories
                dirs[:] = [d for d in dirs if d not in ['.git', 'node_modules', '__pycache__', '.pytest_cache']]

                for file in files:
                    if any(file.endswith(ext) for ext in code_extensions):
                        code_files.append(os.path.join(root, file))

        except Exception as e:
            logger.debug(f"Error finding code files: {e}")

        return code_files

    def _parse_generic_config(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Parse generic configuration file"""
        try:
            with open(file_path, 'r') as f:
                content = f.read()

            filename = os.path.basename(file_path)
            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext in ['.json']:
                return json.loads(content)
            elif file_ext in ['.yaml', '.yml']:
                return yaml.safe_load(content)
            elif file_ext in ['.toml']:
                return toml.loads(content)
            else:
                # Return basic file information
                return {
                    'filename': filename,
                    'size': len(content),
                    'lines': len(content.splitlines()),
                    'encoding': 'utf-8'  # Assumed
                }

        except Exception as e:
            logger.debug(f"Error parsing generic config {file_path}: {e}")
            return None

    def get_extraction_summary(self, results: List[ExtractedMetadata]) -> Dict[str, Any]:
        """Generate summary of metadata extraction results"""
        summary = {
            'total_extractions': len(results),
            'metadata_types': {},
            'confidence_average': 0.0,
            'file_sources_count': 0,
            'extraction_methods': set(),
            'services_analyzed': set()
        }

        if not results:
            return summary

        # Analyze results
        confidence_sum = 0.0
        all_files = set()

        for result in results:
            # Count by metadata type
            metadata_type = result.metadata_type
            if metadata_type not in summary['metadata_types']:
                summary['metadata_types'][metadata_type] = 0
            summary['metadata_types'][metadata_type] += 1

            # Track confidence
            confidence_sum += result.confidence

            # Track files
            all_files.update(result.file_sources)

            # Track methods and services
            summary['extraction_methods'].add(result.extraction_method)
            summary['services_analyzed'].add(result.service_id)

        summary['confidence_average'] = confidence_sum / len(results)
        summary['file_sources_count'] = len(all_files)
        summary['extraction_methods'] = list(summary['extraction_methods'])
        summary['services_analyzed'] = list(summary['services_analyzed'])

        return summary
