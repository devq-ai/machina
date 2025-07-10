#!/usr/bin/env python3
"""
GCP MCP Server - Production Implementation
Provides Google Cloud Platform operations including Compute Engine, Cloud Storage, and BigQuery.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pathlib import Path

try:
    from google.cloud import compute_v1
    from google.cloud import storage
    from google.cloud import bigquery
    from google.oauth2 import service_account
    from google.api_core import exceptions
except ImportError:
    print("Installing required dependencies...")
    import subprocess
    subprocess.check_call(["pip", "install", "google-cloud-compute", "google-cloud-storage", "google-cloud-bigquery"])
    from google.cloud import compute_v1
    from google.cloud import storage
    from google.cloud import bigquery
    from google.oauth2 import service_account

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MCP Protocol Constants
JSONRPC_VERSION = "2.0"
MCP_VERSION = "2024-11-05"


class MCPError:
    """Standard MCP error codes"""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603


class GCPClient:
    """Google Cloud Platform client wrapper"""

    def __init__(self, project_id: Optional[str] = None, credentials_path: Optional[str] = None):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        self.credentials_path = credentials_path or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        # Initialize credentials
        if self.credentials_path:
            self.credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path
            )
        else:
            self.credentials = None

        # Initialize clients
        self.compute_client = None
        self.storage_client = None
        self.bigquery_client = None

    def initialize_clients(self):
        """Initialize GCP service clients"""
        try:
            # Compute Engine
            self.compute_client = compute_v1.InstancesClient(credentials=self.credentials)
            self.zones_client = compute_v1.ZonesClient(credentials=self.credentials)
            self.machine_types_client = compute_v1.MachineTypesClient(credentials=self.credentials)

            # Cloud Storage
            self.storage_client = storage.Client(
                credentials=self.credentials,
                project=self.project_id
            )

            # BigQuery
            self.bigquery_client = bigquery.Client(
                credentials=self.credentials,
                project=self.project_id
            )

            logger.info("GCP clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize GCP clients: {e}")
            raise

    # Compute Engine methods
    async def list_instances(self, zone: Optional[str] = None) -> List[Dict[str, Any]]:
        """List Compute Engine instances"""
        try:
            instances = []

            if zone:
                # List instances in specific zone
                request = compute_v1.ListInstancesRequest(
                    project=self.project_id,
                    zone=zone
                )
                response = self.compute_client.list(request=request)

                for instance in response:
                    instances.append({
                        "name": instance.name,
                        "id": instance.id,
                        "machineType": instance.machine_type.split('/')[-1],
                        "status": instance.status,
                        "zone": zone,
                        "creationTimestamp": instance.creation_timestamp,
                        "networkInterfaces": [
                            {
                                "networkIP": ni.network_i_p,
                                "accessConfigs": [
                                    {"natIP": ac.nat_i_p} for ac in ni.access_configs
                                ]
                            } for ni in instance.network_interfaces
                        ]
                    })
            else:
                # List instances across all zones
                zones_request = compute_v1.ListZonesRequest(project=self.project_id)
                zones_response = self.zones_client.list(request=zones_request)

                for zone_obj in zones_response:
                    zone_name = zone_obj.name
                    request = compute_v1.ListInstancesRequest(
                        project=self.project_id,
                        zone=zone_name
                    )
                    response = self.compute_client.list(request=request)

                    for instance in response:
                        instances.append({
                            "name": instance.name,
                            "id": instance.id,
                            "machineType": instance.machine_type.split('/')[-1],
                            "status": instance.status,
                            "zone": zone_name,
                            "creationTimestamp": instance.creation_timestamp
                        })

            return instances
        except Exception as e:
            logger.error(f"Error listing instances: {e}")
            raise

    async def create_instance(self, name: str, zone: str, machine_type: str,
                            source_image: str = "projects/debian-cloud/global/images/family/debian-11",
                            disk_size_gb: int = 10) -> Dict[str, Any]:
        """Create a new Compute Engine instance"""
        try:
            # Instance configuration
            instance = compute_v1.Instance()
            instance.name = name
            instance.machine_type = f"zones/{zone}/machineTypes/{machine_type}"

            # Boot disk
            disk = compute_v1.AttachedDisk()
            disk.boot = True
            disk.auto_delete = True
            disk.initialize_params = compute_v1.AttachedDiskInitializeParams()
            disk.initialize_params.source_image = source_image
            disk.initialize_params.disk_size_gb = disk_size_gb
            instance.disks = [disk]

            # Network interface
            network_interface = compute_v1.NetworkInterface()
            network_interface.name = "global/networks/default"

            # External IP
            access_config = compute_v1.AccessConfig()
            access_config.type_ = "ONE_TO_ONE_NAT"
            access_config.name = "External NAT"
            network_interface.access_configs = [access_config]

            instance.network_interfaces = [network_interface]

            # Create instance
            request = compute_v1.InsertInstanceRequest()
            request.project = self.project_id
            request.zone = zone
            request.instance_resource = instance

            operation = self.compute_client.insert(request=request)

            return {
                "operation": operation.name,
                "status": "creating",
                "instance_name": name,
                "zone": zone
            }
        except Exception as e:
            logger.error(f"Error creating instance: {e}")
            raise

    async def stop_instance(self, name: str, zone: str) -> Dict[str, Any]:
        """Stop a Compute Engine instance"""
        try:
            request = compute_v1.StopInstanceRequest()
            request.project = self.project_id
            request.zone = zone
            request.instance = name

            operation = self.compute_client.stop(request=request)

            return {
                "operation": operation.name,
                "status": "stopping",
                "instance_name": name,
                "zone": zone
            }
        except Exception as e:
            logger.error(f"Error stopping instance: {e}")
            raise

    async def start_instance(self, name: str, zone: str) -> Dict[str, Any]:
        """Start a Compute Engine instance"""
        try:
            request = compute_v1.StartInstanceRequest()
            request.project = self.project_id
            request.zone = zone
            request.instance = name

            operation = self.compute_client.start(request=request)

            return {
                "operation": operation.name,
                "status": "starting",
                "instance_name": name,
                "zone": zone
            }
        except Exception as e:
            logger.error(f"Error starting instance: {e}")
            raise

    async def delete_instance(self, name: str, zone: str) -> Dict[str, Any]:
        """Delete a Compute Engine instance"""
        try:
            request = compute_v1.DeleteInstanceRequest()
            request.project = self.project_id
            request.zone = zone
            request.instance = name

            operation = self.compute_client.delete(request=request)

            return {
                "operation": operation.name,
                "status": "deleting",
                "instance_name": name,
                "zone": zone
            }
        except Exception as e:
            logger.error(f"Error deleting instance: {e}")
            raise

    # Cloud Storage methods
    async def list_buckets(self) -> List[Dict[str, Any]]:
        """List Cloud Storage buckets"""
        try:
            buckets = []
            for bucket in self.storage_client.list_buckets():
                buckets.append({
                    "name": bucket.name,
                    "location": bucket.location,
                    "storageClass": bucket.storage_class,
                    "timeCreated": bucket.time_created.isoformat() if bucket.time_created else None,
                    "updated": bucket.updated.isoformat() if bucket.updated else None
                })
            return buckets
        except Exception as e:
            logger.error(f"Error listing buckets: {e}")
            raise

    async def create_bucket(self, bucket_name: str, location: str = "US",
                          storage_class: str = "STANDARD") -> Dict[str, Any]:
        """Create a new Cloud Storage bucket"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            bucket.location = location
            bucket.storage_class = storage_class

            new_bucket = self.storage_client.create_bucket(bucket)

            return {
                "name": new_bucket.name,
                "location": new_bucket.location,
                "storageClass": new_bucket.storage_class,
                "created": True
            }
        except Exception as e:
            logger.error(f"Error creating bucket: {e}")
            raise

    async def upload_file(self, bucket_name: str, source_file_path: str,
                         destination_blob_name: Optional[str] = None) -> Dict[str, Any]:
        """Upload a file to Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(bucket_name)

            if not destination_blob_name:
                destination_blob_name = Path(source_file_path).name

            blob = bucket.blob(destination_blob_name)

            # Upload file
            with open(source_file_path, "rb") as f:
                blob.upload_from_file(f)

            return {
                "bucket": bucket_name,
                "name": destination_blob_name,
                "size": blob.size,
                "contentType": blob.content_type,
                "uploaded": True
            }
        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            raise

    async def list_blobs(self, bucket_name: str, prefix: Optional[str] = None,
                        delimiter: Optional[str] = None) -> List[Dict[str, Any]]:
        """List objects in a Cloud Storage bucket"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blobs = []

            for blob in bucket.list_blobs(prefix=prefix, delimiter=delimiter):
                blobs.append({
                    "name": blob.name,
                    "size": blob.size,
                    "contentType": blob.content_type,
                    "timeCreated": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None
                })

            return blobs
        except Exception as e:
            logger.error(f"Error listing blobs: {e}")
            raise

    async def delete_blob(self, bucket_name: str, blob_name: str) -> Dict[str, Any]:
        """Delete an object from Cloud Storage"""
        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()

            return {
                "bucket": bucket_name,
                "name": blob_name,
                "deleted": True
            }
        except Exception as e:
            logger.error(f"Error deleting blob: {e}")
            raise

    # BigQuery methods
    async def list_datasets(self) -> List[Dict[str, Any]]:
        """List BigQuery datasets"""
        try:
            datasets = []
            for dataset in self.bigquery_client.list_datasets():
                dataset_ref = dataset.reference
                dataset_obj = self.bigquery_client.get_dataset(dataset_ref)

                datasets.append({
                    "datasetId": dataset_obj.dataset_id,
                    "location": dataset_obj.location,
                    "created": dataset_obj.created.isoformat() if dataset_obj.created else None,
                    "modified": dataset_obj.modified.isoformat() if dataset_obj.modified else None,
                    "description": dataset_obj.description
                })

            return datasets
        except Exception as e:
            logger.error(f"Error listing datasets: {e}")
            raise

    async def create_dataset(self, dataset_id: str, location: str = "US",
                           description: Optional[str] = None) -> Dict[str, Any]:
        """Create a new BigQuery dataset"""
        try:
            dataset = bigquery.Dataset(f"{self.project_id}.{dataset_id}")
            dataset.location = location

            if description:
                dataset.description = description

            dataset = self.bigquery_client.create_dataset(dataset)

            return {
                "datasetId": dataset.dataset_id,
                "location": dataset.location,
                "created": dataset.created.isoformat() if dataset.created else None,
                "description": dataset.description
            }
        except Exception as e:
            logger.error(f"Error creating dataset: {e}")
            raise

    async def query_bigquery(self, query: str, use_legacy_sql: bool = False) -> Dict[str, Any]:
        """Execute a BigQuery query"""
        try:
            job_config = bigquery.QueryJobConfig(use_legacy_sql=use_legacy_sql)

            # Run the query
            query_job = self.bigquery_client.query(query, job_config=job_config)

            # Wait for the query to complete
            results = query_job.result()

            # Process results
            rows = []
            for row in results:
                rows.append(dict(row))

            return {
                "rows": rows,
                "totalRows": results.total_rows,
                "schema": [
                    {
                        "name": field.name,
                        "type": field.field_type,
                        "mode": field.mode
                    } for field in results.schema
                ],
                "jobId": query_job.job_id,
                "totalBytesProcessed": query_job.total_bytes_processed
            }
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            raise

    async def list_tables(self, dataset_id: str) -> List[Dict[str, Any]]:
        """List tables in a BigQuery dataset"""
        try:
            dataset_ref = self.bigquery_client.dataset(dataset_id)
            tables = []

            for table in self.bigquery_client.list_tables(dataset_ref):
                table_ref = dataset_ref.table(table.table_id)
                table_obj = self.bigquery_client.get_table(table_ref)

                tables.append({
                    "tableId": table_obj.table_id,
                    "created": table_obj.created.isoformat() if table_obj.created else None,
                    "modified": table_obj.modified.isoformat() if table_obj.modified else None,
                    "numRows": table_obj.num_rows,
                    "numBytes": table_obj.num_bytes,
                    "description": table_obj.description
                })

            return tables
        except Exception as e:
            logger.error(f"Error listing tables: {e}")
            raise


class GCPMCPServer:
    """GCP MCP Server implementation"""

    def __init__(self):
        self.client: Optional[GCPClient] = None
        self.server_info = {
            "name": "gcp-mcp",
            "version": "1.0.0",
            "description": "Google Cloud Platform operations MCP server",
            "author": "DevQ.ai Team"
        }

    async def initialize(self):
        """Initialize the server"""
        self.client = GCPClient()
        try:
            self.client.initialize_clients()
            logger.info("GCP MCP Server initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GCP clients: {e}")
            self.client = None

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            # Compute Engine tools
            {
                "name": "list_instances",
                "description": "List Compute Engine instances",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "zone": {"type": "string", "description": "Specific zone (optional)"}
                    }
                }
            },
            {
                "name": "create_instance",
                "description": "Create a new Compute Engine instance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Instance name"},
                        "zone": {"type": "string", "description": "Zone (e.g., us-central1-a)"},
                        "machine_type": {"type": "string", "description": "Machine type (e.g., e2-micro)"},
                        "source_image": {"type": "string", "description": "Source image"},
                        "disk_size_gb": {"type": "integer", "description": "Boot disk size in GB"}
                    },
                    "required": ["name", "zone", "machine_type"]
                }
            },
            {
                "name": "stop_instance",
                "description": "Stop a Compute Engine instance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Instance name"},
                        "zone": {"type": "string", "description": "Zone"}
                    },
                    "required": ["name", "zone"]
                }
            },
            {
                "name": "start_instance",
                "description": "Start a Compute Engine instance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Instance name"},
                        "zone": {"type": "string", "description": "Zone"}
                    },
                    "required": ["name", "zone"]
                }
            },
            {
                "name": "delete_instance",
                "description": "Delete a Compute Engine instance",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Instance name"},
                        "zone": {"type": "string", "description": "Zone"}
                    },
                    "required": ["name", "zone"]
                }
            },
            # Cloud Storage tools
            {
                "name": "list_buckets",
                "description": "List Cloud Storage buckets",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "create_bucket",
                "description": "Create a new Cloud Storage bucket",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bucket_name": {"type": "string", "description": "Bucket name"},
                        "location": {"type": "string", "description": "Location (default: US)"},
                        "storage_class": {"type": "string", "description": "Storage class (default: STANDARD)"}
                    },
                    "required": ["bucket_name"]
                }
            },
            {
                "name": "list_blobs",
                "description": "List objects in a Cloud Storage bucket",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bucket_name": {"type": "string", "description": "Bucket name"},
                        "prefix": {"type": "string", "description": "Prefix filter"},
                        "delimiter": {"type": "string", "description": "Delimiter for grouping"}
                    },
                    "required": ["bucket_name"]
                }
            },
            {
                "name": "upload_file",
                "description": "Upload a file to Cloud Storage",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bucket_name": {"type": "string", "description": "Bucket name"},
                        "source_file_path": {"type": "string", "description": "Local file path"},
                        "destination_blob_name": {"type": "string", "description": "Destination name in bucket"}
                    },
                    "required": ["bucket_name", "source_file_path"]
                }
            },
            {
                "name": "delete_blob",
                "description": "Delete an object from Cloud Storage",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "bucket_name": {"type": "string", "description": "Bucket name"},
                        "blob_name": {"type": "string", "description": "Object name"}
                    },
                    "required": ["bucket_name", "blob_name"]
                }
            },
            # BigQuery tools
            {
                "name": "list_datasets",
                "description": "List BigQuery datasets",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "create_dataset",
                "description": "Create a new BigQuery dataset",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dataset_id": {"type": "string", "description": "Dataset ID"},
                        "location": {"type": "string", "description": "Location (default: US)"},
                        "description": {"type": "string", "description": "Dataset description"}
                    },
                    "required": ["dataset_id"]
                }
            },
            {
                "name": "query_bigquery",
                "description": "Execute a BigQuery SQL query",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SQL query"},
                        "use_legacy_sql": {"type": "boolean", "description": "Use legacy SQL syntax"}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "list_tables",
                "description": "List tables in a BigQuery dataset",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dataset_id": {"type": "string", "description": "Dataset ID"}
                    },
                    "required": ["dataset_id"]
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        if not self.client:
            return {"error": "GCP client not initialized. Please provide credentials."}

        try:
            # Compute Engine tools
            if tool_name == "list_instances":
                instances = await self.client.list_instances(**arguments)
                return {
                    "instances": instances,
                    "count": len(instances)
                }
            elif tool_name == "create_instance":
                result = await self.client.create_instance(**arguments)
                return result
            elif tool_name == "stop_instance":
                result = await self.client.stop_instance(**arguments)
                return result
            elif tool_name == "start_instance":
                result = await self.client.start_instance(**arguments)
                return result
            elif tool_name == "delete_instance":
                result = await self.client.delete_instance(**arguments)
                return result

            # Cloud Storage tools
            elif tool_name == "list_buckets":
                buckets = await self.client.list_buckets()
                return {
                    "buckets": buckets,
                    "count": len(buckets)
                }
            elif tool_name == "create_bucket":
                result = await self.client.create_bucket(**arguments)
                return result
            elif tool_name == "list_blobs":
                blobs = await self.client.list_blobs(**arguments)
                return {
                    "blobs": blobs,
                    "count": len(blobs)
                }
            elif tool_name == "upload_file":
                result = await self.client.upload_file(**arguments)
                return result
            elif tool_name == "delete_blob":
                result = await self.client.delete_blob(**arguments)
                return result

            # BigQuery tools
            elif tool_name == "list_datasets":
                datasets = await self.client.list_datasets()
                return {
                    "datasets": datasets,
                    "count": len(datasets)
                }
            elif tool_name == "create_dataset":
                result = await self.client.create_dataset(**arguments)
                return result
            elif tool_name == "query_bigquery":
                result = await self.client.query_bigquery(**arguments)
                return result
            elif tool_name == "list_tables":
                tables = await self.client.list_tables(**arguments)
                return {
                    "tables": tables,
                    "count": len(tables)
                }
            else:
                raise ValueError(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return {"error": str(e)}

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle JSON-RPC request"""
        request_id = request.get("id")
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "initialize":
                await self.initialize()
                result = {
                    "protocolVersion": MCP_VERSION,
                    "serverInfo": self.server_info,
                    "capabilities": {
                        "tools": True,
                        "resources": False,
                        "prompts": False,
                        "logging": False
                    },
                    "instructions": "GCP MCP server for Google Cloud Platform operations"
                }
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
            elif method == "health":
                result = {
                    "status": "healthy" if self.client else "no_auth",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "authenticated": self.client is not None,
                    "project_id": self.client.project_id if self.client else None
                }
            else:
                return {
                    "jsonrpc": JSONRPC_VERSION,
                    "id": request_id,
                    "error": {
                        "code": MCPError.METHOD_NOT_FOUND,
                        "message": f"Method not found: {method}"
                    }
                }

            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "result": result
            }

        except Exception as e:
            logger.error(f"Request handling error: {e}")
            return {
                "jsonrpc": JSONRPC_VERSION,
                "id": request_id,
                "error": {
                    "code": MCPError.INTERNAL_ERROR,
                    "message": str(e)
                }
            }

    async def run_stdio(self):
        """Run the server in stdio mode"""
        logger.info("Starting GCP MCP Server in stdio mode")

        try:
            while True:
                # Read request from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, input
                )

                if not line:
                    continue

                try:
                    request = json.loads(line)
                    response = await self.handle_request(request)

                    # Write response to stdout
                    print(json.dumps(response))

                except json.JSONDecodeError as e:
                    error_response = {
                        "jsonrpc": JSONRPC_VERSION,
                        "id": None,
                        "error": {
                            "code": MCPError.PARSE_ERROR,
                            "message": f"Parse error: {e}"
                        }
                    }
                    print(json.dumps(error_response))

        except KeyboardInterrupt:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")


async def main():
    """Main entry point"""
    server = GCPMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
