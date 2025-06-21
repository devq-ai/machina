#!/bin/zsh

# Zed IDE specific zsh configuration for DevQ.ai
# This file is loaded when Zed starts a new terminal session

# Configure Powerlevel10k instant prompt to suppress warnings but keep verbose output
if [[ -n "$ZSH_VERSION" ]]; then
    typeset -g POWERLEVEL9K_INSTANT_PROMPT=quiet
fi

# Set DevQ.ai environment variables
export DEVQAI_ROOT="/Users/dionedge/devqai"
export PYTHONPATH="$DEVQAI_ROOT:$PYTHONPATH"
export MCP_SERVERS_PATH="$DEVQAI_ROOT/mcp/mcp-servers"
export PTOLEMIES_PATH="$DEVQAI_ROOT/ptolemies"

# Add DevQ.ai bin directory to PATH
if [[ -d "$DEVQAI_ROOT/bin" ]]; then
    export PATH="$DEVQAI_ROOT/bin:$PATH"
fi

# Database configuration
export SURREALDB_URL="ws://localhost:8000/rpc"
export SURREALDB_USERNAME="root"
export SURREALDB_PASSWORD="root"
export SURREALDB_NAMESPACE="ptolemies"
export SURREALDB_DATABASE="knowledge"

# Logfire configuration
export LOGFIRE_PROJECT_NAME="devq-ai-development"
export LOGFIRE_SERVICE_NAME="devq-ai-zed"

# Development tool configuration
export FASTAPI_ENV="development"
export DEBUG="true"
export UVICORN_HOST="0.0.0.0"
export UVICORN_PORT="8000"
export COVERAGE_THRESHOLD="90"
export BLACK_LINE_LENGTH="88"
export ISORT_PROFILE="black"

# Testing configuration
export PYTEST_CURRENT_TEST="1"
export PYTEST_CACHE_DIR="/tmp/pytest_cache"
export MYPY_CACHE_DIR="/tmp/mypy_cache"

# Source the main zshrc if it exists (only in zsh)
if [[ -n "$ZSH_VERSION" && -f "$HOME/.zshrc" ]]; then
    source "$HOME/.zshrc" 2>/dev/null || true
fi

# Source DevQ.ai specific configuration
if [[ -f "$DEVQAI_ROOT/.zshrc.devqai" ]]; then
    source "$DEVQAI_ROOT/.zshrc.devqai" 2>/dev/null || true
fi

# Note: We don't change directories automatically to respect the starting location
# Use navigation aliases (ag, bayes, darwin, nash, ptolemies) to move around DevQ.ai

# Auto-activate virtual environment if it exists
if [[ -f "venv/bin/activate" ]] && [[ -z "$VIRTUAL_ENV" ]]; then
    source venv/bin/activate
    echo "🐍 Activated virtual environment: venv"

    # Verify activation was successful
    if [[ -n "$VIRTUAL_ENV" ]] && [[ "$PATH" == *"$VIRTUAL_ENV"* ]]; then
        # Small delay to ensure environment is fully loaded
        sleep 0.2
    else
        echo "⚠️  Virtual environment activation may have failed"
    fi
fi

# DevQ.ai specific aliases and functions
alias pytest-devq="pytest tests/ --cov=src/ --cov-report=html --cov-fail-under=90"
alias fastapi-run="uvicorn main:app --reload --host 0.0.0.0 --port 8000"
logfire-check() {
    if [[ -n "$VIRTUAL_ENV" ]]; then
        # In virtual environment, check directly
        if "$VIRTUAL_ENV/bin/python" -c "import logfire" >/dev/null 2>&1; then
            logfire_version=$("$VIRTUAL_ENV/bin/python" -c "import logfire; print(logfire.__version__)" 2>/dev/null || echo "unknown")
            echo "✅ Logfire available, version: $logfire_version"
        else
            echo "⚠️ Logfire not available"
        fi
    else
        # No virtual environment, check system python
        if python -c "import logfire" >/dev/null 2>&1; then
            logfire_version=$(python -c "import logfire; print(logfire.__version__)" 2>/dev/null || echo "unknown")
            echo "✅ Logfire available, version: $logfire_version"
        else
            echo "⚠️ Logfire not available"
        fi
    fi
}
alias taskmaster-check="npx task-master-ai --version"

# DevQ.ai info display function (can be called manually)
alias devq-info='$DEVQAI_ROOT/devgen/.zed/devq-info.sh'

# DevQ.ai environment reload function
devq-reload() {
    echo "🔄 Reloading DevQ.ai environment..."

    # Source the DevQ.ai zshrc configuration
    if [[ -f "/Users/dionedge/devqai/devgen/.zed/.zshrc" ]]; then
        source "/Users/dionedge/devqai/devgen/.zed/.zshrc"
        echo "✅ DevQ.ai configuration reloaded"
    else
        echo "⚠️  DevQ.ai zshrc not found"
    fi
}

# Tools reporting function
tools-report() {
    if [[ -f "scripts/generate_tools_report.py" ]]; then
        python scripts/generate_tools_report.py
        echo "📖 View full report: cat tools/tools_report.md"
    else
        echo "⚠️  Tools report script not found: scripts/generate_tools_report.py"
        echo "   Please run from a project directory with the script"
    fi
}

# Git aliases for DevQ.ai workflow
alias gst="git status"
alias gco="git checkout"
alias gcb="git checkout -b"
alias gaa="git add ."
alias gcm="git commit -m"
alias gp="git push"
alias gpl="git pull"
alias gl="git log --oneline -10"
alias gb="git branch"
alias gd="git diff"
alias gds="git diff --staged"

# Python environment management
alias venv-create="python3 -m venv venv"
alias venv-activate="source venv/bin/activate"
alias venv-deactivate="deactivate"
alias pip-freeze="pip freeze > requirements.txt"
alias pip-install="pip install -r requirements.txt"
alias pip-upgrade="pip install --upgrade pip"

# DevQ.ai specific Python functions
devq-setup() {
    echo "🔧 Setting up DevQ.ai Python environment..."
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    fi
    source venv/bin/activate
    pip install --upgrade pip
    # Install DevQ.ai standard packages
    pip install "logfire[fastapi]" fastapi uvicorn pytest pytest-cov
    if [[ -f "requirements.txt" ]]; then
        pip install -r requirements.txt
        echo "✅ Requirements installed"
    fi
    echo "🚀 DevQ.ai Python environment ready"
}

# TaskMaster AI integration functions
task-list() {
    echo "📋 Current TaskMaster AI tasks:"
    if command -v task-master >/dev/null 2>&1; then
        task-master list
    else
        npx task-master-ai list
    fi
}

task-next() {
    echo "🎯 Next task to work on:"
    if command -v task-master >/dev/null 2>&1; then
        task-master next
    else
        npx task-master-ai next
    fi
}

task-add() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: task-add \"task description\""
        return 1
    fi
    local prompt="$1"
    echo "➕ Adding new task: $prompt"
    if command -v task-master >/dev/null 2>&1; then
        task-master add-task --prompt="$prompt" --research
    else
        npx task-master-ai add-task --prompt="$prompt" --research
    fi
}

task-done() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: task-done <task-id>"
        return 1
    fi
    local task_id="$1"
    echo "✅ Marking task $task_id as done"
    if command -v task-master >/dev/null 2>&1; then
        task-master set-status --id="$task_id" --status=done
    else
        npx task-master-ai set-status --id="$task_id" --status=done
    fi
}

task-show() {
    if [[ $# -eq 0 ]]; then
        echo "Usage: task-show <task-id>"
        return 1
    fi
    local task_id="$1"
    echo "📄 Task details for ID: $task_id"
    if command -v task-master >/dev/null 2>&1; then
        task-master show "$task_id"
    else
        npx task-master-ai show "$task_id"
    fi
}

task-complexity() {
    echo "🧮 Analyzing project complexity..."
    if command -v task-master >/dev/null 2>&1; then
        task-master analyze-complexity --research
    else
        npx task-master-ai analyze-complexity --research
    fi
}

devq-test() {
    echo "🧪 Running DevQ.ai test suite..."
    if [[ -d "tests" ]]; then
        pytest tests/ --cov=src/ --cov-report=html --cov-fail-under=90 -v
    else
        echo "⚠️  No tests directory found"
    fi
}

devq-clean() {
    echo "🧹 Cleaning DevQ.ai project..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete 2>/dev/null
    find . -type f -name "*.pyo" -delete 2>/dev/null
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null
    echo "✅ Project cleaned"
}

# Quick navigation aliases (changes directory)
alias devq-root="cd $DEVQAI_ROOT && pwd"
alias ag="cd $DEVQAI_ROOT/ag && pwd"
alias bayes="cd $DEVQAI_ROOT/bayes && pwd"
alias darwin="cd $DEVQAI_ROOT/darwin && pwd"
alias nash="cd $DEVQAI_ROOT/nash && pwd"
alias ptolemies="cd $DEVQAI_ROOT/ptolemies && pwd"

# MCP server management functions
start-context7() {
    cd "$DEVQAI_ROOT/mcp/mcp-servers/context7-mcp"
    python -m context7_mcp.server
}

start-crawl4ai() {
    cd "$DEVQAI_ROOT/mcp/mcp-servers/crawl4ai-mcp"
    python -m crawl4ai_mcp.server
}

mcp-inspect() {
    if [[ $# -eq 0 ]]; then
        echo "🔧 Available MCP servers:"
        echo "  Core: taskmaster-ai, memory, filesystem, git, fetch, sequentialthinking"
        echo "  DevQ.ai: context7, ptolemies, bayes, surrealdb"
        echo "  Optional: crawl4ai, github, orchestrator, magic, shadcn-ui, registry"
        echo ""
        echo "Usage: mcp-inspect <server-name>"
        echo "Example: mcp-inspect taskmaster-ai"
        return 1
    fi

    local server=$1
    echo "🔍 Inspecting MCP server: $server"
    echo ""

    case $server in
        taskmaster-ai)
            echo "📋 TaskMaster AI - Task management and workflow automation"
            echo "Status: $(npx task-master-ai --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            echo "Usage: npx task-master-ai [command]"
            ;;
        memory)
            echo "🧠 Memory - Persistent context management"
            echo "Status: $(npx @modelcontextprotocol/server-memory --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            ;;
        filesystem)
            echo "📁 Filesystem - File operations"
            echo "Status: $(npx @modelcontextprotocol/server-filesystem --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            ;;
        git)
            echo "🌿 Git - Version control integration"
            echo "Status: $(npx @modelcontextprotocol/server-git --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            ;;
        fetch)
            echo "🌐 Fetch - HTTP/API requests"
            echo "Status: $(npx @modelcontextprotocol/server-fetch --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            ;;
        sequentialthinking)
            echo "🧠 Sequential Thinking - Step-by-step reasoning"
            echo "Status: $(npx @modelcontextprotocol/server-sequentialthinking --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            ;;
        context7)
            echo "🧠 Context7 - Contextual reasoning with Redis"
            echo "Directory: $DEVQAI_ROOT/mcp/mcp-servers/context7-mcp"
            echo "Status: $(test -d "$DEVQAI_ROOT/mcp/mcp-servers/context7-mcp" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            if [[ -d "$DEVQAI_ROOT/mcp/mcp-servers/context7-mcp" ]]; then
                echo "Test: $(cd "$DEVQAI_ROOT/mcp/mcp-servers/context7-mcp" && python -c "import context7_mcp.server; print('✅ Module loads')" 2>/dev/null || echo '❌ Module import failed')"
            fi
            ;;
        ptolemies)
            echo "📚 Ptolemies - Knowledge base and semantic search"
            echo "Directory: $DEVQAI_ROOT/ptolemies"
            echo "Status: $(test -d "$DEVQAI_ROOT/ptolemies" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            if [[ -d "$DEVQAI_ROOT/ptolemies" ]]; then
                echo "Test: $(cd "$DEVQAI_ROOT/ptolemies" && python -c "import ptolemies.mcp.ptolemies_mcp; print('✅ Module loads')" 2>/dev/null || echo '❌ Module import failed')"
            fi
            ;;
        bayes)
            echo "📊 Bayes - Bayesian analysis and statistical modeling"
            echo "Directory: $DEVQAI_ROOT/bayes"
            echo "Status: $(test -d "$DEVQAI_ROOT/bayes" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            if [[ -d "$DEVQAI_ROOT/bayes" ]]; then
                echo "Test: $(cd "$DEVQAI_ROOT/bayes" && python -c "import bayes_mcp; print('✅ Module loads')" 2>/dev/null || echo '❌ Module import failed')"
            fi
            ;;
        surrealdb)
            echo "🗄️  SurrealDB - Multi-model database operations"
            echo "Directory: $DEVQAI_ROOT/mcp/mcp-servers/surrealdb-mcp"
            echo "Status: $(test -d "$DEVQAI_ROOT/mcp/mcp-servers/surrealdb-mcp" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            if [[ -d "$DEVQAI_ROOT/mcp/mcp-servers/surrealdb-mcp" ]]; then
                echo "Test: $(cd "$DEVQAI_ROOT/mcp/mcp-servers/surrealdb-mcp" && python -c "import surrealdb_mcp.server; print('✅ Module loads')" 2>/dev/null || echo '❌ Module import failed')"
            fi
            ;;
        crawl4ai)
            echo "🕷️  Crawl4AI - Web scraping and content extraction"
            echo "Directory: $DEVQAI_ROOT/mcp/mcp-servers/crawl4ai-mcp"
            echo "Status: $(test -d "$DEVQAI_ROOT/mcp/mcp-servers/crawl4ai-mcp" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            ;;
        github)
            echo "🐙 GitHub - Repository management and integration"
            echo "Status: $(npx @modelcontextprotocol/server-github --version 2>/dev/null && echo '✅ Available' || echo '❌ Not available')"
            echo "Type: NPM package"
            ;;
        orchestrator)
            echo "🎭 Orchestrator - Multi-agent coordination"
            echo "Directory: $DEVQAI_ROOT/.claude"
            echo "Status: $(test -d "$DEVQAI_ROOT/.claude" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            ;;
        magic|shadcn-ui|registry)
            echo "🛠️  $server - Development utility"
            echo "Directory: $DEVQAI_ROOT/mcp/mcp-servers/$server-mcp"
            echo "Status: $(test -d "$DEVQAI_ROOT/mcp/mcp-servers/$server-mcp" && echo '✅ Directory exists' || echo '❌ Directory missing')"
            echo "Type: Python module"
            ;;
        *)
            echo "❌ Unknown MCP server: $server"
            echo ""
            echo "💡 Try: mcp-inspect (without arguments) to see available servers"
            return 1
            ;;
    esac

    echo ""
    echo "💡 Tip: Run 'tools-report' for complete MCP tools status"
}

# Function to get required MCP servers dynamically
get_required_mcp_servers() {
    local required_tools=""

    # First try to read from tools.md first line (fastest)
    if [[ -f "tools/tools.md" ]]; then
        local first_line=$(head -n 1 "tools/tools.md" 2>/dev/null)
        if [[ "$first_line" =~ ^required_tools: ]]; then
            required_tools="${first_line#required_tools: }"
        fi
    fi

    # Fallback if first line method fails
    if [[ -z "$required_tools" ]]; then
        required_tools="bayes, context7, fetch, filesystem, git, memory, ptolemies, sequentialthinking, surrealdb, taskmaster-ai"
    fi

    echo "$required_tools"
}

# Function to display startup information
devq_show_info() {
    echo "🚀 DevQ.ai Environment Loaded"
    echo "🧪 Testing: pytest-devq, devq-test (full test suite)"
    echo "🔥 Logfire: Always instrument with logfire.span()"
    echo "🔧 Required MCP Servers: $(get_required_mcp_servers)"
    echo "   Use mcp-inspect <server-name> for details"
    echo "🐍 Python: devq-setup, devq-clean, venv-* commands"
    echo "📋 Tasks: task-list, task-next, task-add, task-done, task-show"
    echo "📁 Current directory: $(pwd)"

    # Quick health check
    if command -v task-master >/dev/null 2>&1 || command -v npx >/dev/null 2>&1; then
        echo "✅ TaskMaster AI available"
    else
        echo "⚠️  TaskMaster AI not found"
    fi

    # Check logfire availability more reliably with better timing
    logfire_status=""

    # Give virtual environment a moment to fully initialize if just activated
    if [[ -n "$VIRTUAL_ENV" ]] && [[ -f "venv/bin/activate" ]]; then
        sleep 0.1
    fi

    if [[ -n "$VIRTUAL_ENV" ]]; then
        # In virtual environment, check directly with explicit path
        if "$VIRTUAL_ENV/bin/python" -c "import logfire" >/dev/null 2>&1; then
            logfire_version=$("$VIRTUAL_ENV/bin/python" -c "import logfire; print(logfire.__version__)" 2>/dev/null || echo "unknown")
            logfire_status="✅ Logfire available (v$logfire_version)"
        else
            logfire_status="⚠️  Logfire not available - run 'devq-setup' to install"
        fi
    else
        # No virtual environment, check system python
        if python -c "import logfire" >/dev/null 2>&1; then
            logfire_version=$(python -c "import logfire; print(logfire.__version__)" 2>/dev/null || echo "unknown")
            logfire_status="✅ Logfire available (v$logfire_version)"
        else
            logfire_status="⚠️  Logfire not available - run 'devq-setup' to install"
        fi
    fi
    echo "$logfire_status"

    # Check if we're in a virtual environment
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "🐍 Virtual environment: $(basename $VIRTUAL_ENV)"
    fi

    # Show git branch if in a git repository
    if git rev-parse --git-dir > /dev/null 2>&1; then
        branch=$(git branch --show-current 2>/dev/null)
        if [[ -n "$branch" ]]; then
            echo "🌿 Git branch: $branch"
        fi
    fi
}

# Display startup information only if in interactive mode
if [[ $- == *i* ]]; then
    devq_show_info
fi

# Set prompt for DevQ.ai development
if [[ -n "$ZSH_VERSION" ]]; then
    autoload -U colors && colors

    # Function to get git branch
    git_branch() {
        if git rev-parse --git-dir > /dev/null 2>&1; then
            branch=$(git branch --show-current 2>/dev/null)
            if [[ -n "$branch" ]]; then
                echo " %{$fg[yellow]%}($branch)%{$reset_color%}"
            fi
        fi
    }

    # Function to show virtual environment
    venv_info() {
        if [[ -n "$VIRTUAL_ENV" ]]; then
            echo " %{$fg[blue]%}[$(basename $VIRTUAL_ENV)]%{$reset_color%}"
        fi
    }

    # Set the prompt with git and venv info (only in zsh)
    if [[ -n "$ZSH_VERSION" ]]; then
        setopt PROMPT_SUBST
        PROMPT="%{$fg[cyan]%}[DevQ.ai]%{$reset_color%}$(venv_info)$(git_branch) %{$fg[green]%}%~%{$reset_color%} %# "
    fi
fi
