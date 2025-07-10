#!/usr/bin/env python3
"""
Memory MCP Server - Production Implementation
Provides persistent memory storage for context, facts, and conversation history.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import sqlite3
import hashlib
from dataclasses import dataclass
from enum import Enum

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


class MemoryType(Enum):
    """Types of memory entries"""
    FACT = "fact"
    CONTEXT = "context"
    CONVERSATION = "conversation"
    TASK = "task"
    PREFERENCE = "preference"
    RELATIONSHIP = "relationship"


@dataclass
class MemoryEntry:
    """Memory entry data structure"""
    id: str
    type: MemoryType
    content: str
    metadata: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    access_count: int = 0
    importance: float = 0.5
    tags: List[str] = None

    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MemoryStore:
    """SQLite-based memory storage"""

    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        """Create database tables"""
        cursor = self.conn.cursor()

        # Main memory table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                importance REAL DEFAULT 0.5
            )
        """)

        # Tags table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                memory_id TEXT NOT NULL,
                tag TEXT NOT NULL,
                FOREIGN KEY (memory_id) REFERENCES memories(id),
                PRIMARY KEY (memory_id, tag)
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON memories(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tag ON tags(tag)")

        self.conn.commit()

    def generate_id(self, content: str, type: MemoryType) -> str:
        """Generate unique ID for memory entry"""
        data = f"{type.value}:{content}:{datetime.now(timezone.utc).isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def store(self, entry: MemoryEntry) -> bool:
        """Store a memory entry"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO memories
                (id, type, content, metadata, created_at, updated_at, access_count, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                entry.id,
                entry.type.value,
                entry.content,
                json.dumps(entry.metadata),
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
                entry.access_count,
                entry.importance
            ))

            # Store tags
            cursor.execute("DELETE FROM tags WHERE memory_id = ?", (entry.id,))
            for tag in entry.tags:
                cursor.execute("INSERT INTO tags (memory_id, tag) VALUES (?, ?)",
                             (entry.id, tag))

            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            self.conn.rollback()
            return False

    def retrieve(self, id: str) -> Optional[MemoryEntry]:
        """Retrieve a memory entry by ID"""
        cursor = self.conn.cursor()

        # Update access count
        cursor.execute("""
            UPDATE memories
            SET access_count = access_count + 1
            WHERE id = ?
        """, (id,))

        # Retrieve memory
        cursor.execute("SELECT * FROM memories WHERE id = ?", (id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Get tags
        cursor.execute("SELECT tag FROM tags WHERE memory_id = ?", (id,))
        tags = [r[0] for r in cursor.fetchall()]

        self.conn.commit()

        return MemoryEntry(
            id=row['id'],
            type=MemoryType(row['type']),
            content=row['content'],
            metadata=json.loads(row['metadata'] or '{}'),
            created_at=datetime.fromisoformat(row['created_at']),
            updated_at=datetime.fromisoformat(row['updated_at']),
            access_count=row['access_count'],
            importance=row['importance'],
            tags=tags
        )

    def search(self, query: str, type: Optional[MemoryType] = None,
              tags: Optional[List[str]] = None, limit: int = 20) -> List[MemoryEntry]:
        """Search memories"""
        cursor = self.conn.cursor()

        # Build query
        sql = "SELECT DISTINCT m.* FROM memories m"
        conditions = []
        params = []

        if tags:
            sql += " JOIN tags t ON m.id = t.memory_id"
            conditions.append(f"t.tag IN ({','.join(['?'] * len(tags))})")
            params.extend(tags)

        if query:
            conditions.append("m.content LIKE ?")
            params.append(f"%{query}%")

        if type:
            conditions.append("m.type = ?")
            params.append(type.value)

        if conditions:
            sql += " WHERE " + " AND ".join(conditions)

        sql += " ORDER BY m.importance DESC, m.access_count DESC LIMIT ?"
        params.append(limit)

        cursor.execute(sql, params)
        rows = cursor.fetchall()

        memories = []
        for row in rows:
            # Get tags
            cursor.execute("SELECT tag FROM tags WHERE memory_id = ?", (row['id'],))
            tags = [r[0] for r in cursor.fetchall()]

            memories.append(MemoryEntry(
                id=row['id'],
                type=MemoryType(row['type']),
                content=row['content'],
                metadata=json.loads(row['metadata'] or '{}'),
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                access_count=row['access_count'],
                importance=row['importance'],
                tags=tags
            ))

        return memories

    def update_importance(self, id: str, importance: float) -> bool:
        """Update memory importance"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                UPDATE memories
                SET importance = ?, updated_at = ?
                WHERE id = ?
            """, (importance, datetime.now(timezone.utc).isoformat(), id))

            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating importance: {e}")
            return False

    def delete(self, id: str) -> bool:
        """Delete a memory entry"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("DELETE FROM tags WHERE memory_id = ?", (id,))
            cursor.execute("DELETE FROM memories WHERE id = ?", (id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting memory: {e}")
            return False

    def get_statistics(self) -> Dict[str, Any]:
        """Get memory statistics"""
        cursor = self.conn.cursor()

        # Total memories
        cursor.execute("SELECT COUNT(*) FROM memories")
        total = cursor.fetchone()[0]

        # By type
        cursor.execute("""
            SELECT type, COUNT(*)
            FROM memories
            GROUP BY type
        """)
        by_type = dict(cursor.fetchall())

        # Most accessed
        cursor.execute("""
            SELECT id, content, access_count
            FROM memories
            ORDER BY access_count DESC
            LIMIT 5
        """)
        most_accessed = [
            {"id": r[0], "content": r[1][:50], "access_count": r[2]}
            for r in cursor.fetchall()
        ]

        # Most important
        cursor.execute("""
            SELECT id, content, importance
            FROM memories
            ORDER BY importance DESC
            LIMIT 5
        """)
        most_important = [
            {"id": r[0], "content": r[1][:50], "importance": r[2]}
            for r in cursor.fetchall()
        ]

        return {
            "total": total,
            "by_type": by_type,
            "most_accessed": most_accessed,
            "most_important": most_important
        }

    def close(self):
        """Close database connection"""
        self.conn.close()


class MemoryMCPServer:
    """Memory MCP Server implementation"""

    def __init__(self):
        self.store: Optional[MemoryStore] = None
        self.server_info = {
            "name": "memory-mcp",
            "version": "1.0.0",
            "description": "Persistent memory storage for context and facts",
            "author": "DevQ.ai Team"
        }

    async def initialize(self):
        """Initialize the server"""
        db_path = os.getenv("MEMORY_DB_PATH", "memory.db")
        self.store = MemoryStore(db_path)
        logger.info(f"Memory MCP Server initialized with database: {db_path}")

    def list_tools(self) -> List[Dict[str, Any]]:
        """List available tools"""
        return [
            {
                "name": "store_memory",
                "description": "Store a memory entry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "enum": ["fact", "context", "conversation", "task", "preference", "relationship"]},
                        "content": {"type": "string", "description": "Memory content"},
                        "metadata": {"type": "object", "description": "Additional metadata"},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                        "importance": {"type": "number", "description": "Importance score (0-1)"}
                    },
                    "required": ["type", "content"]
                }
            },
            {
                "name": "retrieve_memory",
                "description": "Retrieve a memory by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Memory ID"}
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "search_memories",
                "description": "Search memories by query, type, or tags",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "type": {"type": "string", "enum": ["fact", "context", "conversation", "task", "preference", "relationship"]},
                        "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                        "limit": {"type": "integer", "description": "Maximum results (default: 20)"}
                    }
                }
            },
            {
                "name": "update_importance",
                "description": "Update memory importance score",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Memory ID"},
                        "importance": {"type": "number", "description": "New importance score (0-1)"}
                    },
                    "required": ["id", "importance"]
                }
            },
            {
                "name": "delete_memory",
                "description": "Delete a memory entry",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string", "description": "Memory ID"}
                    },
                    "required": ["id"]
                }
            },
            {
                "name": "get_memory_stats",
                "description": "Get memory statistics",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "store_conversation",
                "description": "Store a conversation turn",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "role": {"type": "string", "enum": ["user", "assistant"]},
                        "content": {"type": "string", "description": "Message content"},
                        "metadata": {"type": "object", "description": "Additional context"}
                    },
                    "required": ["role", "content"]
                }
            },
            {
                "name": "get_conversation_history",
                "description": "Get recent conversation history",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "description": "Number of messages (default: 10)"}
                    }
                }
            }
        ]

    async def handle_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution"""
        if not self.store:
            return {"error": "Memory store not initialized"}

        try:
            if tool_name == "store_memory":
                type_str = arguments["type"]
                content = arguments["content"]
                metadata = arguments.get("metadata", {})
                tags = arguments.get("tags", [])
                importance = arguments.get("importance", 0.5)

                entry = MemoryEntry(
                    id=self.store.generate_id(content, MemoryType(type_str)),
                    type=MemoryType(type_str),
                    content=content,
                    metadata=metadata,
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    tags=tags,
                    importance=importance
                )

                success = self.store.store(entry)

                return {
                    "stored": success,
                    "id": entry.id,
                    "type": type_str
                }

            elif tool_name == "retrieve_memory":
                memory = self.store.retrieve(arguments["id"])

                if memory:
                    return {
                        "found": True,
                        "memory": {
                            "id": memory.id,
                            "type": memory.type.value,
                            "content": memory.content,
                            "metadata": memory.metadata,
                            "tags": memory.tags,
                            "importance": memory.importance,
                            "access_count": memory.access_count,
                            "created_at": memory.created_at.isoformat(),
                            "updated_at": memory.updated_at.isoformat()
                        }
                    }
                else:
                    return {"found": False}

            elif tool_name == "search_memories":
                query = arguments.get("query", "")
                type_str = arguments.get("type")
                tags = arguments.get("tags", [])
                limit = arguments.get("limit", 20)

                memories = self.store.search(
                    query=query,
                    type=MemoryType(type_str) if type_str else None,
                    tags=tags,
                    limit=limit
                )

                return {
                    "memories": [
                        {
                            "id": m.id,
                            "type": m.type.value,
                            "content": m.content,
                            "tags": m.tags,
                            "importance": m.importance,
                            "access_count": m.access_count
                        }
                        for m in memories
                    ],
                    "count": len(memories)
                }

            elif tool_name == "update_importance":
                success = self.store.update_importance(
                    arguments["id"],
                    arguments["importance"]
                )

                return {
                    "updated": success,
                    "id": arguments["id"]
                }

            elif tool_name == "delete_memory":
                success = self.store.delete(arguments["id"])

                return {
                    "deleted": success,
                    "id": arguments["id"]
                }

            elif tool_name == "get_memory_stats":
                stats = self.store.get_statistics()
                return stats

            elif tool_name == "store_conversation":
                entry = MemoryEntry(
                    id=self.store.generate_id(
                        f"{arguments['role']}: {arguments['content']}",
                        MemoryType.CONVERSATION
                    ),
                    type=MemoryType.CONVERSATION,
                    content=arguments["content"],
                    metadata={
                        "role": arguments["role"],
                        **arguments.get("metadata", {})
                    },
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                    tags=["conversation", arguments["role"]]
                )

                success = self.store.store(entry)

                return {
                    "stored": success,
                    "id": entry.id
                }

            elif tool_name == "get_conversation_history":
                limit = arguments.get("limit", 10)

                conversations = self.store.search(
                    query="",
                    type=MemoryType.CONVERSATION,
                    limit=limit
                )

                # Sort by creation time (most recent first)
                conversations.sort(key=lambda x: x.created_at, reverse=True)

                return {
                    "conversations": [
                        {
                            "role": c.metadata.get("role", "unknown"),
                            "content": c.content,
                            "timestamp": c.created_at.isoformat(),
                            "id": c.id
                        }
                        for c in conversations
                    ],
                    "count": len(conversations)
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
                    "instructions": "Memory MCP server for persistent context storage"
                }
            elif method == "tools/list":
                result = {"tools": self.list_tools()}
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                result = await self.handle_tool_call(tool_name, arguments)
            elif method == "health":
                result = {
                    "status": "healthy" if self.store else "not_initialized",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "db_path": self.store.db_path if self.store else None
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

    async def cleanup(self):
        """Cleanup resources"""
        if self.store:
            self.store.close()

    async def run_stdio(self):
        """Run the server in stdio mode"""
        logger.info("Starting Memory MCP Server in stdio mode")

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
        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    server = MemoryMCPServer()
    await server.run_stdio()


if __name__ == "__main__":
    asyncio.run(main())
