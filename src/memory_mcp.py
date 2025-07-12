#!/usr/bin/env python
"""
Memory MCP Server
FastMCP server for persistent memory management using existing memory.db.
Provides session persistence and memory operations.
"""
import asyncio
import os
import sqlite3
import json
import hashlib
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
#     service_name='memory-mcp-server',
#     environment='production'
# )

# Create FastMCP app instance
app = FastMCP("memory-mcp")

class MemoryManager:
    """Memory operations manager using existing memory.db."""
    
    def __init__(self):
        self.db_path = os.getenv('MEMORY_DB_PATH', '/Users/dionedge/devqai/machina/memory.db')
        self.ensure_database()
    
    def ensure_database(self):
        """Ensure database exists and has proper schema."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Memory database not found at {self.db_path}")
        
        # Test connection
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT count(*) FROM memories")
                count = cursor.fetchone()[0]
                # logfire.info("Memory database connected", path=self.db_path, memory_count=count)
        except Exception as e:
            # logfire.error("Memory database connection failed", path=self.db_path, error=str(e))
            pass
            raise
    
    def get_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

memory_manager = MemoryManager()

@app.tool()
@logfire.instrument("memory_health_check")
async def memory_health_check() -> Dict[str, Any]:
    """Check memory database health and return statistics."""
    # logfire.info("Memory health check requested")
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get database statistics
            cursor.execute("SELECT count(*) FROM memories")
            total_memories = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*) FROM memories WHERE expires_at IS NULL OR expires_at > ?", 
                          (datetime.now().isoformat(),))
            active_memories = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(DISTINCT context) FROM memories WHERE context IS NOT NULL")
            unique_contexts = cursor.fetchone()[0]
            
            health_status = {
                "status": "healthy",
                "database_path": memory_manager.db_path,
                "total_memories": total_memories,
                "active_memories": active_memories,
                "unique_contexts": unique_contexts,
                "timestamp": datetime.now().isoformat()
            }
            
            # logfire.info("Memory health check completed", health_status=health_status)
            return health_status
            
    except Exception as e:
        # logfire.error("Memory health check failed", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("store_memory")
async def store_memory(
    content: str, 
    context: Optional[str] = None,
    tags: Optional[str] = None,
    importance: int = 5,
    expires_at: Optional[str] = None
) -> Dict[str, Any]:
    """Store a new memory in the database."""
    # logfire.info("Storing memory", 
    #             content_length=len(content), 
    #             context=context, 
    #             importance=importance)
    
    try:
        # Generate unique ID and content hash
        memory_id = f"mem_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(4).hex()}"
        content_hash = memory_manager.generate_content_hash(content)
        timestamp = datetime.now().isoformat()
        
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check for duplicate content
            cursor.execute("SELECT id FROM memories WHERE content_hash = ?", (content_hash,))
            existing = cursor.fetchone()
            
            if existing:
                # logfire.warning("Duplicate content detected", 
                #                content_hash=content_hash, 
                #                existing_id=existing[0])
                pass
                return {
                    "status": "duplicate",
                    "memory_id": existing[0],
                    "message": "Memory with similar content already exists"
                }
            
            # Insert new memory
            cursor.execute("""
                INSERT INTO memories 
                (id, content, context, tags, created_at, updated_at, importance, expires_at, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (memory_id, content, context, tags, timestamp, timestamp, importance, expires_at, content_hash))
            
            conn.commit()
            
            result = {
                "status": "stored",
                "memory_id": memory_id,
                "content_hash": content_hash,
                "created_at": timestamp,
                "importance": importance
            }
            
            # logfire.info("Memory stored successfully", memory_id=memory_id, content_hash=content_hash)
            return result
            
    except Exception as e:
        # logfire.error("Failed to store memory", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("search_memories")
async def search_memories(
    query: str,
    context: Optional[str] = None,
    tags: Optional[str] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Search memories by content, context, or tags."""
    # logfire.info("Searching memories", query=query, context=context, tags=tags, limit=limit)
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Build search query
            sql_query = """
                SELECT id, content, context, tags, created_at, updated_at, importance, expires_at
                FROM memories 
                WHERE (expires_at IS NULL OR expires_at > ?)
                AND content LIKE ?
            """
            params = [datetime.now().isoformat(), f'%{query}%']
            
            if context:
                sql_query += " AND context = ?"
                params.append(context)
            
            if tags:
                sql_query += " AND tags LIKE ?"
                params.append(f'%{tags}%')
            
            sql_query += " ORDER BY importance DESC, created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(sql_query, params)
            rows = cursor.fetchall()
            
            memories = []
            for row in rows:
                memory = {
                    "id": row[0],
                    "content": row[1],
                    "context": row[2],
                    "tags": row[3],
                    "created_at": row[4],
                    "updated_at": row[5],
                    "importance": row[6],
                    "expires_at": row[7]
                }
                memories.append(memory)
            
            # logfire.info("Memory search completed", 
            #             query=query, 
            #             results_count=len(memories),
            #             limit=limit)
            
            return memories
            
    except Exception as e:
        # logfire.error("Memory search failed", query=query, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("get_memory")
async def get_memory(memory_id: str) -> Dict[str, Any]:
    """Get a specific memory by ID."""
    # logfire.info("Getting memory", memory_id=memory_id)
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, content, context, tags, created_at, updated_at, importance, expires_at, content_hash
                FROM memories 
                WHERE id = ?
            """, (memory_id,))
            
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Memory not found: {memory_id}")
            
            memory = {
                "id": row[0],
                "content": row[1], 
                "context": row[2],
                "tags": row[3],
                "created_at": row[4],
                "updated_at": row[5],
                "importance": row[6],
                "expires_at": row[7],
                "content_hash": row[8]
            }
            
            # logfire.info("Memory retrieved", memory_id=memory_id)
            return memory
            
    except Exception as e:
        # logfire.error("Failed to get memory", memory_id=memory_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("update_memory")
async def update_memory(
    memory_id: str,
    content: Optional[str] = None,
    context: Optional[str] = None,
    tags: Optional[str] = None,
    importance: Optional[int] = None
) -> Dict[str, Any]:
    """Update an existing memory."""
    # logfire.info("Updating memory", memory_id=memory_id)
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if memory exists
            cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
            if not cursor.fetchone():
                raise ValueError(f"Memory not found: {memory_id}")
            
            # Build update query
            updates = []
            params = []
            
            if content is not None:
                updates.append("content = ?")
                params.append(content)
                updates.append("content_hash = ?")
                params.append(memory_manager.generate_content_hash(content))
            
            if context is not None:
                updates.append("context = ?")
                params.append(context)
            
            if tags is not None:
                updates.append("tags = ?")
                params.append(tags)
            
            if importance is not None:
                updates.append("importance = ?")
                params.append(importance)
            
            if updates:
                updates.append("updated_at = ?")
                params.append(datetime.now().isoformat())
                params.append(memory_id)
                
                sql_query = f"UPDATE memories SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(sql_query, params)
                conn.commit()
            
            result = {
                "status": "updated",
                "memory_id": memory_id,
                "updated_at": datetime.now().isoformat()
            }
            
            # logfire.info("Memory updated successfully", memory_id=memory_id)
            return result
            
    except Exception as e:
        # logfire.error("Failed to update memory", memory_id=memory_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("delete_memory")
async def delete_memory(memory_id: str) -> Dict[str, Any]:
    """Delete a memory from the database."""
    # logfire.info("Deleting memory", memory_id=memory_id)
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if memory exists
            cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
            if not cursor.fetchone():
                raise ValueError(f"Memory not found: {memory_id}")
            
            # Delete memory
            cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()
            
            result = {
                "status": "deleted",
                "memory_id": memory_id,
                "deleted_at": datetime.now().isoformat()
            }
            
            # logfire.info("Memory deleted successfully", memory_id=memory_id)
            return result
            
    except Exception as e:
        # logfire.error("Failed to delete memory", memory_id=memory_id, error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("list_contexts")
async def list_contexts() -> List[str]:
    """List all unique contexts in the memory database."""
    # logfire.info("Listing memory contexts")
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT DISTINCT context 
                FROM memories 
                WHERE context IS NOT NULL 
                AND (expires_at IS NULL OR expires_at > ?)
                ORDER BY context
            """, (datetime.now().isoformat(),))
            
            contexts = [row[0] for row in cursor.fetchall()]
            
            # logfire.info("Contexts listed", count=len(contexts))
            return contexts
            
    except Exception as e:
        # logfire.error("Failed to list contexts", error=str(e))
        pass
        raise

@app.tool()
@logfire.instrument("cleanup_expired_memories")
async def cleanup_expired_memories() -> Dict[str, Any]:
    """Remove expired memories from the database."""
    # logfire.info("Cleaning up expired memories")
    
    try:
        with memory_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Count expired memories
            cursor.execute("""
                SELECT count(*) FROM memories 
                WHERE expires_at IS NOT NULL 
                AND expires_at <= ?
            """, (datetime.now().isoformat(),))
            
            expired_count = cursor.fetchone()[0]
            
            # Delete expired memories
            cursor.execute("""
                DELETE FROM memories 
                WHERE expires_at IS NOT NULL 
                AND expires_at <= ?
            """, (datetime.now().isoformat(),))
            
            conn.commit()
            
            result = {
                "status": "cleaned",
                "expired_memories_removed": expired_count,
                "cleaned_at": datetime.now().isoformat()
            }
            
            # logfire.info("Expired memories cleaned up", expired_count=expired_count)
            return result
            
    except Exception as e:
        # logfire.error("Failed to cleanup expired memories", error=str(e))
        pass
        raise

# Server startup handler

async def startup():
    """Server startup handler."""
    # logfire.info("Memory MCP server starting up")
    
    # Test database connectivity on startup
    try:
        await memory_health_check()
        # logfire.info("Memory database connectivity verified on startup")
    except Exception as e:
        # logfire.warning("Memory database connectivity test failed on startup", error=str(e))


        pass
async def shutdown():
    """Server shutdown handler."""
    # logfire.info("Memory MCP server shutting down")

if __name__ == "__main__":
    # logfire.info("Starting Memory MCP server")
    import asyncio
    asyncio.run(app.run_stdio_async())