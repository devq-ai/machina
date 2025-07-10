#!/bin/bash

# DevQ.ai Environment Information Display
# This script shows the current DevQ.ai environment status and available tools
# Works in bash, zsh, and other POSIX shells

echo "🚀 DevQ.ai Environment Loaded"
echo "🧪 Testing: pytest-devq, devq-test (full test suite)"
echo "🔥 Logfire: Always instrument with logfire.span()"
# Get required tools dynamically from tools.md
required_tools=""

# Read from tools.md required_tools line (line 4 based on current structure)
if [[ -f "tools/tools.md" ]]; then
    # Look for the required_tools line specifically
    required_line=$(grep "^required_tools:" "tools/tools.md" 2>/dev/null)
    if [[ -n "$required_line" ]]; then
        required_tools="${required_line#required_tools: }"
        # Count the tools
        tool_count=$(echo "$required_tools" | tr ',' '\n' | wc -l | tr -d ' ')
        echo "🔧 Required Tools ($tool_count): $required_tools"
    else
        echo "⚠️  Could not read required tools from tools.md"
    fi
else
    echo "⚠️  tools/tools.md not found"
fi
echo "   Use mcp-inspect <server-name> for details"
echo "🐍 Python: devq-setup, devq-clean, venv-* commands"
echo "📋 Tasks: task-next, task-add, task-done, task-show"
echo "📁 Current directory: $(pwd)"

# Check TaskMaster AI availability
if command -v task-master >/dev/null 2>&1 || command -v npx >/dev/null 2>&1; then
    if npx task-master-ai --version >/dev/null 2>&1; then
        echo "✅ TaskMaster AI available"
    else
        echo "⚠️  TaskMaster AI not found"
    fi
else
    echo "⚠️  TaskMaster AI not found"
fi

# Check Logfire availability
if [[ -n "$VIRTUAL_ENV" ]]; then
    # In virtual environment, check directly with explicit path
    if "$VIRTUAL_ENV/bin/python" -c "import logfire" >/dev/null 2>&1; then
        logfire_version=$("$VIRTUAL_ENV/bin/python" -c "import logfire; print(logfire.__version__)" 2>/dev/null || echo "unknown")
        echo "✅ Logfire available (v$logfire_version)"
    else
        echo "⚠️  Logfire not available - run 'devq-setup' to install"
    fi
else
    # No virtual environment, check system python
    if python -c "import logfire" >/dev/null 2>&1; then
        logfire_version=$(python -c "import logfire; print(logfire.__version__)" 2>/dev/null || echo "unknown")
        echo "✅ Logfire available (v$logfire_version)"
    else
        echo "⚠️  Logfire not available - run 'devq-setup' to install"
    fi
fi

# Check virtual environment status
if [[ -n "$VIRTUAL_ENV" ]]; then
    echo "🐍 Virtual environment: $(basename $VIRTUAL_ENV)"
else
    echo "🐍 No virtual environment active"
fi

# Check git branch if in a git repository
if git rev-parse --git-dir > /dev/null 2>&1; then
    branch=$(git branch --show-current 2>/dev/null)
    if [[ -n "$branch" ]]; then
        echo "🌿 Git branch: $branch"
    fi
fi
