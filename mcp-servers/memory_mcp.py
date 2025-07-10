#!/usr/bin/env python3
"""
Memory MCP Server
Persistent memory management with context storage and retrieval using FastMCP framework.
"""

import asyncio
import json
import os
import sqlite3
import hashlib
from typing import Dict, Any, List, Optional, Union
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add parent directory to path for FastMCP imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastmcp import FastMCP
import logfire

try:
    from pydantic import BaseModel, Field
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False
    BaseModel = object
    def Field(*args, **kwargs):
        return None


class MemoryEntry(BaseModel if PYDANTIC_AVAILABLE else object):
    """Memory entry model"""
    id: Optional[str] = Field(None, description="Unique memory ID")
    content: str = Field(..., description="Memory content")
    context: Optional[str] = Field(None, description="Context or category")
    tags: List[str] = Field(default_factory=list, description="Memory tags")
    created_at: Optional[str] = Field(None, description="Creation timestamp")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")
    importance: int = Field(5, description="Importance score 1-10")
    expires_at: Optional[str] = Field(None, description="Expiration timestamp")


class MemoryMCP:
    """
    Memory MCP Server using FastMCP framework

    Provides comprehensive memory management operations including:
    - Persistent storage and retrieval
    - Context-based organization
    - Tag-based categorization
    - Search and filtering
    - Memory expiration management
    - Importance scoring
    """

    def __init__(self):
        self.mcp = FastMCP("memory-mcp", version="1.0.0", description="Persistent memory management and context storage")
        self.db_path = os.getenv("MEMORY_DB_PATH", "memory.db")
        self.max_memories = int(os.getenv("MEMORY_MAX_ENTRIES", "10000"))
        self._setup_database()
        self._setup_tools()

    def _setup_database(self):
        """Initialize SQLite database for memory storage"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    context TEXT,
                    tags TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    importance INTEGER DEFAULT 5,
                    expires_at TEXT,
                    content_hash TEXT
                )
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_context ON memories(context)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)
            """)
            self.conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)
            """)
            self.conn.commit()
            logfire.info("Memory database initialized successfully")
        except Exception as e:
            logfire.error(f"Failed to initialize memory database: {str(e)}")
            raise

    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory entry"""
        return hashlib.md5(f"{content}{datetime.utcnow().isoformat()}".encode()).hexdigest()

    def _cleanup_expired(self):
        """Remove expired memories"""
        try:
            current_time = datetime.utcnow().isoformat()
            cursor = self.conn.cursor()
            cursor.execute(
                "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at < ?",
                (current_time,)
            )
            deleted_count = cursor.rowcount
            self.conn.commit()
            if deleted_count > 0:
                logfire.info(f"Cleaned up {deleted_count} expired memories")
        except Exception as e:
            logfire.error(f"Failed to cleanup expired memories: {str(e)}")

    def _setup_tools(self):
        """Setup Memory MCP tools"""

        @self.mcp.tool(
            name="store_memory",
            description="Store a new memory with context and tags",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to store"},
                    "context": {"type": "string", "description": "Context or category for the memory"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                    "importance": {"type": "integer", "description": "Importance score 1-10", "default": 5},
                    "expires_in_hours": {"type": "integer", "description": "Hours until expiration (optional)"}
                },
                "required": ["content"]
            }
        )
        async def store_memory(content: str, context: str = None, tags: List[str] = None,
                             importance: int = 5, expires_in_hours: int = None) -> Dict[str, Any]:
            """Store a new memory entry"""
            try:
                self._cleanup_expired()

                # Check if we're at capacity and need to remove old memories
                cursor = self.conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM memories")
                count = cursor.fetchone()[0]

                if count >= self.max_memories:
                    # Remove oldest, least important memories
                    cursor.execute("""
                        DELETE FROM memories WHERE id IN (
                            SELECT id FROM memories
                            ORDER BY importance ASC, created_at ASC
                            LIMIT 100
                        )
                    """)
                    self.conn.commit()

                memory_id = self._generate_id(content)
                created_at = datetime.utcnow().isoformat()
                content_hash = hashlib.md5(content.encode()).hexdigest()

                expires_at = None
                if expires_in_hours:
                    expires_at = (datetime.utcnow() + timedelta(hours=expires_in_hours)).isoformat()

                tags_str = json.dumps(tags or [])

                cursor.execute("""
                    INSERT OR REPLACE INTO memories
                    (id, content, context, tags, created_at, updated_at, importance, expires_at, content_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (memory_id, content, context, tags_str, created_at, created_at, importance, expires_at, content_hash))

                self.conn.commit()

                return {
                    "memory_id": memory_id,
                    "status": "stored",
                    "content": content,
                    "context": context,
                    "tags": tags or [],
                    "importance": importance,
                    "created_at": created_at,
                    "expires_at": expires_at
                }

            except Exception as e:
                logfire.error(f"Failed to store memory: {str(e)}")
                return {"error": f"Memory storage failed: {str(e)}"}

        @self.mcp.tool(
            name="retrieve_memory",
            description="Retrieve a specific memory by ID",
            input_schema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID to retrieve"}
                },
                "required": ["memory_id"]
            }
        )
        async def retrieve_memory(memory_id: str) -> Dict[str, Any]:
            """Retrieve a specific memory by ID"""
            try:
                self._cleanup_expired()

                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT id, content, context, tags, created_at, updated_at, importance, expires_at
                    FROM memories WHERE id = ?
                """, (memory_id,))

                row = cursor.fetchone()
                if not row:
                    return {"error": f"Memory with ID '{memory_id}' not found"}

                tags = json.loads(row[3]) if row[3] else []

                return {
                    "memory_id": row[0],
                    "content": row[1],
                    "context": row[2],
                    "tags": tags,
                    "created_at": row[4],
                    "updated_at": row[5],
                    "importance": row[6],
                    "expires_at": row[7]
                }

            except Exception as e:
                logfire.error(f"Failed to retrieve memory: {str(e)}")
                return {"error": f"Memory retrieval failed: {str(e)}"}

        @self.mcp.tool(
            name="search_memories",
            description="Search memories by content, context, or tags",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query for content"},
                    "context": {"type": "string", "description": "Filter by context"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "min_importance": {"type": "integer", "description": "Minimum importance score"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 50}
                }
            }
        )
        async def search_memories(query: str = None, context: str = None, tags: List[str] = None,
                                min_importance: int = None, limit: int = 50) -> Dict[str, Any]:
            """Search memories with various filters"""
            try:
                self._cleanup_expired()

                conditions = []
                params = []

                if query:
                    conditions.append("content LIKE ?")
                    params.append(f"%{query}%")

                if context:
                    conditions.append("context = ?")
                    params.append(context)

                if tags:
                    for tag in tags:
                        conditions.append("tags LIKE ?")
                        params.append(f"%{tag}%")

                if min_importance is not None:
                    conditions.append("importance >= ?")
                    params.append(min_importance)

                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

                cursor = self.conn.cursor()
                cursor.execute(f"""
                    SELECT id, content, context, tags, created_at, updated_at, importance, expires_at
                    FROM memories {where_clause}
                    ORDER BY importance DESC, created_at DESC
                    LIMIT ?
                """, params + [limit])

                rows = cursor.fetchall()
                memories = []

                for row in rows:
                    tags_list = json.loads(row[3]) if row[3] else []
                    memories.append({
                        "memory_id": row[0],
                        "content": row[1],
                        "context": row[2],
                        "tags": tags_list,
                        "created_at": row[4],
                        "updated_at": row[5],
                        "importance": row[6],
                        "expires_at": row[7]
                    })

                return {
                    "memories": memories,
                    "total_found": len(memories),
                    "search_params": {
                        "query": query,
                        "context": context,
                        "tags": tags,
                        "min_importance": min_importance,
                        "limit": limit
                    }
                }

            except Exception as e:
                logfire.error(f"Failed to search memories: {str(e)}")
                return {"error": f"Memory search failed: {str(e)}"}

        @self.mcp.tool(
            name="update_memory",
            description="Update an existing memory",
            input_schema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID to update"},
                    "content": {"type": "string", "description": "New content"},
                    "context": {"type": "string", "description": "New context"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "New tags"},
                    "importance": {"type": "integer", "description": "New importance score 1-10"}
                },
                "required": ["memory_id"]
            }
        )
        async def update_memory(memory_id: str, content: str = None, context: str = None,
                              tags: List[str] = None, importance: int = None) -> Dict[str, Any]:
            """Update an existing memory"""
            try:
                cursor = self.conn.cursor()

                # Check if memory exists
                cursor.execute("SELECT id FROM memories WHERE id = ?", (memory_id,))
                if not cursor.fetchone():
                    return {"error": f"Memory with ID '{memory_id}' not found"}

                updates = []
                params = []

                if content is not None:
                    updates.append("content = ?")
                    params.append(content)

                if context is not None:
                    updates.append("context = ?")
                    params.append(context)

                if tags is not None:
                    updates.append("tags = ?")
                    params.append(json.dumps(tags))

                if importance is not None:
                    updates.append("importance = ?")
                    params.append(importance)

                updates.append("updated_at = ?")
                params.append(datetime.utcnow().isoformat())

                params.append(memory_id)

                cursor.execute(f"""
                    UPDATE memories
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, params)

                self.conn.commit()

                return {
                    "memory_id": memory_id,
                    "status": "updated",
                    "updated_fields": {
                        "content": content,
                        "context": context,
                        "tags": tags,
                        "importance": importance
                    }
                }

            except Exception as e:
                logfire.error(f"Failed to update memory: {str(e)}")
                return {"error": f"Memory update failed: {str(e)}"}

        @self.mcp.tool(
            name="delete_memory",
            description="Delete a specific memory",
            input_schema={
                "type": "object",
                "properties": {
                    "memory_id": {"type": "string", "description": "Memory ID to delete"}
                },
                "required": ["memory_id"]
            }
        )
        async def delete_memory(memory_id: str) -> Dict[str, Any]:
            """Delete a specific memory"""
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))

                if cursor.rowcount == 0:
                    return {"error": f"Memory with ID '{memory_id}' not found"}

                self.conn.commit()

                return {
                    "memory_id": memory_id,
                    "status": "deleted"
                }

            except Exception as e:
                logfire.error(f"Failed to delete memory: {str(e)}")
                return {"error": f"Memory deletion failed: {str(e)}"}

        @self.mcp.tool(
            name="list_contexts",
            description="List all available contexts",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def list_contexts() -> Dict[str, Any]:
            """List all available contexts"""
            try:
                cursor = self.conn.cursor()
                cursor.execute("""
                    SELECT context, COUNT(*) as count
                    FROM memories
                    WHERE context IS NOT NULL
                    GROUP BY context
                    ORDER BY count DESC
                """)

                contexts = []
                for row in cursor.fetchall():
                    contexts.append({
                        "context": row[0],
                        "memory_count": row[1]
                    })

                return {
                    "contexts": contexts,
                    "total_contexts": len(contexts)
                }

            except Exception as e:
                logfire.error(f"Failed to list contexts: {str(e)}")
                return {"error": f"Context listing failed: {str(e)}"}

        @self.mcp.tool(
            name="get_memory_stats",
            description="Get memory database statistics",
            input_schema={
                "type": "object",
                "properties": {}
            }
        )
        async def get_memory_stats() -> Dict[str, Any]:
            """Get memory database statistics"""
            try:
                self._cleanup_expired()

                cursor = self.conn.cursor()

                # Total memories
                cursor.execute("SELECT COUNT(*) FROM memories")
                total_memories = cursor.fetchone()[0]

                # Memories by importance
                cursor.execute("""
                    SELECT importance, COUNT(*)
                    FROM memories
                    GROUP BY importance
                    ORDER BY importance DESC
                """)
                importance_distribution = dict(cursor.fetchall())

                # Most recent memories
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM memories
                    WHERE created_at > datetime('now', '-24 hours')
                """)
                recent_count = cursor.fetchone()[0]

                # Expiring soon
                cursor.execute("""
                    SELECT COUNT(*)
                    FROM memories
                    WHERE expires_at IS NOT NULL AND expires_at > datetime('now') AND expires_at < datetime('now', '+24 hours')
                """)
                expiring_soon = cursor.fetchone()[0]

                return {
                    "total_memories": total_memories,
                    "max_capacity": self.max_memories,
                    "capacity_used_percent": round((total_memories / self.max_memories) * 100, 2),
                    "recent_24h": recent_count,
                    "expiring_soon_24h": expiring_soon,
                    "importance_distribution": importance_distribution,
                    "database_path": self.db_path
                }

            except Exception as e:
                logfire.error(f"Failed to get memory stats: {str(e)}")
                return {"error": f"Memory stats query failed: {str(e)}"}

        @self.mcp.tool(
            name="export_memories",
            description="Export memories to JSON format",
            input_schema={
                "type": "object",
                "properties": {
                    "context": {"type": "string", "description": "Filter by context"},
                    "min_importance": {"type": "integer", "description": "Minimum importance score"}
                }
            }
        )
        async def export_memories(context: str = None, min_importance: int = None) -> Dict[str, Any]:
            """Export memories to JSON format"""
            try:
                conditions = []
                params = []

                if context:
                    conditions.append("context = ?")
                    params.append(context)

                if min_importance is not None:
                    conditions.append("importance >= ?")
                    params.append(min_importance)

                where_clause = ""
                if conditions:
                    where_clause = "WHERE " + " AND ".join(conditions)

                cursor = self.conn.cursor()
                cursor.execute(f"""
                    SELECT id, content, context, tags, created_at, updated_at, importance, expires_at
                    FROM memories {where_clause}
                    ORDER BY importance DESC, created_at DESC
                """, params)

                memories = []
                for row in cursor.fetchall():
                    tags_list = json.loads(row[3]) if row[3] else []
                    memories.append({
                        "memory_id": row[0],
                        "content": row[1],
                        "context": row[2],
                        "tags": tags_list,
                        "created_at": row[4],
                        "updated_at": row[5],
                        "importance": row[6],
                        "expires_at": row[7]
                    })

                export_data = {
                    "export_timestamp": datetime.utcnow().isoformat(),
                    "total_memories": len(memories),
                    "filters": {
                        "context": context,
                        "min_importance": min_importance
                    },
                    "memories": memories
                }

                return {
                    "status": "exported",
                    "export_data": export_data
                }

            except Exception as e:
                logfire.error(f"Failed to export memories: {str(e)}")
                return {"error": f"Memory export failed: {str(e)}"}

    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'conn'):
            self.conn.close()

    async def run(self):
        """Run the Memory MCP server"""
        await self.mcp.run_stdio()


async def main():
    """Main entry point"""
    server = MemoryMCP()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
