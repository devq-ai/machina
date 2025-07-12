#!/usr/bin/env python
"""
SurrealDB MCP Server
FastMCP server for SurrealDB multi-model database operations.
Provides database queries, graph operations, and vector search capabilities.
"""
import asyncio
import os
import json
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

import httpx
import logfire
from fastmcp import FastMCP
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logfire
# logfire.configure(
#     token=os.getenv('LOGFIRE_WRITE_TOKEN'),
#     service_name='surrealdb-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("surrealdb-mcp")

class SurrealDBClient:
    """SurrealDB client for multi-model database operations."""
    
    def __init__(self):
        self.url = os.getenv('SURREALDB_URL', 'ws://localhost:8000/rpc')
        self.http_url = self.url.replace('ws://', 'http://').replace('/rpc', '')
        self.username = os.getenv('SURREALDB_USERNAME', 'root')
        self.password = os.getenv('SURREALDB_PASSWORD', 'root')
        self.namespace = os.getenv('SURREALDB_NAMESPACE', 'ptolemies')
        self.database = os.getenv('SURREALDB_DATABASE', 'knowledge')
        self.token = None
    
    async def authenticate(self) -> bool:
        """Authenticate with SurrealDB and get token."""
        try:
            auth_data = {
                "user": self.username,
                "pass": self.password,
                "ns": self.namespace,
                "db": self.database
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.http_url}/signin",
                    json=auth_data,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    self.token = response.text.strip().strip('"')
                    # logfire.info("SurrealDB authentication successful")
                    return True
                else:
                    # logfire.error("SurrealDB authentication failed", 
                    #              status_code=response.status_code,
                    #              response=response.text)
                    return False
                    
        except Exception as e:
            # logfire.error("SurrealDB authentication error", error=str(e))
            pass
            return False
    
    async def execute_query(self, query: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a SurrealDB query."""
        if not self.token:
            auth_success = await self.authenticate()
            if not auth_success:
                raise RuntimeError("Failed to authenticate with SurrealDB")
        
        try:
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "NS": self.namespace,
                "DB": self.database
            }
            
            payload = {
                "method": "query",
                "params": [query, params or {}]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.http_url}/sql",
                    json=payload,
                    headers=headers,
                    timeout=30.0
                )
                
                result = {
                    "status_code": response.status_code,
                    "success": response.status_code == 200,
                    "query": query
                }
                
                try:
                    result["data"] = response.json()
                except Exception:
                    result["data"] = response.text
                
                if not result["success"]:
                    # logfire.error("SurrealDB query failed", 
                    pass
                    #              query=query,
                    #              status_code=response.status_code,
                    #              response=result["data"])
                    pass
                
                return result
                
        except Exception as e:
            # logfire.error("SurrealDB query error", query=query, error=str(e))
            pass
            raise

surrealdb_client = SurrealDBClient()

@app.tool()
@logfire.instrument("surrealdb_health_check")
async def surrealdb_health_check() -> Dict[str, Any]:
    """Check SurrealDB connectivity and database status."""
    # logfire.info("SurrealDB health check requested")
    
    try:
        # Test authentication
        auth_success = await surrealdb_client.authenticate()
        
        if not auth_success:
            raise RuntimeError("Failed to authenticate with SurrealDB")
        
        # Test basic query
        result = await surrealdb_client.execute_query("INFO FOR DB;")
        
        if result["success"]:
            health_status = {
                "status": "healthy",
                "url": surrealdb_client.url,
                "namespace": surrealdb_client.namespace,
                "database": surrealdb_client.database,
                "authenticated": True,
                "database_info": result["data"],
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise RuntimeError(f"Database query failed: {result['data']}")
        
        # logfire.info("SurrealDB health check completed", health_status=health_status)
        return health_status
        
    except Exception as e:
        # logfire.error("SurrealDB health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("execute_sql_query")
async def execute_sql_query(query: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute a custom SurrealDB SQL query."""
    # logfire.info("Executing SurrealDB query", query=query[:100])
    
    try:
        result = await surrealdb_client.execute_query(query, params)
        
        query_result = {
            "query": query,
            "params": params,
            "success": result["success"],
            "data": result["data"],
            "timestamp": datetime.now().isoformat()
        }
        
        if result["success"]:
            # Try to extract record count if possible
            if isinstance(result["data"], list) and result["data"]:
                query_result["record_count"] = len(result["data"][0].get("result", []))
        
        # logfire.info("SurrealDB query executed", 
        #             success=result["success"],
        #             query_length=len(query))
        
        return query_result
        
    except Exception as e:
        # logfire.error("Failed to execute SurrealDB query", query=query, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("create_record")
async def create_record(table: str, data: Dict[str, Any], record_id: Optional[str] = None) -> Dict[str, Any]:
    """Create a new record in a SurrealDB table."""
    # logfire.info("Creating record", table=table, record_id=record_id)
    
    try:
        if record_id:
            query = f"CREATE {table}:{record_id} CONTENT $data;"
        else:
            query = f"CREATE {table} CONTENT $data;"
        
        params = {"data": data}
        result = await surrealdb_client.execute_query(query, params)
        
        if result["success"]:
            created_record = {
                "table": table,
                "record_id": record_id,
                "data": data,
                "result": result["data"],
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Record created successfully", table=table, record_id=record_id)
            return created_record
        else:
            raise RuntimeError(f"Failed to create record: {result['data']}")
            
    except Exception as e:
        # logfire.error("Failed to create record", table=table, record_id=record_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("select_records")
async def select_records(
    table: str,
    where_clause: Optional[str] = None,
    limit: Optional[int] = None,
    order_by: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Select records from a SurrealDB table."""
    # logfire.info("Selecting records", table=table, where_clause=where_clause)
    
    try:
        query = f"SELECT * FROM {table}"
        
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if order_by:
            query += f" ORDER BY {order_by}"
        
        if limit:
            query += f" LIMIT {limit}"
        
        query += ";"
        
        result = await surrealdb_client.execute_query(query)
        
        if result["success"]:
            records = []
            if isinstance(result["data"], list) and result["data"]:
                records = result["data"][0].get("result", [])
            
            # logfire.info("Records selected", 
            #             table=table,
            #             count=len(records),
            #             where_clause=where_clause)
            
            return records
        else:
            raise RuntimeError(f"Failed to select records: {result['data']}")
            
    except Exception as e:
        # logfire.error("Failed to select records", table=table, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("update_record")
async def update_record(table: str, record_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a record in a SurrealDB table."""
    # logfire.info("Updating record", table=table, record_id=record_id)
    
    try:
        query = f"UPDATE {table}:{record_id} MERGE $data;"
        params = {"data": data}
        
        result = await surrealdb_client.execute_query(query, params)
        
        if result["success"]:
            updated_record = {
                "table": table,
                "record_id": record_id,
                "data": data,
                "result": result["data"],
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Record updated successfully", table=table, record_id=record_id)
            return updated_record
        else:
            raise RuntimeError(f"Failed to update record: {result['data']}")
            
    except Exception as e:
        # logfire.error("Failed to update record", table=table, record_id=record_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("delete_record")
async def delete_record(table: str, record_id: str) -> Dict[str, Any]:
    """Delete a record from a SurrealDB table."""
    # logfire.info("Deleting record", table=table, record_id=record_id)
    
    try:
        query = f"DELETE {table}:{record_id};"
        result = await surrealdb_client.execute_query(query)
        
        if result["success"]:
            deletion_result = {
                "table": table,
                "record_id": record_id,
                "result": result["data"],
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Record deleted successfully", table=table, record_id=record_id)
            return deletion_result
        else:
            raise RuntimeError(f"Failed to delete record: {result['data']}")
            
    except Exception as e:
        # logfire.error("Failed to delete record", table=table, record_id=record_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("create_graph_relation")
async def create_graph_relation(
    from_table: str,
    from_id: str,
    relation_type: str,
    to_table: str,
    to_id: str,
    properties: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Create a graph relationship between two records."""
    # logfire.info("Creating graph relation", 
    #             from_table=from_table,
    #             to_table=to_table,
    #             relation_type=relation_type)
    
    try:
        if properties:
            query = f"RELATE {from_table}:{from_id}->{relation_type}->{to_table}:{to_id} CONTENT $props;"
            params = {"props": properties}
        else:
            query = f"RELATE {from_table}:{from_id}->{relation_type}->{to_table}:{to_id};"
            params = {}
        
        result = await surrealdb_client.execute_query(query, params)
        
        if result["success"]:
            relation_result = {
                "from": f"{from_table}:{from_id}",
                "relation": relation_type,
                "to": f"{to_table}:{to_id}",
                "properties": properties,
                "result": result["data"],
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Graph relation created successfully", 
            #             from_table=from_table,
            #             to_table=to_table,
            #             relation_type=relation_type)
            
            return relation_result
        else:
            raise RuntimeError(f"Failed to create graph relation: {result['data']}")
            
    except Exception as e:
        # logfire.error("Failed to create graph relation", 
        pass
        #              from_table=from_table,
        #              to_table=to_table,
        #              relation_type=relation_type,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("vector_search")
async def vector_search(
    table: str,
    vector_field: str,
    query_vector: List[float],
    limit: int = 10,
    threshold: Optional[float] = None
) -> List[Dict[str, Any]]:
    """Perform vector similarity search."""
    # logfire.info("Performing vector search", 
    #             table=table,
    #             vector_field=vector_field,
    #             vector_dimension=len(query_vector),
    #             limit=limit)
    
    try:
        # Build vector search query
        if threshold:
            query = f"""
            SELECT *, vector::similarity::cosine({vector_field}, $vector) AS similarity
            FROM {table}
            WHERE vector::similarity::cosine({vector_field}, $vector) > {threshold}
            ORDER BY similarity DESC
            LIMIT {limit};
            """
        else:
            query = f"""
            SELECT *, vector::similarity::cosine({vector_field}, $vector) AS similarity
            FROM {table}
            ORDER BY similarity DESC
            LIMIT {limit};
            """
        
        params = {"vector": query_vector}
        result = await surrealdb_client.execute_query(query, params)
        
        if result["success"]:
            search_results = []
            if isinstance(result["data"], list) and result["data"]:
                search_results = result["data"][0].get("result", [])
            
            # logfire.info("Vector search completed", 
            #             table=table,
            #             results_count=len(search_results),
            #             vector_dimension=len(query_vector))
            
            return search_results
        else:
            raise RuntimeError(f"Vector search failed: {result['data']}")
            
    except Exception as e:
        # logfire.error("Vector search failed", 
        pass
        #              table=table,
        #              vector_field=vector_field,
        #              error=str(e))
        raise

@app.tool()
@logfire.instrument("get_database_schema")
async def get_database_schema() -> Dict[str, Any]:
    """Get the database schema information."""
    # logfire.info("Getting database schema")
    
    try:
        queries = {
            "database_info": "INFO FOR DB;",
            "tables": "INFO FOR TB;",
            "namespaces": "INFO FOR NS;"
        }
        
        schema_info = {}
        
        for info_type, query in queries.items():
            result = await surrealdb_client.execute_query(query)
            if result["success"]:
                schema_info[info_type] = result["data"]
            else:
                schema_info[info_type] = f"Error: {result['data']}"
        
        schema_result = {
            "namespace": surrealdb_client.namespace,
            "database": surrealdb_client.database,
            "schema": schema_info,
            "timestamp": datetime.now().isoformat()
        }
        
        # logfire.info("Database schema retrieved")
        return schema_result
        
    except Exception as e:
        # logfire.error("Failed to get database schema", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("count_records")
async def count_records(table: str, where_clause: Optional[str] = None) -> Dict[str, Any]:
    """Count records in a table with optional filter."""
    # logfire.info("Counting records", table=table, where_clause=where_clause)
    
    try:
        if where_clause:
            query = f"SELECT count() FROM {table} WHERE {where_clause} GROUP ALL;"
        else:
            query = f"SELECT count() FROM {table} GROUP ALL;"
        
        result = await surrealdb_client.execute_query(query)
        
        if result["success"]:
            count_data = result["data"]
            count = 0
            
            if isinstance(count_data, list) and count_data:
                count_result = count_data[0].get("result", [])
                if count_result:
                    count = count_result[0].get("count", 0)
            
            count_info = {
                "table": table,
                "where_clause": where_clause,
                "count": count,
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Record count completed", table=table, count=count)
            return count_info
        else:
            raise RuntimeError(f"Failed to count records: {result['data']}")
            
    except Exception as e:
        # logfire.error("Failed to count records", table=table, error=str(e))
        pass
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("SurrealDB MCP server starting up")
    
    # Test SurrealDB connectivity on startup
    try:
        await surrealdb_health_check()
        # logfire.info("SurrealDB connectivity verified on startup")
    except Exception as e:
        # logfire.warning("SurrealDB connectivity test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("SurrealDB MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting SurrealDB MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())