"""
Test module for Local Service Scanner functionality
"""

import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from app.discovery.local_scanner import LocalServiceScanner, ServiceInfo


class TestLocalServiceScanner:
    """Test cases for LocalServiceScanner"""

    def setup_method(self):
        """Set up test environment before each test"""
        self.temp_dir = tempfile.mkdtemp()
        self.scanner = LocalServiceScanner(
            base_directories=[self.temp_dir],
            max_depth=3
        )

    def teardown_method(self):
        """Clean up test environment after each test"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def create_test_service(self, service_name: str, service_type: str, files: dict):
        """Helper method to create test service directory structure"""
        service_dir = os.path.join(self.temp_dir, service_name)
        os.makedirs(service_dir, exist_ok=True)

        for filename, content in files.items():
            file_path = os.path.join(service_dir, filename)
            with open(file_path, 'w') as f:
                if isinstance(content, dict):
                    json.dump(content, f, indent=2)
                else:
                    f.write(content)

        return service_dir

    def test_scan_empty_directory(self):
        """Test scanning empty directory"""
        services = self.scanner.scan()
        assert len(services) == 0

    def test_scan_node_service(self):
        """Test scanning Node.js service"""
        package_json = {
            "name": "test-node-service",
            "version": "1.0.0",
            "description": "Test Node.js service",
            "main": "server.js",
            "scripts": {
                "start": "node server.js",
                "test": "jest"
            },
            "dependencies": {
                "express": "^4.18.0",
                "lodash": "^4.17.21"
            }
        }

        server_js = """
const express = require('express');
const app = express();

app.get('/health', (req, res) => {
    res.json({ status: 'healthy' });
});

app.listen(3000, () => {
    console.log('Server running on port 3000');
});
"""

        self.create_test_service("node-app", "node", {
            "package.json": package_json,
            "server.js": server_js
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]

        assert service.name == "test-node-service"
        assert service.type == "express"
        assert service.metadata["version"] == "1.0.0"
        assert "express" in service.metadata["dependencies"]
        assert service.port == 3000

    def test_scan_python_service(self):
        """Test scanning Python service"""
        pyproject_toml = """
[project]
name = "test-python-service"
version = "1.0.0"
description = "Test Python service"
dependencies = [
    "fastapi>=0.68.0",
    "uvicorn>=0.15.0"
]

[project.scripts]
start = "uvicorn main:app"
"""

        main_py = """
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

        self.create_test_service("python-app", "python", {
            "pyproject.toml": pyproject_toml,
            "main.py": main_py
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]
        assert service.name == "test-python-service"
        assert service.type == "fastapi"
        assert service.metadata["version"] == "1.0.0"
        assert any("fastapi" in dep for dep in service.metadata["dependencies"])
        assert service.port == 8000

    def test_scan_docker_service(self):
        """Test scanning Docker service"""
        dockerfile = """
FROM node:16-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 3000
CMD ["npm", "start"]
"""

        docker_compose = {
            "version": "3.8",
            "services": {
                "web": {
                    "build": ".",
                    "ports": ["3000:3000"],
                    "environment": [
                        "NODE_ENV=production"
                    ]
                }
            }
        }

        self.create_test_service("docker-app", "docker", {
            "Dockerfile": dockerfile,
            "docker-compose.yml": docker_compose
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]
        assert service.type == "docker"
        assert "3000" in service.metadata["exposed_ports"]
        assert service.metadata["compose_version"] == "3.8"

    def test_scan_mcp_service(self):
        """Test scanning MCP service"""
        mcp_config = {
            "name": "test-mcp-server",
            "protocol": "stdio",
            "command": "python",
            "args": ["server.py"],
            "description": "Test MCP server",
            "tags": ["mcp", "test"],
            "env": {
                "LOG_LEVEL": "INFO"
            }
        }

        self.create_test_service("mcp-server", "mcp", {
            "service.json": mcp_config
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]
        assert service.name == "test-mcp-server"
        assert service.type == "mcp"
        assert service.metadata["protocol"] == "stdio"
        assert "mcp" in service.metadata["tags"]

    def test_scan_fastapi_service(self):
        """Test scanning FastAPI service"""
        main_py = """
from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Test API", version="1.0.0")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

        requirements_txt = """
fastapi>=0.68.0
uvicorn>=0.15.0
pydantic>=1.8.0
"""

        self.create_test_service("fastapi-app", "fastapi", {
            "main.py": main_py,
            "requirements.txt": requirements_txt
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]
        assert service.type == "fastapi"
        assert service.port == 8000
        assert service.health_endpoint == "http://localhost:8000/health"

    def test_scan_multiple_services(self):
        """Test scanning multiple services"""
        # Create Node.js service
        self.create_test_service("node-app", "node", {
            "package.json": {
                "name": "node-service",
                "main": "index.js",
                "scripts": {"start": "node index.js"}
            }
        })

        # Create Python service
        self.create_test_service("python-app", "python", {
            "requirements.txt": "flask>=2.0.0",
            "app.py": "from flask import Flask\napp = Flask(__name__)"
        })

        # Create Docker service
        self.create_test_service("docker-app", "docker", {
            "Dockerfile": "FROM alpine\nEXPOSE 8080"
        })

        services = self.scanner.scan()

        assert len(services) == 3
        service_types = [s.type for s in services]
        assert "node" in service_types
        assert "flask" in service_types
        assert "docker" in service_types

    def test_scan_specific_directory(self):
        """Test scanning specific directory"""
        specific_dir = os.path.join(self.temp_dir, "specific")
        os.makedirs(specific_dir)

        self.create_test_service("specific/test-app", "node", {
            "package.json": {"name": "specific-service"}
        })

        services = self.scanner.scan_specific_directory(specific_dir)

        assert len(services) == 1
        assert services[0].name == "specific-service"

    def test_scan_nonexistent_directory(self):
        """Test scanning non-existent directory"""
        nonexistent_dir = "/path/that/does/not/exist"
        services = self.scanner.scan_specific_directory(nonexistent_dir)
        assert len(services) == 0

    def test_max_depth_limit(self):
        """Test maximum depth limit"""
        # Create deeply nested structure
        deep_path = self.temp_dir
        for i in range(10):
            deep_path = os.path.join(deep_path, f"level{i}")
            os.makedirs(deep_path, exist_ok=True)

        # Create service at deep level
        service_path = os.path.join(deep_path, "deep-service")
        os.makedirs(service_path)
        with open(os.path.join(service_path, "package.json"), 'w') as f:
            json.dump({"name": "deep-service"}, f)

        services = self.scanner.scan()
        # Should not find the deeply nested service due to max_depth=3
        assert len(services) == 0

    def test_permission_error_handling(self):
        """Test handling of permission errors"""
        with patch('os.listdir', side_effect=PermissionError("Access denied")):
            services = self.scanner.scan()
            # Should handle permission error gracefully
            assert len(services) == 0

    def test_file_content_analysis(self):
        """Test file content analysis for service indicators"""
        # Create Python file with FastAPI indicators
        fastapi_content = """
from fastapi import FastAPI
app = FastAPI()

@app.get("/api/users")
def get_users():
    return []
"""

        self.create_test_service("api-service", "python", {
            "main.py": fastapi_content,
            "requirements.txt": "fastapi\nuvicorn"
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]
        assert service.type == "fastapi"  # Should detect FastAPI based on content

    def test_metadata_extraction_accuracy(self):
        """Test accuracy of metadata extraction"""
        complex_package_json = {
            "name": "complex-service",
            "version": "2.1.0",
            "description": "A complex Node.js service",
            "main": "dist/server.js",
            "scripts": {
                "start": "node dist/server.js",
                "build": "tsc",
                "test": "jest",
                "dev": "nodemon src/server.ts"
            },
            "dependencies": {
                "express": "^4.18.0",
                "typescript": "^4.7.0",
                "mongoose": "^6.3.0"
            },
            "devDependencies": {
                "jest": "^28.0.0",
                "nodemon": "^2.0.0"
            },
            "keywords": ["api", "service", "nodejs"],
            "author": "Test Developer",
            "license": "MIT"
        }

        self.create_test_service("complex-app", "node", {
            "package.json": complex_package_json
        })

        services = self.scanner.scan()

        assert len(services) == 1
        service = services[0]
        metadata = service.metadata

        assert metadata["name"] == "complex-service"
        assert metadata["version"] == "2.1.0"
        assert metadata["author"] == "Test Developer"
        assert metadata["license"] == "MIT"
        assert "express" in metadata["dependencies"]
        assert "jest" in metadata["dependencies"]  # Includes dev dependencies
        assert metadata["framework_indicators"] == ["express", "typescript"]

    def test_get_scan_summary(self):
        """Test scan summary functionality"""
        summary = self.scanner.get_scan_summary()

        assert "base_directories" in summary
        assert "max_depth" in summary
        assert "supported_service_types" in summary
        assert "service_patterns" in summary

        assert self.temp_dir in summary["base_directories"]
        assert summary["max_depth"] == 3
        assert "node" in summary["supported_service_types"]
        assert "python" in summary["supported_service_types"]

    def test_service_info_structure(self):
        """Test ServiceInfo data structure"""
        self.create_test_service("test-service", "node", {
            "package.json": {"name": "test"}
        })

        services = self.scanner.scan()
        service = services[0]

        # Verify all required fields are present
        assert hasattr(service, 'id')
        assert hasattr(service, 'name')
        assert hasattr(service, 'type')
        assert hasattr(service, 'location')
        assert hasattr(service, 'metadata')
        assert hasattr(service, 'config_files')
        assert hasattr(service, 'discovered_at')

        # Verify data types
        assert isinstance(service.id, str)
        assert isinstance(service.name, str)
        assert isinstance(service.type, str)
        assert isinstance(service.metadata, dict)
        assert isinstance(service.config_files, list)

    def test_error_resilience(self):
        """Test error resilience during scanning"""
        # Create valid service
        self.create_test_service("good-service", "node", {
            "package.json": {"name": "good-service"}
        })

        # Create directory with invalid JSON
        bad_service_dir = os.path.join(self.temp_dir, "bad-service")
        os.makedirs(bad_service_dir)
        with open(os.path.join(bad_service_dir, "package.json"), 'w') as f:
            f.write("invalid json content")

        services = self.scanner.scan()

        # Should find both services - the good one with full metadata, bad one with limited metadata
        assert len(services) == 2
        # Find the good service (has full metadata)
        good_service = next((s for s in services if s.name == "good-service"), None)
        bad_service = next((s for s in services if s.name == "bad-service"), None)

        assert good_service is not None
        assert bad_service is not None

        # Good service should have complete metadata
        assert good_service.metadata.get("name") == "good-service"

        # Bad service should have limited metadata due to parsing error
        assert bad_service.metadata.get("name") is None or bad_service.metadata.get("name") == "bad-service"

    def test_framework_detection(self):
        """Test framework detection accuracy"""
        # Test Express detection
        express_package = {
            "name": "express-app",
            "dependencies": {"express": "^4.18.0"}
        }

        self.create_test_service("express-app", "node", {
            "package.json": express_package
        })

        services = self.scanner.scan()
        service = services[0]
        assert "express" in service.metadata["framework_indicators"]

    def test_health_endpoint_detection(self):
        """Test health endpoint detection"""
        # FastAPI service with custom port
        fastapi_content = """
from fastapi import FastAPI
app = FastAPI()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, port=9000)
"""

        self.create_test_service("custom-port-service", "python", {
            "main.py": fastapi_content,
            "requirements.txt": "fastapi"
        })

        services = self.scanner.scan()
        service = services[0]

        assert service.port == 9000
        assert service.health_endpoint == "http://localhost:9000/health"

    def test_docker_compose_parsing(self):
        """Test Docker Compose file parsing"""
        compose_content = {
            "version": "3.8",
            "services": {
                "api": {
                    "build": ".",
                    "ports": ["8080:8080"],
                    "environment": {
                        "NODE_ENV": "production"
                    }
                },
                "db": {
                    "image": "postgres:13",
                    "environment": {
                        "POSTGRES_DB": "testdb"
                    }
                }
            }
        }

        self.create_test_service("compose-app", "docker", {
            "docker-compose.yml": compose_content
        })

        services = self.scanner.scan()
        service = services[0]

        assert "8080:8080" in service.metadata["ports"]
        assert service.metadata["service_count"] == 2

    def test_concurrent_scanning(self):
        """Test concurrent scanning capabilities"""
        # Create multiple services
        for i in range(5):
            self.create_test_service(f"service-{i}", "node", {
                "package.json": {"name": f"service-{i}"}
            })

        # Run scan multiple times to test consistency
        results = []
        for _ in range(3):
            result = self.scanner.scan()
            results.append(result)

        # All scans should return the same number of services
        for result in results:
            assert len(result) == 5
