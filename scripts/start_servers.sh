#!/bin/bash

# This script starts all production-ready MCP servers sequentially.

# List of production-ready servers
servers=(
    "agentql-mcp"
    "aws-core-mcp-server"
    "bayes-mcp"
    "brightdata-mcp"
    "browser-tools-context-server"
    "calendar-mcp"
    "darwin-mcp"
    "docker-mcp"
    "fastmcp-mcp"
    "gcp-mcp"
    "github-mcp"
    "gmail-mcp"
    "jupyter-mcp"
    "logfire-mcp"
    "mcp-cerebra-legal"
    "memory-mcp"
    "mcp-server-buildkite"
    "mcp-server-github"
    "ptolemies-mcp-server"
    "pulumi-mcp-server"
    "puppeteer-mcp"
    "scholarly-mcp"
    "shadcn-ui-mcp-server"
    "shopify-mcp"
    "solver-mzn-mcp"
    "solver-pysat-mcp"
    "solver-z3-mcp"
    "stripe-mcp"
    "task-master"
    "time-mcp"
    "upstash-mcp"
    "wikidata-mcp"
)

port=8001

for server_name in "${servers[@]}"; do
    echo "Starting $server_name on port $port"
    uvicorn mcp.mcp-servers.$server_name.src.server:app --host 0.0.0.0 --port $port &
    port=$((port+1))
done

echo "All servers started."
