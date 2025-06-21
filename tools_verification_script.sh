#!/bin/bash
# tools-verification.sh - Comprehensive DevQ.ai Tool Stack Verification
# Must pass before any project work begins

set -e  # Exit on any error

echo "🔍 DevQ.ai Tool Stack Verification"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Error tracking
ERRORS=0
WARNINGS=0

# Function to check command and report
check_command() {
    local cmd="$1"
    local description="$2"
    local required="${3:-true}"
    
    if command -v "$cmd" &> /dev/null; then
        echo -e "${GREEN}✅ $description${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ $description (REQUIRED)${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠️  $description (OPTIONAL)${NC}"
            ((WARNINGS++))
        fi
        return 1
    fi
}

# Function to check Python module
check_python_module() {
    local module="$1"
    local description="$2"
    local required="${3:-true}"
    
    if python3 -c "import $module; print('$module version:', getattr($module, '__version__', 'unknown'))" 2>/dev/null; then
        echo -e "${GREEN}✅ $description${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ $description (REQUIRED)${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠️  $description (OPTIONAL)${NC}"
            ((WARNINGS++))
        fi
        return 1
    fi
}

# Function to check service
check_service() {
    local url="$1"
    local description="$2"
    local required="${3:-true}"
    
    if curl -s --max-time 5 "$url" &> /dev/null; then
        echo -e "${GREEN}✅ $description${NC}"
        return 0
    else
        if [ "$required" = "true" ]; then
            echo -e "${RED}❌ $description (REQUIRED)${NC}"
            ((ERRORS++))
        else
            echo -e "${YELLOW}⚠️  $description (OPTIONAL)${NC}"
            ((WARNINGS++))
        fi
        return 1
    fi
}

echo "🏗️  Core Framework Stack"
echo "========================"

# Core Framework Verification
check_python_module "fastapi" "FastAPI Framework"
check_python_module "pytest" "PyTest Testing Framework"  
check_python_module "logfire" "Logfire Observability"
check_python_module "pydantic_ai" "Pydantic AI Framework"
check_python_module "uvicorn" "Uvicorn ASGI Server"

echo ""
echo "🧪 Testing & Quality Tools"
echo "=========================="

check_command "black" "Black Code Formatter"
check_command "isort" "Import Sorter"
check_command "mypy" "MyPy Type Checker"
check_command "flake8" "Flake8 Linter" false

echo ""
echo "📋 Task Management"
echo "=================="

# TaskMaster AI verification
if npx task-master-ai --version &> /dev/null; then
    echo -e "${GREEN}✅ TaskMaster AI (via NPX)${NC}"
else
    echo -e "${RED}❌ TaskMaster AI (REQUIRED)${NC}"
    ((ERRORS++))
fi

echo ""
echo "🤖 MCP Servers & Tools"
echo "======================"

# Dart MCP Server
if npx dart-mcp-server --help &> /dev/null; then
    echo -e "${GREEN}✅ Dart MCP Server${NC}"
else
    echo -e "${RED}❌ Dart MCP Server (REQUIRED)${NC}"
    ((ERRORS++))
fi

# Core MCP Servers
for server in filesystem git fetch memory sequentialthinking; do
    if npx "@modelcontextprotocol/server-$server" --help &> /dev/null; then
        echo -e "${GREEN}✅ MCP Server: $server${NC}"
    else
        echo -e "${YELLOW}⚠️  MCP Server: $server (will install on first use)${NC}"
        ((WARNINGS++))
    fi
done

echo ""
echo "🧠 Knowledge Base & Context Tools"
echo "=================================="

# Check DevQ.ai environment
if [ -n "$DEVQAI_ROOT" ] && [ -d "$DEVQAI_ROOT" ]; then
    echo -e "${GREEN}✅ DevQ.ai Environment (DEVQAI_ROOT set)${NC}"
else
    echo -e "${RED}❌ DevQ.ai Environment (DEVQAI_ROOT required)${NC}"
    ((ERRORS++))
fi

# Context7 (Redis-based contextual reasoning)
if [ -d "/Users/dionedge/devqai/mcp/mcp-servers/context7-mcp" ]; then
    echo -e "${GREEN}✅ Context7 MCP Server (directory exists)${NC}"
    # Try to import the module
    if PYTHONPATH="/Users/dionedge/devqai" python3 -c "from context7_mcp.server import Context7MCPServer" 2>/dev/null; then
        echo -e "${GREEN}✅ Context7 Python Module${NC}"
    else
        echo -e "${YELLOW}⚠️  Context7 Python Module (check dependencies)${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ Context7 MCP Server (REQUIRED for planning)${NC}"
    ((ERRORS++))
fi

# Ptolemies Knowledge Base
if [ -d "/Users/dionedge/devqai/ptolemies" ]; then
    echo -e "${GREEN}✅ Ptolemies Knowledge Base (directory exists)${NC}"
    # Check if can access CLI
    if PYTHONPATH="/Users/dionedge/devqai" python3 -m ptolemies.cli list | head -1 &> /dev/null; then
        echo -e "${GREEN}✅ Ptolemies CLI Access${NC}"
    else
        echo -e "${YELLOW}⚠️  Ptolemies CLI (check SurrealDB connection)${NC}"
        ((WARNINGS++))
    fi
else
    echo -e "${RED}❌ Ptolemies Knowledge Base (REQUIRED)${NC}"
    ((ERRORS++))
fi

# Bayes Statistical Tools
if [ -d "/Users/dionedge/devqai/bayes" ]; then
    echo -e "${GREEN}✅ Bayes Statistical Tools${NC}"
else
    echo -e "${YELLOW}⚠️  Bayes Statistical Tools${NC}"
    ((WARNINGS++))
fi

echo ""
echo "🗄️  Database Services"
echo "===================="

# SurrealDB
check_service "http://localhost:8000/status" "SurrealDB Service"

# Redis (for Context7)
if [ -n "$UPSTASH_REDIS_REST_URL" ]; then
    echo -e "${GREEN}✅ Redis Configuration (Upstash)${NC}"
else
    echo -e "${YELLOW}⚠️  Redis Configuration (needed for Context7)${NC}"
    ((WARNINGS++))
fi

# Neo4j (optional)
check_service "http://localhost:7474" "Neo4j Service" false

echo ""
echo "🛠️  Development Tools"
echo "===================="

check_command "git" "Git Version Control"
check_command "docker" "Docker" false
check_command "node" "Node.js"
check_command "npm" "NPM Package Manager"
check_command "zed" "Zed IDE" false
check_command "curl" "cURL"

echo ""
echo "🔧 Environment Variables"
echo "========================"

# Check critical environment variables
vars=(
    "DEVQAI_ROOT"
    "ANTHROPIC_API_KEY" 
    "SURREALDB_URL"
    "SURREALDB_USERNAME"
    "SURREALDB_PASSWORD"
    "DART_TOKEN"
)

for var in "${vars[@]}"; do
    if [ -n "${!var}" ]; then
        echo -e "${GREEN}✅ $var${NC}"
    else
        echo -e "${RED}❌ $var (REQUIRED)${NC}"
        ((ERRORS++))
    fi
done

# Optional but recommended
optional_vars=(
    "UPSTASH_REDIS_REST_URL"
    "UPSTASH_REDIS_REST_TOKEN"
    "LOGFIRE_TOKEN"
    "OPENAI_API_KEY"
)

for var in "${optional_vars[@]}"; do
    if [ -n "${!var}" ]; then
        echo -e "${GREEN}✅ $var${NC}"
    else
        echo -e "${YELLOW}⚠️  $var (optional but recommended)${NC}"
        ((WARNINGS++))
    fi
done

echo ""
echo "🧪 Quick Functionality Tests"
echo "============================"

# Test FastAPI import and basic functionality
if python3 -c "
from fastapi import FastAPI
import logfire
app = FastAPI()
print('FastAPI + Logfire integration: OK')
" 2>/dev/null; then
    echo -e "${GREEN}✅ FastAPI + Logfire Integration${NC}"
else
    echo -e "${RED}❌ FastAPI + Logfire Integration${NC}"
    ((ERRORS++))
fi

# Test PyTest basic functionality
if python3 -c "
import pytest
import sys
print('PyTest version:', pytest.__version__)
" 2>/dev/null; then
    echo -e "${GREEN}✅ PyTest Functionality${NC}"
else
    echo -e "${RED}❌ PyTest Functionality${NC}"
    ((ERRORS++))
fi

# Test Pydantic AI import
if python3 -c "
from pydantic_ai import Agent
print('Pydantic AI: OK')
" 2>/dev/null; then
    echo -e "${GREEN}✅ Pydantic AI Import${NC}"
else
    echo -e "${RED}❌ Pydantic AI Import${NC}"
    ((ERRORS++))
fi

echo ""
echo "📊 Verification Summary"
echo "======================"

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical tools verified successfully!${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNINGS optional tools/services not available${NC}"
    fi
    echo -e "${BLUE}✅ Ready for DevQ.ai development!${NC}"
    exit 0
else
    echo -e "${RED}❌ $ERRORS critical issues found${NC}"
    if [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}⚠️  $WARNINGS warnings (optional tools)${NC}"
    fi
    echo ""
    echo -e "${RED}🚫 Cannot proceed with development until critical issues are resolved.${NC}"
    echo ""
    echo "Common fixes:"
    echo "1. Install missing Python packages: pip install fastapi pytest logfire pydantic-ai"
    echo "2. Install TaskMaster AI: npm install -g task-master-ai"
    echo "3. Start SurrealDB: surreal start --user root --pass root --bind 0.0.0.0:8000 memory"
    echo "4. Set environment variables in .env file"
    echo "5. Source DevQ.ai environment: source .zshrc.devqai"
    exit 1
fi