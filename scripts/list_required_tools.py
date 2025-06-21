#!/usr/bin/env python3
"""
List Required Tools Script

This script reads the tools/tools.md file and lists all tools that have 'required: true'.
It provides both a count and the actual list of required tools.

Usage:
    python scripts/list_required_tools.py
    python scripts/list_required_tools.py --format=csv
    python scripts/list_required_tools.py --count-only
"""

import argparse
import sys
from pathlib import Path
from typing import List, Set, Tuple


def parse_tools_md(file_path: Path) -> Tuple[List[str], int]:
    """
    Parse tools.md file and extract tools with required: true.

    Returns:
        Tuple of (unique_tools_list, total_records_count)
    """
    if not file_path.exists():
        print(f"Error: {file_path} not found")
        return [], 0

    required_tools = []
    current_tool = None
    total_records = 0

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and the required_tools summary line
                if not line or line.startswith('required_tools:'):
                    continue

                # Detect tool definition
                if line.startswith('tool:'):
                    current_tool = line[5:].strip()
                    continue

                # Check for required: true
                if line == 'required: true' and current_tool:
                    required_tools.append(current_tool)
                    total_records += 1

    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return [], 0

    # Get unique tools (in case of duplicates)
    unique_tools = list(dict.fromkeys(required_tools))  # Preserves order

    return unique_tools, total_records


def format_output(tools: List[str], total_records: int, format_type: str = 'list') -> str:
    """Format the output based on the requested format."""

    if format_type == 'count-only':
        return f"Total required tools: {len(tools)} unique ({total_records} total records)"

    elif format_type == 'csv':
        result = f"# Required tools ({len(tools)} unique, {total_records} total records)\n"
        result += ', '.join(tools)
        return result

    elif format_type == 'list':
        result = f"Required Tools Analysis\n"
        result += f"=====================\n\n"
        result += f"Unique required tools: {len(tools)}\n"
        result += f"Total required records: {total_records}\n"

        if total_records > len(tools):
            duplicates = total_records - len(tools)
            result += f"Duplicate entries: {duplicates}\n"

        result += f"\nRequired Tools List:\n"
        result += f"-------------------\n"

        for i, tool in enumerate(tools, 1):
            result += f"{i:2d}. {tool}\n"

        return result

    else:
        return "Unknown format type"


def update_required_tools_line(file_path: Path, tools: List[str]) -> bool:
    """Update the first line of tools.md with the current required tools list."""

    if not file_path.exists():
        return False

    try:
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Create new required_tools line
        new_first_line = f"required_tools: {', '.join(tools)}\n"

        # Update or add the required_tools line
        if lines and lines[0].startswith('required_tools:'):
            lines[0] = new_first_line
        else:
            lines.insert(0, new_first_line)
            lines.insert(1, '\n')  # Add blank line after

        # Write back to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)

        return True

    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='List tools with required: true from tools.md',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/list_required_tools.py
  python scripts/list_required_tools.py --format=csv
  python scripts/list_required_tools.py --count-only
  python scripts/list_required_tools.py --update-first-line
        """
    )

    parser.add_argument(
        '--format',
        choices=['list', 'csv', 'count-only'],
        default='list',
        help='Output format (default: list)'
    )

    parser.add_argument(
        '--update-first-line',
        action='store_true',
        help='Update the first line of tools.md with current required tools'
    )

    parser.add_argument(
        '--tools-file',
        type=Path,
        default=Path('tools/tools.md'),
        help='Path to tools.md file (default: tools/tools.md)'
    )

    args = parser.parse_args()

    # Parse the tools.md file
    tools, total_records = parse_tools_md(args.tools_file)

    if not tools:
        print("No required tools found or error reading file.")
        sys.exit(1)

    # Update first line if requested
    if args.update_first_line:
        if update_required_tools_line(args.tools_file, tools):
            print(f"✅ Updated required_tools line in {args.tools_file}")
        else:
            print(f"❌ Failed to update {args.tools_file}")
            sys.exit(1)

    # Generate and print output
    output = format_output(tools, total_records, args.format)
    print(output)

    # Return appropriate exit code
    sys.exit(0)


if __name__ == '__main__':
    main()
