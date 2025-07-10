#!/usr/bin/env python3
"""
Docker MCP Server
Provides Docker container management operations using FastMCP.
"""

import asyncio
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    import docker
    from docker.errors import DockerException, APIError, NotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None
    DockerException = Exception
    APIError = Exception
    NotFound = Exception


class DockerMCP:
    """
    Docker MCP Server using FastMCP framework

    Provides comprehensive Docker operations including:
    - Container management (create, start, stop, remove)
    - Image management (pull, build, list, remove)
    - Network operations
    - Volume management
    - System information
    """

    def __init__(self):
        self.mcp = FastMCP("docker-mcp", version="1.0.0", description="Docker container and image management")
        self.docker_client: Optional[docker.DockerClient] = None
        self._setup_tools()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Docker client"""
        if not DOCKER_AVAILABLE:
            logfire.warning("Docker dependencies not available. Install with: pip install docker")
            return

        try:
            self.docker_client = docker.from_env()
            # Test connection
            self.docker_client.ping()
            logfire.info("Docker client initialized successfully")
        except Exception as e:
            logfire.error(f"Failed to initialize Docker client: {str(e)}")

    def _setup_tools(self):
        """Setup Docker MCP tools"""

        @self.mcp.tool(
            name="list_containers",
            description="List Docker containers",
            input_schema={
                "type": "object",
                "properties": {
                    "all": {"type": "boolean", "description": "Show all containers (default: False, running only)"},
                    "filters": {"type": "object", "description": "Filters to apply"}
                }
            }
        )
        async def list_containers(all: bool = False, filters: Dict[str, Any] = None) -> Dict[str, Any]:
            """List Docker containers"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                containers = self.docker_client.containers.list(all=all, filters=filters or {})

                container_list = []
                for container in containers:
                    container_list.append({
                        "id": container.id,
                        "short_id": container.short_id,
                        "name": container.name,
                        "image": container.image.tags[0] if container.image.tags else container.image.id,
                        "status": container.status,
                        "created": container.attrs["Created"],
                        "state": container.attrs["State"],
                        "ports": container.attrs.get("NetworkSettings", {}).get("Ports", {}),
                        "labels": container.labels
                    })

                return {
                    "containers": container_list,
                    "total_count": len(container_list)
                }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="get_container",
            description="Get detailed information about a specific container",
            input_schema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name"}
                },
                "required": ["container_id"]
            }
        )
        async def get_container(container_id: str) -> Dict[str, Any]:
            """Get container details"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                container = self.docker_client.containers.get(container_id)

                return {
                    "id": container.id,
                    "short_id": container.short_id,
                    "name": container.name,
                    "image": container.image.tags[0] if container.image.tags else container.image.id,
                    "status": container.status,
                    "created": container.attrs["Created"],
                    "state": container.attrs["State"],
                    "config": container.attrs["Config"],
                    "network_settings": container.attrs.get("NetworkSettings", {}),
                    "mounts": container.attrs.get("Mounts", []),
                    "labels": container.labels
                }
            except NotFound:
                return {"error": f"Container '{container_id}' not found"}
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="create_container",
            description="Create a new Docker container",
            input_schema={
                "type": "object",
                "properties": {
                    "image": {"type": "string", "description": "Docker image name"},
                    "name": {"type": "string", "description": "Container name"},
                    "command": {"type": "string", "description": "Command to run"},
                    "environment": {"type": "object", "description": "Environment variables"},
                    "ports": {"type": "object", "description": "Port mappings"},
                    "volumes": {"type": "object", "description": "Volume mappings"},
                    "detach": {"type": "boolean", "description": "Run in detached mode"}
                },
                "required": ["image"]
            }
        )
        async def create_container(image: str, name: str = None, command: str = None,
                                 environment: Dict[str, str] = None, ports: Dict[str, int] = None,
                                 volumes: Dict[str, Dict[str, str]] = None, detach: bool = True) -> Dict[str, Any]:
            """Create a new container"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                container = self.docker_client.containers.create(
                    image=image,
                    name=name,
                    command=command,
                    environment=environment or {},
                    ports=ports or {},
                    volumes=volumes or {},
                    detach=detach
                )

                return {
                    "id": container.id,
                    "short_id": container.short_id,
                    "name": container.name,
                    "status": "created"
                }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="start_container",
            description="Start a Docker container",
            input_schema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name"}
                },
                "required": ["container_id"]
            }
        )
        async def start_container(container_id: str) -> Dict[str, Any]:
            """Start a container"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                container = self.docker_client.containers.get(container_id)
                container.start()

                return {
                    "id": container.id,
                    "name": container.name,
                    "status": "started"
                }
            except NotFound:
                return {"error": f"Container '{container_id}' not found"}
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="stop_container",
            description="Stop a Docker container",
            input_schema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name"},
                    "timeout": {"type": "integer", "description": "Seconds to wait before killing"}
                },
                "required": ["container_id"]
            }
        )
        async def stop_container(container_id: str, timeout: int = 10) -> Dict[str, Any]:
            """Stop a container"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                container = self.docker_client.containers.get(container_id)
                container.stop(timeout=timeout)

                return {
                    "id": container.id,
                    "name": container.name,
                    "status": "stopped"
                }
            except NotFound:
                return {"error": f"Container '{container_id}' not found"}
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="remove_container",
            description="Remove a Docker container",
            input_schema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name"},
                    "force": {"type": "boolean", "description": "Force removal of running container"},
                    "volumes": {"type": "boolean", "description": "Remove associated volumes"}
                },
                "required": ["container_id"]
            }
        )
        async def remove_container(container_id: str, force: bool = False, volumes: bool = False) -> Dict[str, Any]:
            """Remove a container"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                container = self.docker_client.containers.get(container_id)
                container.remove(force=force, v=volumes)

                return {
                    "id": container_id,
                    "status": "removed"
                }
            except NotFound:
                return {"error": f"Container '{container_id}' not found"}
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="get_container_logs",
            description="Get logs from a Docker container",
            input_schema={
                "type": "object",
                "properties": {
                    "container_id": {"type": "string", "description": "Container ID or name"},
                    "tail": {"type": "integer", "description": "Number of lines from end of logs"},
                    "timestamps": {"type": "boolean", "description": "Include timestamps"},
                    "follow": {"type": "boolean", "description": "Follow log output"}
                },
                "required": ["container_id"]
            }
        )
        async def get_container_logs(container_id: str, tail: int = 100, timestamps: bool = False, follow: bool = False) -> Dict[str, Any]:
            """Get container logs"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                container = self.docker_client.containers.get(container_id)
                logs = container.logs(tail=tail, timestamps=timestamps, follow=follow)

                return {
                    "container_id": container_id,
                    "logs": logs.decode('utf-8') if isinstance(logs, bytes) else str(logs),
                    "tail": tail,
                    "timestamps": timestamps
                }
            except NotFound:
                return {"error": f"Container '{container_id}' not found"}
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="list_images",
            description="List Docker images",
            input_schema={
                "type": "object",
                "properties": {
                    "all": {"type": "boolean", "description": "Show all images including intermediates"},
                    "filters": {"type": "object", "description": "Filters to apply"}
                }
            }
        )
        async def list_images(all: bool = False, filters: Dict[str, Any] = None) -> Dict[str, Any]:
            """List Docker images"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                images = self.docker_client.images.list(all=all, filters=filters or {})

                image_list = []
                for image in images:
                    image_list.append({
                        "id": image.id,
                        "short_id": image.short_id,
                        "tags": image.tags,
                        "created": image.attrs["Created"],
                        "size": image.attrs["Size"],
                        "virtual_size": image.attrs["VirtualSize"],
                        "labels": image.labels
                    })

                return {
                    "images": image_list,
                    "total_count": len(image_list)
                }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="pull_image",
            description="Pull a Docker image from registry",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {"type": "string", "description": "Image repository name"},
                    "tag": {"type": "string", "description": "Image tag"},
                    "all_tags": {"type": "boolean", "description": "Pull all tags"}
                },
                "required": ["repository"]
            }
        )
        async def pull_image(repository: str, tag: str = "latest", all_tags: bool = False) -> Dict[str, Any]:
            """Pull an image"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                image = self.docker_client.images.pull(
                    repository=repository,
                    tag=None if all_tags else tag,
                    all_tags=all_tags
                )

                if all_tags:
                    return {
                        "repository": repository,
                        "status": "pulled all tags"
                    }
                else:
                    return {
                        "id": image.id,
                        "tags": image.tags,
                        "status": "pulled"
                    }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="remove_image",
            description="Remove a Docker image",
            input_schema={
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "Image ID or tag"},
                    "force": {"type": "boolean", "description": "Force removal"},
                    "noprune": {"type": "boolean", "description": "Do not delete untagged parents"}
                },
                "required": ["image_id"]
            }
        )
        async def remove_image(image_id: str, force: bool = False, noprune: bool = False) -> Dict[str, Any]:
            """Remove an image"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                self.docker_client.images.remove(image=image_id, force=force, noprune=noprune)

                return {
                    "image_id": image_id,
                    "status": "removed"
                }
            except NotFound:
                return {"error": f"Image '{image_id}' not found"}
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="get_system_info",
            description="Get Docker system information",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_system_info() -> Dict[str, Any]:
            """Get Docker system information"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                info = self.docker_client.info()
                version = self.docker_client.version()

                return {
                    "containers": info.get("Containers", 0),
                    "containers_running": info.get("ContainersRunning", 0),
                    "containers_paused": info.get("ContainersPaused", 0),
                    "containers_stopped": info.get("ContainersStopped", 0),
                    "images": info.get("Images", 0),
                    "server_version": info.get("ServerVersion"),
                    "kernel_version": info.get("KernelVersion"),
                    "operating_system": info.get("OperatingSystem"),
                    "total_memory": info.get("MemTotal"),
                    "cpu_count": info.get("NCPU"),
                    "docker_root_dir": info.get("DockerRootDir"),
                    "storage_driver": info.get("Driver"),
                    "version_info": version
                }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="list_networks",
            description="List Docker networks",
            input_schema={
                "type": "object",
                "properties": {
                    "filters": {"type": "object", "description": "Filters to apply"}
                }
            }
        )
        async def list_networks(filters: Dict[str, Any] = None) -> Dict[str, Any]:
            """List Docker networks"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                networks = self.docker_client.networks.list(filters=filters or {})

                network_list = []
                for network in networks:
                    network_list.append({
                        "id": network.id,
                        "short_id": network.short_id,
                        "name": network.name,
                        "driver": network.attrs.get("Driver"),
                        "scope": network.attrs.get("Scope"),
                        "created": network.attrs.get("Created"),
                        "internal": network.attrs.get("Internal", False),
                        "attachable": network.attrs.get("Attachable", False),
                        "containers": list(network.attrs.get("Containers", {}).keys())
                    })

                return {
                    "networks": network_list,
                    "total_count": len(network_list)
                }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

        @self.mcp.tool(
            name="list_volumes",
            description="List Docker volumes",
            input_schema={
                "type": "object",
                "properties": {
                    "filters": {"type": "object", "description": "Filters to apply"}
                }
            }
        )
        async def list_volumes(filters: Dict[str, Any] = None) -> Dict[str, Any]:
            """List Docker volumes"""
            if not self._check_client():
                return {"error": "Docker client not available"}

            try:
                volumes = self.docker_client.volumes.list(filters=filters or {})

                volume_list = []
                for volume in volumes:
                    volume_list.append({
                        "name": volume.name,
                        "driver": volume.attrs.get("Driver"),
                        "mountpoint": volume.attrs.get("Mountpoint"),
                        "created": volume.attrs.get("CreatedAt"),
                        "scope": volume.attrs.get("Scope"),
                        "labels": volume.attrs.get("Labels", {}),
                        "options": volume.attrs.get("Options", {})
                    })

                return {
                    "volumes": volume_list,
                    "total_count": len(volume_list)
                }
            except DockerException as e:
                return {"error": f"Docker error: {str(e)}"}
            except Exception as e:
                return {"error": f"Unexpected error: {str(e)}"}

    def _check_client(self) -> bool:
        """Check if Docker client is available and initialized"""
        if not DOCKER_AVAILABLE:
            return False
        return self.docker_client is not None

    async def run(self):
        """Run the Docker MCP server"""
        await self.mcp.run_stdio()


async def main():
    """Main entry point"""
    server = DockerMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
