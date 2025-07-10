#!/usr/bin/env python3
"""
Test suite for Docker MCP Server
Tests Docker container management operations using FastMCP framework.
"""

import pytest
import asyncio
import json
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_servers.docker_mcp import DockerMCP


class TestDockerMCP:
    """Test Docker MCP server functionality"""

    @pytest.fixture
    def docker_mcp(self):
        """Create DockerMCP instance for testing"""
        return DockerMCP()

    @pytest.fixture
    def mock_docker_client(self):
        """Mock Docker client for testing"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.containers = Mock()
        mock_client.images = Mock()
        mock_client.networks = Mock()
        mock_client.volumes = Mock()
        mock_client.info.return_value = {
            "Containers": 5,
            "ContainersRunning": 2,
            "ContainersPaused": 0,
            "ContainersStopped": 3,
            "Images": 10,
            "ServerVersion": "20.10.0",
            "KernelVersion": "5.4.0",
            "OperatingSystem": "Ubuntu 20.04",
            "MemTotal": 8589934592,
            "NCPU": 4,
            "DockerRootDir": "/var/lib/docker",
            "Driver": "overlay2"
        }
        mock_client.version.return_value = {
            "Version": "20.10.0",
            "ApiVersion": "1.41"
        }
        return mock_client

    @pytest.fixture
    def mock_container(self):
        """Mock Docker container for testing"""
        container = Mock()
        container.id = "abc123"
        container.short_id = "abc123"
        container.name = "test-container"
        container.image.tags = ["nginx:latest"]
        container.status = "running"
        container.attrs = {
            "Created": "2023-01-01T00:00:00Z",
            "State": {"Status": "running", "Running": True},
            "Config": {"Image": "nginx:latest"},
            "NetworkSettings": {"Ports": {"80/tcp": [{"HostPort": "8080"}]}},
            "Mounts": []
        }
        container.labels = {"app": "test"}
        container.logs.return_value = b"Test log output"
        return container

    @pytest.fixture
    def mock_image(self):
        """Mock Docker image for testing"""
        image = Mock()
        image.id = "sha256:def456"
        image.short_id = "def456"
        image.tags = ["nginx:latest"]
        image.attrs = {
            "Created": "2023-01-01T00:00:00Z",
            "Size": 142000000,
            "VirtualSize": 142000000
        }
        image.labels = {}
        return image

    def test_docker_mcp_initialization(self, docker_mcp):
        """Test DockerMCP initialization"""
        assert docker_mcp.mcp is not None
        assert docker_mcp.mcp.name == "docker-mcp"
        assert docker_mcp.mcp.version == "1.0.0"

    @patch('mcp_servers.docker_mcp.docker')
    def test_docker_client_initialization_success(self, mock_docker, docker_mcp):
        """Test successful Docker client initialization"""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_docker.from_env.return_value = mock_client

        docker_mcp._initialize_client()

        assert docker_mcp.docker_client is not None
        mock_docker.from_env.assert_called_once()
        mock_client.ping.assert_called_once()

    @patch('mcp_servers.docker_mcp.docker')
    def test_docker_client_initialization_failure(self, mock_docker, docker_mcp):
        """Test failed Docker client initialization"""
        mock_docker.from_env.side_effect = Exception("Docker not available")

        docker_mcp._initialize_client()

        # Should not raise exception, but client should be None
        assert docker_mcp.docker_client is None

    @patch('mcp_servers.docker_mcp.DOCKER_AVAILABLE', False)
    def test_docker_not_available(self, docker_mcp):
        """Test behavior when Docker is not available"""
        docker_mcp._initialize_client()
        assert docker_mcp.docker_client is None
        assert not docker_mcp._check_client()

    @pytest.mark.asyncio
    async def test_list_containers_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container listing"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.list.return_value = [mock_container]

        # Get the list_containers tool function
        tools = docker_mcp.mcp.tools
        list_containers_tool = next(tool for tool in tools if tool.name == "list_containers")

        result = await list_containers_tool.handler(all=False)

        assert "containers" in result
        assert result["total_count"] == 1
        assert result["containers"][0]["id"] == "abc123"
        assert result["containers"][0]["name"] == "test-container"
        assert result["containers"][0]["status"] == "running"

    @pytest.mark.asyncio
    async def test_list_containers_no_client(self, docker_mcp):
        """Test container listing without Docker client"""
        docker_mcp.docker_client = None

        tools = docker_mcp.mcp.tools
        list_containers_tool = next(tool for tool in tools if tool.name == "list_containers")

        result = await list_containers_tool.handler(all=False)

        assert "error" in result
        assert "Docker client not available" in result["error"]

    @pytest.mark.asyncio
    async def test_get_container_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container retrieval"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        tools = docker_mcp.mcp.tools
        get_container_tool = next(tool for tool in tools if tool.name == "get_container")

        result = await get_container_tool.handler(container_id="abc123")

        assert result["id"] == "abc123"
        assert result["name"] == "test-container"
        assert result["status"] == "running"
        assert "config" in result
        assert "network_settings" in result

    @pytest.mark.asyncio
    async def test_get_container_not_found(self, docker_mcp, mock_docker_client):
        """Test container retrieval when container not found"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.get.side_effect = Exception("Container not found")

        tools = docker_mcp.mcp.tools
        get_container_tool = next(tool for tool in tools if tool.name == "get_container")

        result = await get_container_tool.handler(container_id="nonexistent")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_create_container_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container creation"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.create.return_value = mock_container

        tools = docker_mcp.mcp.tools
        create_container_tool = next(tool for tool in tools if tool.name == "create_container")

        result = await create_container_tool.handler(
            image="nginx:latest",
            name="test-container",
            environment={"ENV": "test"}
        )

        assert result["id"] == "abc123"
        assert result["name"] == "test-container"
        assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_start_container_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container start"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        tools = docker_mcp.mcp.tools
        start_container_tool = next(tool for tool in tools if tool.name == "start_container")

        result = await start_container_tool.handler(container_id="abc123")

        assert result["id"] == "abc123"
        assert result["status"] == "started"
        mock_container.start.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_container_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container stop"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        tools = docker_mcp.mcp.tools
        stop_container_tool = next(tool for tool in tools if tool.name == "stop_container")

        result = await stop_container_tool.handler(container_id="abc123", timeout=10)

        assert result["id"] == "abc123"
        assert result["status"] == "stopped"
        mock_container.stop.assert_called_once_with(timeout=10)

    @pytest.mark.asyncio
    async def test_remove_container_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container removal"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        tools = docker_mcp.mcp.tools
        remove_container_tool = next(tool for tool in tools if tool.name == "remove_container")

        result = await remove_container_tool.handler(container_id="abc123", force=True)

        assert result["id"] == "abc123"
        assert result["status"] == "removed"
        mock_container.remove.assert_called_once_with(force=True, v=False)

    @pytest.mark.asyncio
    async def test_get_container_logs_success(self, docker_mcp, mock_docker_client, mock_container):
        """Test successful container logs retrieval"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.containers.get.return_value = mock_container

        tools = docker_mcp.mcp.tools
        get_logs_tool = next(tool for tool in tools if tool.name == "get_container_logs")

        result = await get_logs_tool.handler(container_id="abc123", tail=50)

        assert result["container_id"] == "abc123"
        assert "logs" in result
        assert result["tail"] == 50
        mock_container.logs.assert_called_once_with(tail=50, timestamps=False, follow=False)

    @pytest.mark.asyncio
    async def test_list_images_success(self, docker_mcp, mock_docker_client, mock_image):
        """Test successful image listing"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.images.list.return_value = [mock_image]

        tools = docker_mcp.mcp.tools
        list_images_tool = next(tool for tool in tools if tool.name == "list_images")

        result = await list_images_tool.handler(all=False)

        assert "images" in result
        assert result["total_count"] == 1
        assert result["images"][0]["id"] == "sha256:def456"
        assert result["images"][0]["tags"] == ["nginx:latest"]

    @pytest.mark.asyncio
    async def test_pull_image_success(self, docker_mcp, mock_docker_client, mock_image):
        """Test successful image pull"""
        docker_mcp.docker_client = mock_docker_client
        mock_docker_client.images.pull.return_value = mock_image

        tools = docker_mcp.mcp.tools
        pull_image_tool = next(tool for tool in tools if tool.name == "pull_image")

        result = await pull_image_tool.handler(repository="nginx", tag="latest")

        assert result["id"] == "sha256:def456"
        assert result["status"] == "pulled"
        mock_docker_client.images.pull.assert_called_once_with(
            repository="nginx",
            tag="latest",
            all_tags=False
        )

    @pytest.mark.asyncio
    async def test_remove_image_success(self, docker_mcp, mock_docker_client):
        """Test successful image removal"""
        docker_mcp.docker_client = mock_docker_client

        tools = docker_mcp.mcp.tools
        remove_image_tool = next(tool for tool in tools if tool.name == "remove_image")

        result = await remove_image_tool.handler(image_id="nginx:latest", force=True)

        assert result["image_id"] == "nginx:latest"
        assert result["status"] == "removed"
        mock_docker_client.images.remove.assert_called_once_with(
            image="nginx:latest",
            force=True,
            noprune=False
        )

    @pytest.mark.asyncio
    async def test_get_system_info_success(self, docker_mcp, mock_docker_client):
        """Test successful system info retrieval"""
        docker_mcp.docker_client = mock_docker_client

        tools = docker_mcp.mcp.tools
        system_info_tool = next(tool for tool in tools if tool.name == "get_system_info")

        result = await system_info_tool.handler()

        assert result["containers"] == 5
        assert result["containers_running"] == 2
        assert result["containers_stopped"] == 3
        assert result["images"] == 10
        assert result["server_version"] == "20.10.0"
        assert result["operating_system"] == "Ubuntu 20.04"

    @pytest.mark.asyncio
    async def test_list_networks_success(self, docker_mcp, mock_docker_client):
        """Test successful network listing"""
        docker_mcp.docker_client = mock_docker_client

        mock_network = Mock()
        mock_network.id = "net123"
        mock_network.short_id = "net123"
        mock_network.name = "bridge"
        mock_network.attrs = {
            "Driver": "bridge",
            "Scope": "local",
            "Created": "2023-01-01T00:00:00Z",
            "Internal": False,
            "Attachable": False,
            "Containers": {}
        }

        mock_docker_client.networks.list.return_value = [mock_network]

        tools = docker_mcp.mcp.tools
        list_networks_tool = next(tool for tool in tools if tool.name == "list_networks")

        result = await list_networks_tool.handler()

        assert "networks" in result
        assert result["total_count"] == 1
        assert result["networks"][0]["id"] == "net123"
        assert result["networks"][0]["name"] == "bridge"
        assert result["networks"][0]["driver"] == "bridge"

    @pytest.mark.asyncio
    async def test_list_volumes_success(self, docker_mcp, mock_docker_client):
        """Test successful volume listing"""
        docker_mcp.docker_client = mock_docker_client

        mock_volume = Mock()
        mock_volume.name = "test-volume"
        mock_volume.attrs = {
            "Driver": "local",
            "Mountpoint": "/var/lib/docker/volumes/test-volume/_data",
            "CreatedAt": "2023-01-01T00:00:00Z",
            "Scope": "local",
            "Labels": {},
            "Options": {}
        }

        mock_docker_client.volumes.list.return_value = [mock_volume]

        tools = docker_mcp.mcp.tools
        list_volumes_tool = next(tool for tool in tools if tool.name == "list_volumes")

        result = await list_volumes_tool.handler()

        assert "volumes" in result
        assert result["total_count"] == 1
        assert result["volumes"][0]["name"] == "test-volume"
        assert result["volumes"][0]["driver"] == "local"

    def test_check_client_with_client(self, docker_mcp, mock_docker_client):
        """Test _check_client method with valid client"""
        docker_mcp.docker_client = mock_docker_client
        assert docker_mcp._check_client() is True

    def test_check_client_without_client(self, docker_mcp):
        """Test _check_client method without client"""
        docker_mcp.docker_client = None
        assert docker_mcp._check_client() is False

    @patch('mcp_servers.docker_mcp.DOCKER_AVAILABLE', False)
    def test_check_client_docker_not_available(self, docker_mcp):
        """Test _check_client method when Docker is not available"""
        assert docker_mcp._check_client() is False

    @pytest.mark.asyncio
    async def test_main_function(self):
        """Test main function execution"""
        from mcp_servers.docker_mcp import main

        # Mock the DockerMCP.run method to avoid actual server startup
        with patch('mcp_servers.docker_mcp.DockerMCP.run') as mock_run:
            await main()
            mock_run.assert_called_once()
