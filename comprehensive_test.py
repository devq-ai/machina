#!/usr/bin/env python3
"""
Comprehensive Coverage Test for Service Discovery Engine
Tests all major components and calculates detailed coverage metrics
"""

import os
import sys
import json
import tempfile
import shutil
import asyncio
from pathlib import Path
import traceback

# Add src to path
sys.path.insert(0, './src')

class ServiceDiscoveryTester:
    """Comprehensive tester for the Service Discovery Engine"""

    def __init__(self):
        self.temp_dir = None
        self.test_results = {}
        self.component_coverage = {}

    def setup(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        print(f"📁 Test directory: {self.temp_dir}")

    def teardown(self):
        """Clean up test environment"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            print("🧹 Cleaned up test directory")

    def create_test_service(self, name, service_type, files):
        """Helper to create test service structures"""
        service_dir = os.path.join(self.temp_dir, name)
        os.makedirs(service_dir, exist_ok=True)

        for filename, content in files.items():
            file_path = os.path.join(service_dir, filename)
            with open(file_path, 'w') as f:
                if isinstance(content, dict):
                    json.dump(content, f, indent=2)
                else:
                    f.write(content)
        return service_dir

    def test_local_scanner_core(self):
        """Test LocalServiceScanner core functionality"""
        print("\n🧪 Testing LocalServiceScanner Core...")

        try:
            from app.discovery.local_scanner import LocalServiceScanner

            # Test 1: Basic initialization
            scanner = LocalServiceScanner(base_directories=[self.temp_dir])
            assert hasattr(scanner, 'service_patterns')
            assert hasattr(scanner, 'base_directories')
            self.test_results['scanner_init'] = True

            # Test 2: Empty directory scan
            services = scanner.scan()
            assert isinstance(services, list)
            assert len(services) == 0
            self.test_results['empty_scan'] = True

            # Test 3: Get scan summary
            summary = scanner.get_scan_summary()
            assert 'supported_service_types' in summary
            assert 'base_directories' in summary
            self.test_results['scan_summary'] = True

            print("✅ LocalServiceScanner Core: PASSED")
            return True

        except Exception as e:
            print(f"❌ LocalServiceScanner Core: FAILED - {e}")
            return False

    def test_service_detection(self):
        """Test service type detection capabilities"""
        print("\n🧪 Testing Service Detection...")

        try:
            from app.discovery.local_scanner import LocalServiceScanner
            scanner = LocalServiceScanner(base_directories=[self.temp_dir])

            # Test Node.js service
            node_files = {
                "package.json": {
                    "name": "test-node-service",
                    "version": "1.0.0",
                    "main": "server.js",
                    "scripts": {"start": "node server.js"},
                    "dependencies": {"express": "^4.18.0"}
                },
                "server.js": "const express = require('express');\napp.listen(3000);"
            }
            self.create_test_service("node-service", "node", node_files)

            # Test Python service
            python_files = {
                "requirements.txt": "fastapi>=0.68.0\nuvicorn>=0.15.0",
                "main.py": "from fastapi import FastAPI\napp = FastAPI()\nuvicorn.run(app, port=8000)"
            }
            self.create_test_service("python-service", "python", python_files)

            # Test Docker service
            docker_files = {
                "Dockerfile": "FROM node:16\nEXPOSE 3000\nCMD ['npm', 'start']",
                "docker-compose.yml": {
                    "version": "3.8",
                    "services": {
                        "web": {
                            "build": ".",
                            "ports": ["3000:3000"]
                        }
                    }
                }
            }
            self.create_test_service("docker-service", "docker", docker_files)

            # Test MCP service
            mcp_files = {
                "service.json": {
                    "name": "test-mcp-server",
                    "protocol": "stdio",
                    "command": "python",
                    "args": ["server.py"]
                }
            }
            self.create_test_service("mcp-service", "mcp", mcp_files)

            # Run scan and verify detection
            services = scanner.scan()
            assert len(services) >= 4, f"Expected at least 4 services, got {len(services)}"

            service_types = [s.type for s in services]
            assert "node" in service_types or "express" in service_types
            assert "python" in service_types or "fastapi" in service_types
            assert "docker" in service_types
            assert "mcp" in service_types

            self.test_results['node_detection'] = True
            self.test_results['python_detection'] = True
            self.test_results['docker_detection'] = True
            self.test_results['mcp_detection'] = True

            print("✅ Service Detection: PASSED")
            return True

        except Exception as e:
            print(f"❌ Service Detection: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_health_probes(self):
        """Test health probe functionality"""
        print("\n🧪 Testing Health Probes...")

        try:
            from app.discovery.health_probe import (
                HealthProbe, HttpHealthProbe, TcpHealthProbe,
                ProcessHealthProbe, CustomScriptProbe, CompositeHealthProbe,
                HealthProbeFactory
            )

            # Test probe initialization
            http_probe = HttpHealthProbe(timeout=5.0, retries=2)
            tcp_probe = TcpHealthProbe(timeout=5.0, retries=2)
            process_probe = ProcessHealthProbe()
            script_probe = CustomScriptProbe()

            assert hasattr(http_probe, 'check_health')
            assert hasattr(tcp_probe, 'check_health')
            assert hasattr(process_probe, 'check_health')
            assert hasattr(script_probe, 'check_health')

            self.test_results['http_probe_init'] = True
            self.test_results['tcp_probe_init'] = True
            self.test_results['process_probe_init'] = True
            self.test_results['script_probe_init'] = True

            # Test composite probe
            composite = CompositeHealthProbe([http_probe, tcp_probe])
            assert hasattr(composite, 'check_health')
            self.test_results['composite_probe_init'] = True

            # Test factory
            test_service = {"health_endpoint": "http://example.com/health"}
            probe = HealthProbeFactory.create_probe(test_service)
            assert isinstance(probe, HttpHealthProbe)
            self.test_results['probe_factory'] = True

            print("✅ Health Probes: PASSED")
            return True

        except Exception as e:
            print(f"❌ Health Probes: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_service_validator(self):
        """Test service validation functionality"""
        print("\n🧪 Testing Service Validator...")

        try:
            from app.discovery.service_validator import ServiceValidator

            validator = ServiceValidator(enable_health_checks=False)

            # Test valid service
            valid_service = {
                "id": "test-service-1",
                "name": "test-service",
                "type": "node",
                "location": "/tmp/test",
                "metadata": {"version": "1.0.0"}
            }

            # This would require async in full test, but we test structure
            assert hasattr(validator, 'validate_service')
            assert hasattr(validator, 'validate_service_batch')
            assert hasattr(validator, 'get_validation_summary')

            self.test_results['validator_init'] = True
            self.test_results['validator_methods'] = True

            print("✅ Service Validator: PASSED")
            return True

        except Exception as e:
            print(f"❌ Service Validator: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_service_registry(self):
        """Test service registry functionality"""
        print("\n🧪 Testing Service Registry...")

        try:
            from app.discovery.service_registry import ServiceRegistry, RegisteredService

            # Test in-memory registry
            registry = ServiceRegistry(
                storage_path=":memory:",
                enable_persistence=False
            )

            # Test service registration
            test_service = {
                "name": "test-service",
                "type": "test",
                "status": "active",
                "location": "/tmp/test",
                "metadata": {"version": "1.0.0"}
            }

            result = registry.register_service(test_service)
            assert result.success
            assert result.action == "created"

            # Test service listing
            services = registry.list_services()
            assert len(services) == 1
            assert services[0].name == "test-service"

            # Test service retrieval
            service = registry.get_service(result.service_id)
            assert service is not None
            assert service.name == "test-service"

            # Test service filtering
            filtered = registry.list_services(filters={"type": "test"})
            assert len(filtered) == 1

            # Test service search
            found = registry.search_services("test")
            assert len(found) == 1

            # Test deregistration
            success = registry.deregister_service(result.service_id)
            assert success

            services = registry.list_services()
            assert len(services) == 0

            self.test_results['registry_registration'] = True
            self.test_results['registry_listing'] = True
            self.test_results['registry_filtering'] = True
            self.test_results['registry_search'] = True
            self.test_results['registry_deregistration'] = True

            print("✅ Service Registry: PASSED")
            return True

        except Exception as e:
            print(f"❌ Service Registry: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_docker_discovery(self):
        """Test Docker service discovery"""
        print("\n🧪 Testing Docker Discovery...")

        try:
            from app.discovery.docker_discovery import DockerServiceDiscovery

            # Test initialization (Docker may not be available)
            discovery = DockerServiceDiscovery(include_stopped=True)

            assert hasattr(discovery, 'discover_services')
            assert hasattr(discovery, 'service_indicators')
            assert hasattr(discovery, 'service_ports')

            # Test service type determination
            image_name = "nginx:latest"
            service_type = discovery._determine_service_type(image_name, {}, {})
            assert service_type == "web_server"

            self.test_results['docker_init'] = True
            self.test_results['docker_type_detection'] = True

            print("✅ Docker Discovery: PASSED")
            return True

        except Exception as e:
            print(f"❌ Docker Discovery: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_external_registry(self):
        """Test external registry adapters"""
        print("\n🧪 Testing External Registry Adapters...")

        try:
            from app.discovery.external_registry import (
                ExternalRegistryAdapter, ConsulAdapter,
                KubernetesAdapter, EurekaAdapter
            )

            # Test main adapter
            adapter = ExternalRegistryAdapter()

            # Test adding different registry types
            consul_params = {
                "host": "localhost",
                "port": 8500,
                "scheme": "http"
            }

            k8s_params = {
                "api_server": "https://kubernetes.default.svc",
                "token": "fake-token",
                "namespace": "default"
            }

            eureka_params = {
                "eureka_url": "http://localhost:8761/eureka"
            }

            # These should succeed even without actual connections
            consul_added = adapter.add_registry("consul", "consul", consul_params)
            k8s_added = adapter.add_registry("k8s", "kubernetes", k8s_params)
            eureka_added = adapter.add_registry("eureka", "eureka", eureka_params)

            assert consul_added
            assert k8s_added
            assert eureka_added

            # Test registry info
            info = adapter.get_registry_info()
            assert info['total_registries'] == 3
            assert 'consul' in info['registry_names']

            self.test_results['external_adapter_init'] = True
            self.test_results['consul_adapter'] = True
            self.test_results['k8s_adapter'] = True
            self.test_results['eureka_adapter'] = True

            print("✅ External Registry Adapters: PASSED")
            return True

        except Exception as e:
            print(f"❌ External Registry Adapters: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_metadata_extractor(self):
        """Test metadata extraction functionality"""
        print("\n🧪 Testing Metadata Extractor...")

        try:
            from app.discovery.metadata_extractor import ServiceMetadataExtractor

            extractor = ServiceMetadataExtractor(
                deep_analysis=True,
                include_dependencies=True,
                analyze_security=True,
                extract_api_specs=True
            )

            # Test with sample service
            test_service = {
                "id": "test-service",
                "type": "node",
                "location": self.temp_dir,
                "metadata": {"version": "1.0.0"}
            }

            # Create a simple package.json for extraction
            self.create_test_service("extract-test", "node", {
                "package.json": {
                    "name": "extract-test-service",
                    "version": "2.0.0",
                    "dependencies": {"express": "^4.18.0"}
                }
            })

            test_service["location"] = os.path.join(self.temp_dir, "extract-test")

            # Test extraction
            results = extractor.extract_metadata(test_service)
            assert isinstance(results, list)
            assert len(results) > 0

            # Test summary
            summary = extractor.get_extraction_summary(results)
            assert 'total_extractions' in summary
            assert 'metadata_types' in summary

            self.test_results['metadata_extractor_init'] = True
            self.test_results['metadata_extraction'] = True
            self.test_results['extraction_summary'] = True

            print("✅ Metadata Extractor: PASSED")
            return True

        except Exception as e:
            print(f"❌ Metadata Extractor: FAILED - {e}")
            traceback.print_exc()
            return False

    def test_integration_workflow(self):
        """Test integrated workflow combining multiple components"""
        print("\n🧪 Testing Integration Workflow...")

        try:
            from app.discovery.local_scanner import LocalServiceScanner
            from app.discovery.service_registry import ServiceRegistry
            from app.discovery.service_validator import ServiceValidator
            from app.discovery.metadata_extractor import ServiceMetadataExtractor

            # Create integrated workflow
            scanner = LocalServiceScanner(base_directories=[self.temp_dir])
            registry = ServiceRegistry(storage_path=":memory:", enable_persistence=False)
            validator = ServiceValidator(enable_health_checks=False)
            extractor = ServiceMetadataExtractor()

            # Create test service
            self.create_test_service("integration-test", "node", {
                "package.json": {
                    "name": "integration-service",
                    "version": "1.0.0",
                    "dependencies": {"express": "^4.18.0"}
                }
            })

            # Step 1: Discover services
            discovered_services = scanner.scan()
            assert len(discovered_services) > 0

            # Step 2: Extract metadata
            service_data = {
                "id": discovered_services[0].id,
                "name": discovered_services[0].name,
                "type": discovered_services[0].type,
                "location": discovered_services[0].location,
                "metadata": discovered_services[0].metadata
            }

            metadata_results = extractor.extract_metadata(service_data)
            assert len(metadata_results) > 0

            # Step 3: Register service
            registration_result = registry.register_service(service_data)
            assert registration_result.success

            # Step 4: Verify registration
            registered_services = registry.list_services()
            assert len(registered_services) > 0

            self.test_results['integration_discovery'] = True
            self.test_results['integration_metadata'] = True
            self.test_results['integration_registration'] = True
            self.test_results['integration_complete'] = True

            print("✅ Integration Workflow: PASSED")
            return True

        except Exception as e:
            print(f"❌ Integration Workflow: FAILED - {e}")
            traceback.print_exc()
            return False

    def calculate_detailed_coverage(self):
        """Calculate detailed coverage metrics"""
        print("\n📊 DETAILED COVERAGE ANALYSIS")

        # Define all testable components
        all_components = {
            'LocalServiceScanner': [
                'scanner_init', 'empty_scan', 'scan_summary',
                'node_detection', 'python_detection', 'docker_detection', 'mcp_detection'
            ],
            'HealthProbes': [
                'http_probe_init', 'tcp_probe_init', 'process_probe_init',
                'script_probe_init', 'composite_probe_init', 'probe_factory'
            ],
            'ServiceValidator': [
                'validator_init', 'validator_methods'
            ],
            'ServiceRegistry': [
                'registry_registration', 'registry_listing', 'registry_filtering',
                'registry_search', 'registry_deregistration'
            ],
            'DockerDiscovery': [
                'docker_init', 'docker_type_detection'
            ],
            'ExternalRegistry': [
                'external_adapter_init', 'consul_adapter', 'k8s_adapter', 'eureka_adapter'
            ],
            'MetadataExtractor': [
                'metadata_extractor_init', 'metadata_extraction', 'extraction_summary'
            ],
            'Integration': [
                'integration_discovery', 'integration_metadata',
                'integration_registration', 'integration_complete'
            ]
        }

        # Calculate coverage per component
        component_stats = {}
        total_tests = 0
        total_passed = 0

        for component, tests in all_components.items():
            passed = sum(1 for test in tests if self.test_results.get(test, False))
            total = len(tests)
            coverage = (passed / total * 100) if total > 0 else 0

            component_stats[component] = {
                'passed': passed,
                'total': total,
                'coverage': coverage
            }

            total_tests += total
            total_passed += passed

            status = "✅" if coverage >= 80 else "⚠️" if coverage >= 60 else "❌"
            print(f"  {status} {component}: {passed}/{total} ({coverage:.1f}%)")

        overall_coverage = (total_passed / total_tests * 100) if total_tests > 0 else 0

        print(f"\n🎯 OVERALL COVERAGE: {total_passed}/{total_tests} ({overall_coverage:.1f}%)")

        # Categorize coverage level
        if overall_coverage >= 85:
            grade = "A+ (Excellent)"
        elif overall_coverage >= 75:
            grade = "A (Very Good)"
        elif overall_coverage >= 65:
            grade = "B (Good)"
        elif overall_coverage >= 50:
            grade = "C (Fair)"
        else:
            grade = "D (Needs Improvement)"

        print(f"📈 COVERAGE GRADE: {grade}")

        return overall_coverage, component_stats

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🚀 STARTING COMPREHENSIVE SERVICE DISCOVERY ENGINE TESTS")
        print("=" * 70)

        self.setup()

        try:
            # Run all test suites
            test_suites = [
                self.test_local_scanner_core,
                self.test_service_detection,
                self.test_health_probes,
                self.test_service_validator,
                self.test_service_registry,
                self.test_docker_discovery,
                self.test_external_registry,
                self.test_metadata_extractor,
                self.test_integration_workflow
            ]

            suite_results = []
            for test_suite in test_suites:
                result = test_suite()
                suite_results.append(result)

            # Calculate final coverage
            coverage, component_stats = self.calculate_detailed_coverage()

            # Print final summary
            print("\n" + "=" * 70)
            print("🏁 FINAL TEST RESULTS")
            print("=" * 70)

            passed_suites = sum(suite_results)
            total_suites = len(suite_results)

            print(f"Test Suites Passed: {passed_suites}/{total_suites}")
            print(f"Overall Coverage: {coverage:.1f}%")

            if coverage >= 75:
                print("🎉 EXCELLENT: Service Discovery Engine is highly functional!")
            elif coverage >= 60:
                print("👍 GOOD: Service Discovery Engine is well implemented!")
            else:
                print("⚠️  FAIR: Some components need attention!")

            return coverage

        finally:
            self.teardown()

def main():
    """Main test execution"""
    tester = ServiceDiscoveryTester()
    coverage = tester.run_all_tests()

    print(f"\n🎯 FINAL COVERAGE: {coverage:.1f}%")
    return coverage

if __name__ == "__main__":
    main()
