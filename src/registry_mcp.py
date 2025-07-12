#!/usr/bin/env python
"""
Registry MCP Server
FastMCP server for MCP server registry, discovery, and management.
Provides server registration, health monitoring, and configuration management.
"""
import asyncio
import os
import json
import yaml
from typing import Any, Dict, List, Optional
from datetime import datetime
from pathlib import Path

import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='registry-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("registry-mcp")

class RegistryManager:
    """MCP server registry and discovery manager."""
    
    def __init__(self):
        self.registry_path = os.getenv('REGISTRY_PATH', '/Users/dionedge/devqai/machina')
        self.master_registry_file = None
        self.discover_master_registry()
    
    def discover_master_registry(self):
        """Find the latest master registry file."""
        registry_dir = Path(self.registry_path)
        
        # Look for master-mcp-server_*.yaml files
        registry_files = list(registry_dir.glob('master-mcp-server_*.yaml'))
        
        if registry_files:
            # Get the most recent file
            self.master_registry_file = max(registry_files, key=lambda f: f.stat().st_mtime)
            # logfire.info("Master registry file discovered", 
            #             file=str(self.master_registry_file))
        else:
            # logfire.warning("No master registry file found", registry_path=self.registry_path)
            pass
    
    def load_registry_data(self) -> Dict[str, Any]:
        """Load server registry data from master file."""
        if not self.master_registry_file or not self.master_registry_file.exists():
            raise FileNotFoundError("Master registry file not found")
        
        try:
            with open(self.master_registry_file, 'r') as f:
                content = f.read()
            
            # Parse YAML content (skip the non-YAML header)
            yaml_start = content.find('```\n') + 4
            yaml_end = content.rfind('\n```')
            
            if yaml_start > 3 and yaml_end > yaml_start:
                yaml_content = content[yaml_start:yaml_end]
                
                # Parse servers manually since they're not in standard YAML format
                servers = []
                current_server = {}
                
                for line in yaml_content.split('\n'):
                    line = line.strip()
                    if line.startswith('filename:'):
                        if current_server:
                            servers.append(current_server)
                        current_server = {'filename': line.split(':', 1)[1].strip()}
                    elif ':' in line and current_server:
                        key, value = line.split(':', 1)
                        current_server[key.strip()] = value.strip()
                
                if current_server:
                    servers.append(current_server)
                
                return {
                    "registry_file": str(self.master_registry_file),
                    "last_updated": datetime.fromtimestamp(
                        self.master_registry_file.stat().st_mtime
                    ).isoformat(),
                    "servers": servers
                }
            else:
                raise ValueError("Invalid registry file format")
                
        except Exception as e:
            # logfire.error("Failed to load registry data", error=str(e))
            pass
            raise

registry_manager = RegistryManager()

@app.tool()
@logfire.instrument("registry_health_check")
async def registry_health_check() -> Dict[str, Any]:
    """Check registry health and return status."""
    # logfire.info("Registry health check requested")
    
    try:
        registry_data = registry_manager.load_registry_data()
        
        # Calculate statistics
        total_servers = len(registry_data["servers"])
        production_servers = len([s for s in registry_data["servers"] 
                                if s.get("required_in_prod") == "yes"])
        tested_servers = len([s for s in registry_data["servers"] 
                            if s.get("tested") == "yes"])
        passed_servers = len([s for s in registry_data["servers"] 
                            if s.get("passed") == "yes"])
        
        health_status = {
            "status": "healthy",
            "registry_file": registry_data["registry_file"],
            "last_updated": registry_data["last_updated"],
            "total_servers": total_servers,
            "production_servers": production_servers,
            "tested_servers": tested_servers,
            "passed_servers": passed_servers,
            "success_rate": (passed_servers / total_servers * 100) if total_servers > 0 else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Registry health check completed", health_status=health_status)
        return health_status
        
    except Exception as e:
        # logfire.error("Registry health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_servers")
async def list_servers(
    filter_by: Optional[str] = None,
    filter_value: Optional[str] = None
) -> List[Dict[str, Any]]:
    """List all registered MCP servers with optional filtering."""
    # logfire.info("Listing servers", filter_by=filter_by, filter_value=filter_value)
    
    try:
        registry_data = registry_manager.load_registry_data()
        servers = registry_data["servers"]
        
        # Apply filters if specified
        if filter_by and filter_value:
            servers = [s for s in servers if s.get(filter_by) == filter_value]
        
        # logfire.info("Servers listed", 
        #             total_count=len(registry_data["servers"]),
        #             filtered_count=len(servers),
        #             filter_by=filter_by,
        #             filter_value=filter_value)
        
        return servers
        
    except Exception as e:
        # logfire.error("Failed to list servers", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_server_info")
async def get_server_info(filename: str) -> Dict[str, Any]:
    """Get detailed information about a specific server."""
    # logfire.info("Getting server info", filename=filename)
    
    try:
        registry_data = registry_manager.load_registry_data()
        
        # Find server by filename
        server = None
        for s in registry_data["servers"]:
            if s.get("filename") == filename:
                server = s
                break
        
        if not server:
            raise ValueError(f"Server not found: {filename}")
        
        # logfire.info("Server info retrieved", filename=filename)
        return server
        
    except Exception as e:
        # logfire.error("Failed to get server info", filename=filename, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_production_servers")
async def get_production_servers() -> List[Dict[str, Any]]:
    """Get all servers marked as required in production."""
    # logfire.info("Getting production servers")
    
    try:
        registry_data = registry_manager.load_registry_data()
        
        production_servers = [
            s for s in registry_data["servers"] 
            if s.get("required_in_prod") == "yes"
        ]
        
        # logfire.info("Production servers retrieved", count=len(production_servers))
        return production_servers
        
    except Exception as e:
        # logfire.error("Failed to get production servers", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_server_status")
async def get_server_status() -> Dict[str, Any]:
    """Get comprehensive server status and statistics."""
    # logfire.info("Getting server status")
    
    try:
        registry_data = registry_manager.load_registry_data()
        servers = registry_data["servers"]
        
        # Calculate comprehensive statistics
        stats = {
            "total_servers": len(servers),
            "production_servers": len([s for s in servers if s.get("required_in_prod") == "yes"]),
            "development_servers": len([s for s in servers if s.get("required_in_prod") == "no"]),
            "tested_servers": len([s for s in servers if s.get("tested") == "yes"]),
            "passed_servers": len([s for s in servers if s.get("passed") == "yes"]),
            "failed_servers": len([s for s in servers if s.get("tested") == "yes" and s.get("passed") == "no"]),
            "untested_servers": len([s for s in servers if s.get("tested") != "yes"]),
        }
        
        # Group by framework
        frameworks = {}
        for server in servers:
            framework = server.get("framework_proposed", "unknown")
            if framework not in frameworks:
                frameworks[framework] = []
            frameworks[framework].append(server.get("filename"))
        
        # Group by purpose
        purposes = {}
        for server in servers:
            purpose = server.get("purpose", "unknown")
            if purpose not in purposes:
                purposes[purpose] = []
            purposes[purpose].append(server.get("filename"))
        
        status = {
            "registry_info": {
                "file": registry_data["registry_file"],
                "last_updated": registry_data["last_updated"]
            },
            "statistics": stats,
            "success_rate": (stats["passed_servers"] / stats["total_servers"] * 100) if stats["total_servers"] > 0 else 0,
            "frameworks": frameworks,
            "purposes": purposes,
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Server status compiled", statistics=stats)
        return status
        
    except Exception as e:
        # logfire.error("Failed to get server status", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("search_servers")
async def search_servers(query: str) -> List[Dict[str, Any]]:
    """Search servers by filename, description, or repository."""
    # logfire.info("Searching servers", query=query)
    
    try:
        registry_data = registry_manager.load_registry_data()
        
        # Search in filename, description, and repo
        matching_servers = []
        query_lower = query.lower()
        
        for server in registry_data["servers"]:
            if (query_lower in server.get("filename", "").lower() or
                query_lower in server.get("description", "").lower() or
                query_lower in server.get("repo", "").lower()):
                matching_servers.append(server)
        
        # logfire.info("Server search completed", 
        #             query=query, 
        #             results_count=len(matching_servers))
        
        return matching_servers
        
    except Exception as e:
        # logfire.error("Server search failed", query=query, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("validate_registry")
async def validate_registry() -> Dict[str, Any]:
    """Validate registry data for consistency and completeness."""
    # logfire.info("Validating registry")
    
    try:
        registry_data = registry_manager.load_registry_data()
        servers = registry_data["servers"]
        
        issues = []
        warnings = []
        
        for server in servers:
            filename = server.get("filename", "unnamed")
            
            # Check required fields
            required_fields = ["filename", "repo", "description", "framework_proposed", "purpose"]
            for field in required_fields:
                if not server.get(field):
                    issues.append(f"{filename}: Missing required field '{field}'")
            
            # Check boolean fields
            boolean_fields = ["dev_needed", "required_in_prod", "rule_test_created", "tested", "passed"]
            for field in boolean_fields:
                value = server.get(field)
                if value not in ["yes", "no", True, False]:
                    warnings.append(f"{filename}: Invalid boolean value for '{field}': {value}")
            
            # Check repo URL format
            repo = server.get("repo", "")
            if repo and not (repo.startswith("http://") or repo.startswith("https://")):
                warnings.append(f"{filename}: Repository URL may be invalid: {repo}")
        
        validation_result = {
            "status": "completed",
            "total_servers": len(servers),
            "issues_count": len(issues),
            "warnings_count": len(warnings),
            "issues": issues,
            "warnings": warnings,
            "is_valid": len(issues) == 0,
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Registry validation completed", 
        #             total_servers=len(servers),
        #             issues_count=len(issues),
        #             warnings_count=len(warnings))
        
        return validation_result
        
    except Exception as e:
        # logfire.error("Registry validation failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_framework_stats")
async def get_framework_stats() -> Dict[str, Any]:
    """Get statistics about framework distribution."""
    # logfire.info("Getting framework statistics")
    
    try:
        registry_data = registry_manager.load_registry_data()
        servers = registry_data["servers"]
        
        current_frameworks = {}
        proposed_frameworks = {}
        
        for server in servers:
            # Current framework stats
            current = server.get("framework_current", "unknown")
            current_frameworks[current] = current_frameworks.get(current, 0) + 1
            
            # Proposed framework stats
            proposed = server.get("framework_proposed", "unknown")
            proposed_frameworks[proposed] = proposed_frameworks.get(proposed, 0) + 1
        
        stats = {
            "current_frameworks": current_frameworks,
            "proposed_frameworks": proposed_frameworks,
            "migration_summary": {
                "total_servers": len(servers),
                "servers_changing_framework": len([
                    s for s in servers 
                    if s.get("framework_current") != s.get("framework_proposed")
                ])
            },
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Framework statistics compiled", stats=stats["migration_summary"])
        return stats
        
    except Exception as e:
        # logfire.error("Failed to get framework stats", error=str(e))
        pass
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("Registry MCP server starting up")
    
    # Test registry access on startup
    try:
        await registry_health_check()
        # logfire.info("Registry access verified on startup")
    except Exception as e:
        # logfire.warning("Registry access test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("Registry MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting Registry MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())