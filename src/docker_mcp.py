#!/usr/bin/env python
"""
Docker MCP Server
FastMCP server for Docker container management with stdio transport support.
Optimized for Docker Desktop compatibility.
"""
import asyncio
import os
import subprocess
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='docker-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("docker-mcp")

class DockerManager:
    """Docker operations manager with stdio transport."""
    
    def __init__(self):
        self.docker_socket = os.getenv('DOCKER_SOCKET_PATH', '/var/run/docker.sock')
        self.docker_host = os.getenv('DOCKER_HOST', 'unix:///var/run/docker.sock')
    
    async def run_docker_command(self, cmd: List[str]) -> Dict[str, Any]:
        """Run docker command and return structured output."""
        try:
            # Use Docker CLI with stdio transport for Docker Desktop compatibility
            full_cmd = ['docker'] + cmd
            
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            result = {
                "command": " ".join(full_cmd),
                "exit_code": process.returncode,
                "stdout": stdout.decode('utf-8') if stdout else "",
                "stderr": stderr.decode('utf-8') if stderr else "",
                "success": process.returncode == 0
            }
            
            return result
            
        except Exception as e:
            return {
                "command": " ".join(cmd),
                "exit_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "error": str(e)
            }

docker_manager = DockerManager()

@app.tool()
@logfire.instrument("docker_health_check")
async def docker_health_check() -> Dict[str, Any]:
    """Check Docker daemon health and connectivity."""
    # logfire.info("Docker health check requested")
    
    try:
        result = await docker_manager.run_docker_command(['version', '--format', 'json'])
        
        if result["success"]:
            version_info = json.loads(result["stdout"]) if result["stdout"] else {}
            
            health_status = {
                "status": "healthy",
                "docker_version": version_info.get("Client", {}).get("Version", "unknown"),
                "server_version": version_info.get("Server", {}).get("Version", "unknown"),
                "api_version": version_info.get("Client", {}).get("ApiVersion", "unknown"),
                "transport": "stdio",
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Docker health check passed", health_status=health_status)
            return health_status
        else:
            raise RuntimeError(f"Docker health check failed: {result['stderr']}")
            
    except Exception as e:
        # logfire.error("Docker health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_containers")
async def list_containers(all_containers: bool = False) -> List[Dict[str, Any]]:
    """List Docker containers."""
    # logfire.info("Listing containers", all_containers=all_containers)
    
    try:
        cmd = ['ps', '--format', 'json']
        if all_containers:
            cmd.append('-a')
        
        result = await docker_manager.run_docker_command(cmd)
        
        if not result["success"]:
            raise RuntimeError(f"Failed to list containers: {result['stderr']}")
        
        # Parse JSON output
        containers = []
        if result["stdout"].strip():
            for line in result["stdout"].strip().split('\n'):
                try:
                    container = json.loads(line)
                    containers.append({
                        "id": container.get("ID", ""),
                        "name": container.get("Names", ""),
                        "image": container.get("Image", ""),
                        "status": container.get("Status", ""),
                        "ports": container.get("Ports", ""),
                        "created": container.get("CreatedAt", "")
                    })
                except json.JSONDecodeError:
                    continue
        
        # logfire.info("Containers listed", count=len(containers), all_containers=all_containers)
        return containers
        
    except Exception as e:
        # logfire.error("Failed to list containers", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("container_info")
async def container_info(container_id: str) -> Dict[str, Any]:
    """Get detailed information about a specific container."""
    # logfire.info("Getting container info", container_id=container_id)
    
    try:
        result = await docker_manager.run_docker_command(['inspect', container_id])
        
        if not result["success"]:
            raise RuntimeError(f"Failed to inspect container: {result['stderr']}")
        
        container_data = json.loads(result["stdout"])[0]
        
        info = {
            "id": container_data.get("Id", ""),
            "name": container_data.get("Name", "").lstrip("/"),
            "image": container_data.get("Config", {}).get("Image", ""),
            "state": container_data.get("State", {}),
            "network_settings": container_data.get("NetworkSettings", {}),
            "mounts": container_data.get("Mounts", []),
            "created": container_data.get("Created", ""),
            "config": container_data.get("Config", {})
        }
        
        # logfire.info("Container info retrieved", container_id=container_id, name=info.get("name"))
        return info
        
    except Exception as e:
        # logfire.error("Failed to get container info", container_id=container_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("start_container")
async def start_container(container_id: str) -> Dict[str, Any]:
    """Start a Docker container."""
    # logfire.info("Starting container", container_id=container_id)
    
    try:
        result = await docker_manager.run_docker_command(['start', container_id])
        
        if result["success"]:
            # logfire.info("Container started successfully", container_id=container_id)
            pass
            return {
                "status": "started",
                "container_id": container_id,
                "message": f"Container {container_id} started successfully"
            }
        else:
            raise RuntimeError(f"Failed to start container: {result['stderr']}")
            
    except Exception as e:
        # logfire.error("Failed to start container", container_id=container_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("stop_container")
async def stop_container(container_id: str, timeout: int = 10) -> Dict[str, Any]:
    """Stop a Docker container."""
    # logfire.info("Stopping container", container_id=container_id, timeout=timeout)
    
    try:
        cmd = ['stop', '-t', str(timeout), container_id]
        result = await docker_manager.run_docker_command(cmd)
        
        if result["success"]:
            # logfire.info("Container stopped successfully", container_id=container_id)
            pass
            return {
                "status": "stopped",
                "container_id": container_id,
                "message": f"Container {container_id} stopped successfully"
            }
        else:
            raise RuntimeError(f"Failed to stop container: {result['stderr']}")
            
    except Exception as e:
        # logfire.error("Failed to stop container", container_id=container_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_images")
async def list_images() -> List[Dict[str, Any]]:
    """List Docker images."""
    # logfire.info("Listing Docker images")
    
    try:
        result = await docker_manager.run_docker_command(['images', '--format', 'json'])
        
        if not result["success"]:
            raise RuntimeError(f"Failed to list images: {result['stderr']}")
        
        images = []
        if result["stdout"].strip():
            for line in result["stdout"].strip().split('\n'):
                try:
                    image = json.loads(line)
                    images.append({
                        "id": image.get("ID", ""),
                        "repository": image.get("Repository", ""),
                        "tag": image.get("Tag", ""),
                        "size": image.get("Size", ""),
                        "created": image.get("CreatedAt", "")
                    })
                except json.JSONDecodeError:
                    continue
        
        # logfire.info("Images listed", count=len(images))
        return images
        
    except Exception as e:
        # logfire.error("Failed to list images", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("container_logs")
async def container_logs(container_id: str, lines: int = 100) -> str:
    """Get logs from a Docker container."""
    # logfire.info("Getting container logs", container_id=container_id, lines=lines)
    
    try:
        cmd = ['logs', '--tail', str(lines), container_id]
        result = await docker_manager.run_docker_command(cmd)
        
        if result["success"]:
            logs = result["stdout"] + result["stderr"]  # Combine stdout and stderr
            # logfire.info("Container logs retrieved", 
            #             container_id=container_id, 
            #             lines_requested=lines,
            #             log_length=len(logs))
            return logs
        else:
            raise RuntimeError(f"Failed to get container logs: {result['stderr']}")
            
    except Exception as e:
        # logfire.error("Failed to get container logs", container_id=container_id, error=str(e))
        pass
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("Docker MCP server starting up")
    
    # Test Docker connectivity on startup
    try:
        await docker_health_check()
        # logfire.info("Docker connectivity verified on startup")
    except Exception as e:
        # logfire.warning("Docker connectivity test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("Docker MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting Docker MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())