#!/usr/bin/env python3
"""
Script to add memory-mcp to Zed IDE configuration

This script safely adds the memory-mcp server configuration to your existing
Zed settings.json file while preserving all existing settings.
"""

import json
import os
from pathlib import Path


def add_memory_mcp_to_zed_config():
    """Add memory-mcp server to Zed IDE configuration."""

    # Path to Zed settings
    zed_settings_path = Path("/Users/dionedge/devqai/.zed/settings.json")

    if not zed_settings_path.exists():
        print(f"❌ Zed settings file not found: {zed_settings_path}")
        return False

    try:
        # Read existing settings
        with open(zed_settings_path, 'r') as f:
            settings = json.load(f)

        # Ensure mcpServers section exists
        if "mcpServers" not in settings:
            settings["mcpServers"] = {}

        # Add memory-mcp configuration
        settings["mcpServers"]["memory"] = {
            "command": "node",
            "args": ["/Users/dionedge/devqai/mcp/mcp-servers/memory-mcp/dist/index.js"],
            "env": {
                "MEMORY_FILE_PATH": "/Users/dionedge/devqai/machina/memory.json"
            }
        }

        # Write updated settings
        with open(zed_settings_path, 'w') as f:
            json.dump(settings, f, indent=4)

        print("✅ Successfully added memory-mcp to Zed configuration")
        print(f"📁 Memory file will be stored at: /Users/dionedge/devqai/machina/memory.json")
        print("🔄 Please restart Zed IDE to load the new MCP server")

        return True

    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in settings file: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating settings: {e}")
        return False


def verify_memory_mcp_installation():
    """Verify that memory-mcp is properly installed."""

    memory_mcp_path = Path("/Users/dionedge/devqai/mcp/mcp-servers/memory-mcp/dist/index.js")

    if not memory_mcp_path.exists():
        print(f"❌ memory-mcp not found at: {memory_mcp_path}")
        return False

    print(f"✅ memory-mcp found at: {memory_mcp_path}")
    return True


def create_memory_directory():
    """Create directory for memory storage if it doesn't exist."""

    memory_dir = Path("/Users/dionedge/devqai/machina")
    memory_dir.mkdir(parents=True, exist_ok=True)

    # Create initial empty memory file
    memory_file = memory_dir / "memory.json"
    if not memory_file.exists():
        with open(memory_file, 'w') as f:
            json.dump([], f, indent=2)
        print(f"📝 Created initial memory file: {memory_file}")

    return True


def show_usage_examples():
    """Show examples of how to use context7 and memory-mcp."""

    print("\n🧠 MCP Tools Usage Examples:")
    print("=" * 50)

    print("\n📚 MEMORY-MCP Tools:")
    print("- create_memory: Store persistent information")
    print("- search_memory: Search through stored memories")
    print("- update_memory: Update existing memories")
    print("- delete_memory: Remove memories")
    print("- list_memories: List all stored memories")

    print("\n🎯 CONTEXT7 Tools:")
    print("- store_context: Store contextual information in Redis")
    print("- retrieve_context: Retrieve stored context")
    print("- search_contexts: Search through contexts")
    print("- delete_context: Remove stored contexts")

    print("\n💡 Example Usage in Zed:")
    print("- 'Remember that we completed TaskMaster AI integration with 100% test coverage'")
    print("- 'What did we store about the Redis configuration?'")
    print("- 'Search for information about MCP protocol implementation'")
    print("- 'Store the current project status in context'")

    print("\n🔗 Integration with Machina Registry:")
    print("- Store project milestones and decisions")
    print("- Remember complex configuration details")
    print("- Track implementation patterns and solutions")
    print("- Maintain development context across sessions")


def main():
    """Main execution function."""

    print("🔧 Setting up memory-mcp for Machina Registry Service")
    print("=" * 60)

    # Verify installation
    if not verify_memory_mcp_installation():
        print("❌ Please install memory-mcp first")
        return

    # Create memory directory
    if not create_memory_directory():
        print("❌ Failed to create memory directory")
        return

    # Add to Zed configuration
    if not add_memory_mcp_to_zed_config():
        print("❌ Failed to update Zed configuration")
        return

    # Show usage examples
    show_usage_examples()

    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Restart Zed IDE")
    print("2. Try using memory and context tools in your AI assistant")
    print("3. Store important project information for future reference")


if __name__ == "__main__":
    main()
