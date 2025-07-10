#!/usr/bin/env python3
"""
Docker MCP Server - Production Implementation
Container Management and Orchestration via MCP
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import mcp.types as types
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio

try:
    import docker
    from docker.errors import DockerException, APIError, NotFound, ImageNotFound
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    print("Warning: Docker SDK not installed. Install with: pip install docker")


class DockerMCPServer:
    """Production Docker MCP Server implementation"""

    def __init__(self):
        self.server = Server("docker-mcp")
        self.docker_client = None
        self._initialized = False

        # Register handlers
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return self._get_tools()

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Optional[Dict[str, Any]] = None) -> List[types.TextContent]:
            return await self._handle_tool_call(name, arguments or {})

    def _initialize_docker_client(self):
        """Initialize Docker client"""
        if not DOCKER_AVAILABLE:
            raise RuntimeError("Docker SDK not installed")

        if not self.docker_client:
            try:
                # Try to connect to Docker daemon
                self.docker_client = docker.from_env()
                # Test connection
                self.docker_client.ping()
                self._initialized = True
            except DockerException as e:
                raise RuntimeError(f"Failed to connect to Docker daemon: {e}")

    def _get_tools(self) -> List[types.Tool]:
        """Define available Docker management tools"""
        return [
            types.Tool(
                name="docker_list_containers",
                description="List all Docker containers",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "all": {
                            "type": "boolean",
                            "description": "Show all containers (default shows just running)",
                            "default": False
                        },
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply (e.g., {'status': 'running'})",
                            "properties": {
                                "status": {
                                    "type": "string",
                                    "enum": ["created", "restarting", "running", "removing", "paused", "exited", "dead"]
                                },
                                "label": {"type": "string"},
                                "name": {"type": "string"}
                            }
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of containers to return",
                            "default": -1
                        }
                    }
                }
            ),
            types.Tool(
                name="docker_create_container",
                description="Create a new Docker container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image": {
                            "type": "string",
                            "description": "Docker image to use"
                        },
                        "name": {
                            "type": "string",
                            "description": "Container name"
                        },
                        "command": {
                            "type": ["string", "array"],
                            "description": "Command to run in the container"
                        },
                        "environment": {
                            "type": "object",
                            "description": "Environment variables as key-value pairs"
                        },
                        "ports": {
                            "type": "object",
                            "description": "Port bindings (e.g., {'80/tcp': 8080})"
                        },
                        "volumes": {
                            "type": "object",
                            "description": "Volume bindings (e.g., {'/host/path': {'bind': '/container/path', 'mode': 'rw'}})"
                        },
                        "detach": {
                            "type": "boolean",
                            "description": "Run container in background",
                            "default": True
                        },
                        "auto_remove": {
                            "type": "boolean",
                            "description": "Automatically remove container when it exits",
                            "default": False
                        }
                    },
                    "required": ["image"]
                }
            ),
            types.Tool(
                name="docker_start_container",
                description="Start a stopped container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID or name"
                        }
                    },
                    "required": ["container_id"]
                }
            ),
            types.Tool(
                name="docker_stop_container",
                description="Stop a running container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID or name"
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds before killing the container",
                            "default": 10
                        }
                    },
                    "required": ["container_id"]
                }
            ),
            types.Tool(
                name="docker_remove_container",
                description="Remove a container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID or name"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force removal of running container",
                            "default": False
                        },
                        "volumes": {
                            "type": "boolean",
                            "description": "Remove associated volumes",
                            "default": False
                        }
                    },
                    "required": ["container_id"]
                }
            ),
            types.Tool(
                name="docker_inspect_container",
                description="Get detailed information about a container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID or name"
                        }
                    },
                    "required": ["container_id"]
                }
            ),
            types.Tool(
                name="docker_container_logs",
                description="Get logs from a container",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "container_id": {
                            "type": "string",
                            "description": "Container ID or name"
                        },
                        "tail": {
                            "type": "integer",
                            "description": "Number of lines to show from the end of the logs",
                            "default": 100
                        },
                        "timestamps": {
                            "type": "boolean",
                            "description": "Show timestamps",
                            "default": True
                        }
                    },
                    "required": ["container_id"]
                }
            ),
            types.Tool(
                name="docker_list_images",
                description="List Docker images",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filters": {
                            "type": "object",
                            "description": "Filters to apply",
                            "properties": {
                                "dangling": {"type": "boolean"},
                                "label": {"type": "string"}
                            }
                        }
                    }
                }
            ),
            types.Tool(
                name="docker_pull_image",
                description="Pull an image from a registry",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "repository": {
                            "type": "string",
                            "description": "Image repository (e.g., 'ubuntu:latest')"
                        }
                    },
                    "required": ["repository"]
                }
            ),
            types.Tool(
                name="docker_build_image",
                description="Build a Docker image from a Dockerfile",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the build context"
                        },
                        "tag": {
                            "type": "string",
                            "description": "Tag for the built image"
                        },
                        "dockerfile": {
                            "type": "string",
                            "description": "Path to Dockerfile relative to build context",
                            "default": "Dockerfile"
                        },
                        "buildargs": {
                            "type": "object",
                            "description": "Build arguments as key-value pairs"
                        },
                        "nocache": {
                            "type": "boolean",
                            "description": "Do not use cache when building",
                            "default": False
                        }
                    },
                    "required": ["path", "tag"]
                }
            ),
            types.Tool(
                name="docker_remove_image",
                description="Remove a Docker image",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "image_id": {
                            "type": "string",
                            "description": "Image ID or tag"
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force removal",
                            "default": False
                        }
                    },
                    "required": ["image_id"]
                }
            ),
            types.Tool(
                name="docker_system_info",
                description="Get Docker system information",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="docker_system_prune",
                description="Remove unused Docker data",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "containers": {
                            "type": "boolean",
                            "description": "Remove stopped containers",
                            "default": True
                        },
                        "images": {
                            "type": "boolean",
                            "description": "Remove unused images",
                            "default": True
                        },
                        "volumes": {
                            "type": "boolean",
                            "description": "Remove unused volumes",
                            "default": False
                        },
                        "networks": {
                            "type": "boolean",
                            "description": "Remove unused networks",
                            "default": True
                        }
                    }
                }
            ),
            types.Tool(
                name="docker_health_check",
                description="Check Docker MCP server and Docker daemon health",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            )
        ]

    async def _handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
        """Handle tool execution"""
        try:
            # Initialize Docker client if needed
            if not self._initialized:
                self._initialize_docker_client()

            # Route to appropriate handler
            handlers = {
                "docker_list_containers": self._list_containers,
                "docker_create_container": self._create_container,
                "docker_start_container": self._start_container,
                "docker_stop_container": self._stop_container,
                "docker_remove_container": self._remove_container,
                "docker_inspect_container": self._inspect_container,
                "docker_container_logs": self._container_logs,
                "docker_list_images": self._list_images,
                "docker_pull_image": self._pull_image,
                "docker_build_image": self._build_image,
                "docker_remove_image": self._remove_image,
                "docker_system_info": self._system_info,
                "docker_system_prune": self._system_prune,
                "docker_health_check": self._health_check
            }

            handler = handlers.get(name)
            if not handler:
                result = {"error": f"Unknown tool: {name}"}
            else:
                result = await handler(arguments)

            return [types.TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]

        except Exception as e:
            return [types.TextContent(
                type="text",
                text=json.dumps({
                    "error": str(e),
                    "tool": name,
                    "status": "failed"
                }, indent=2)
            )]

    async def _list_containers(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List Docker containers"""
        containers = self.docker_client.containers.list(
            all=args.get("all", False),
            filters=args.get("filters", {}),
            limit=args.get("limit", -1)
        )

        container_list = []
        for container in containers:
            container_list.append({
                "id": container.short_id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "status": container.status,
                "created": container.attrs['Created'],
                "ports": container.attrs.get('NetworkSettings', {}).get('Ports', {}),
                "labels": container.labels
            })

        return {
            "status": "success",
            "containers": container_list,
            "count": len(container_list)
        }

    async def _create_container(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new container"""
        # Prepare container configuration
        config = {
            "image": args["image"],
            "name": args.get("name"),
            "command": args.get("command"),
            "environment": args.get("environment", {}),
            "detach": args.get("detach", True),
            "auto_remove": args.get("auto_remove", False)
        }

        # Handle port bindings
        if "ports" in args:
            config["ports"] = args["ports"]

        # Handle volume bindings
        if "volumes" in args:
            config["volumes"] = args["volumes"]

        # Create container
        container = self.docker_client.containers.create(**config)

        return {
            "status": "success",
            "container": {
                "id": container.short_id,
                "name": container.name,
                "status": "created",
                "image": args["image"]
            }
        }

    async def _start_container(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Start a container"""
        container = self.docker_client.containers.get(args["container_id"])
        container.start()

        return {
            "status": "success",
            "container": {
                "id": container.short_id,
                "name": container.name,
                "status": container.status
            }
        }

    async def _stop_container(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a container"""
        container = self.docker_client.containers.get(args["container_id"])
        container.stop(timeout=args.get("timeout", 10))

        return {
            "status": "success",
            "container": {
                "id": container.short_id,
                "name": container.name,
                "status": "stopped"
            }
        }

    async def _remove_container(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a container"""
        container = self.docker_client.containers.get(args["container_id"])
        container.remove(
            force=args.get("force", False),
            v=args.get("volumes", False)
        )

        return {
            "status": "success",
            "message": f"Container {args['container_id']} removed"
        }

    async def _inspect_container(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed container information"""
        container = self.docker_client.containers.get(args["container_id"])

        return {
            "status": "success",
            "container": {
                "id": container.id,
                "short_id": container.short_id,
                "name": container.name,
                "status": container.status,
                "image": container.image.tags[0] if container.image.tags else container.image.short_id,
                "created": container.attrs['Created'],
                "state": container.attrs['State'],
                "config": container.attrs['Config'],
                "network_settings": container.attrs['NetworkSettings'],
                "mounts": container.attrs.get('Mounts', [])
            }
        }

    async def _container_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get container logs"""
        container = self.docker_client.containers.get(args["container_id"])

        logs = container.logs(
            tail=args.get("tail", 100),
            timestamps=args.get("timestamps", True)
        ).decode('utf-8')

        return {
            "status": "success",
            "logs": logs,
            "container_id": container.short_id
        }

    async def _list_images(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """List Docker images"""
        images = self.docker_client.images.list(
            filters=args.get("filters", {})
        )

        image_list = []
        for image in images:
            image_list.append({
                "id": image.short_id,
                "tags": image.tags,
                "created": image.attrs['Created'],
                "size": image.attrs['Size'],
                "labels": image.labels
            })

        return {
            "status": "success",
            "images": image_list,
            "count": len(image_list)
        }

    async def _pull_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Pull an image from registry"""
        image = self.docker_client.images.pull(args["repository"])

        return {
            "status": "success",
            "image": {
                "id": image.short_id,
                "tags": image.tags,
                "size": image.attrs['Size']
            }
        }

    async def _build_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build a Docker image"""
        path = args["path"]
        tag = args["tag"]
        dockerfile = args.get("dockerfile", "Dockerfile")
        buildargs = args.get("buildargs", {})
        nocache = args.get("nocache", False)

        # Build image
        image, build_logs = self.docker_client.images.build(
            path=path,
            tag=tag,
            dockerfile=dockerfile,
            buildargs=buildargs,
            nocache=nocache,
            rm=True
        )

        # Parse build logs
        log_lines = []
        for log in build_logs:
            if 'stream' in log:
                log_lines.append(log['stream'].strip())

        return {
            "status": "success",
            "image": {
                "id": image.short_id,
                "tag": tag,
                "size": image.attrs['Size']
            },
            "build_logs": log_lines[-20:]  # Last 20 lines of build output
        }

    async def _remove_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Remove a Docker image"""
        self.docker_client.images.remove(
            image=args["image_id"],
            force=args.get("force", False)
        )

        return {
            "status": "success",
            "message": f"Image {args['image_id']} removed"
        }

    async def _system_info(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Get Docker system information"""
        info = self.docker_client.info()
        version = self.docker_client.version()

        return {
            "status": "success",
            "docker_version": version['Version'],
            "api_version": version['ApiVersion'],
            "os": info['OperatingSystem'],
            "kernel": info['KernelVersion'],
            "containers": {
                "total": info['Containers'],
                "running": info['ContainersRunning'],
                "paused": info['ContainersPaused'],
                "stopped": info['ContainersStopped']
            },
            "images": info['Images'],
            "driver": info['Driver'],
            "memory_limit": info['MemTotal'],
            "cpu_count": info['NCPU']
        }

    async def _system_prune(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up Docker system"""
        results = {}

        if args.get("containers", True):
            containers_result = self.docker_client.containers.prune()
            results["containers"] = {
                "deleted": containers_result.get('ContainersDeleted', []),
                "space_reclaimed": containers_result.get('SpaceReclaimed', 0)
            }

        if args.get("images", True):
            images_result = self.docker_client.images.prune()
            results["images"] = {
                "deleted": images_result.get('ImagesDeleted', []),
                "space_reclaimed": images_result.get('SpaceReclaimed', 0)
            }

        if args.get("volumes", False):
            volumes_result = self.docker_client.volumes.prune()
            results["volumes"] = {
                "deleted": volumes_result.get('VolumesDeleted', []),
                "space_reclaimed": volumes_result.get('SpaceReclaimed', 0)
            }

        if args.get("networks", True):
            networks_result = self.docker_client.networks.prune()
            results["networks"] = {
                "deleted": networks_result.get('NetworksDeleted', [])
            }

        total_space = sum(r.get('space_reclaimed', 0) for r in results.values())

        return {
            "status": "success",
            "results": results,
            "total_space_reclaimed": total_space
        }

    async def _health_check(self) -> Dict[str, Any]:
        """Check Docker health"""
        try:
            # Ping Docker daemon
            self.docker_client.ping()

            # Get basic info
            info = self.docker_client.info()

            return {
                "status": "healthy",
                "service": "docker-mcp",
                "docker_status": "connected",
                "docker_version": self.docker_client.version()['Version'],
                "containers_running": info['ContainersRunning'],
                "images_count": info['Images'],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "service": "docker-mcp",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

    async def run(self):
        """Run the MCP server"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="docker-mcp",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """Main entry point"""
    server = DockerMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
