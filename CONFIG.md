# DEVQ.AI MASTER ENVIRONMENT VARIABLES FILE

### ==========================================================================
### AGENTICAL CONFIGURATION
### ==========================================================================

AGENTICAL_API_HOST=0.0.0.0
AGENTICAL_API_PORT=8080
AGENTICAL_API_DEBUG=false
AGENTICAL_API_CORS_ORIGINS=
AGENTICAL_MAX_CONCURRENT_AGENTS=10
AGENTICAL_MAX_WORKFLOW_STEPS=100
AGENTICAL_WORKFLOW_TIMEOUT=3600

### ==========================================================================
### CRAWLER CONFIGURATION
### ==========================================================================

CRAWLER_MAX_DEPTH=3
CRAWLER_MAX_PAGES=100
CRAWLER_DELAY_MS=1000
CRAWLER_RESPECT_ROBOTS_TXT=true
CRAWLER_USER_AGENT="Ptolemies Knowledge Crawler/1.0"

### ==========================================================================
### DATABASE CONFIGURATION
### ==========================================================================

UPSTASH_REDIS_REST_URL=https://redis-10892.c124.us-central1-1.gce.redns.redis-cloud.com:10892
UPSTASH_REDIS_REST_TOKEN=${UPSTASH_REDIS_REST_TOKEN}

NEO4J_URI=http://localhost:7474
NEO4J_BOLT_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=Ptolemis
NEO4J_PROJECT=Ptolemis

UPSTASH_REDIS_ENDPOINT="redis-cli --tls -u redis://default:"
UPSTASH_REDIS_VECTOR_ENDPOINT=https://resolved-moth-39824-us1-vector.upstash.io
UPSTASH_VECTOR_DIMENSION_COUNT=384
UPSTASH_VECTOR_SIMULARITY_FUCTION=COSINE
QSTASH_URL=https://qstash.upstash.io
DESTINATION_URL=https://devq.ai/api
UPSTASH_SEARCH_SEARCH=devq-ai-search
UPSTASH_SEARCH_ENDPOINT=https://top-earwig-79587-gcp-usc1-search.upstash.io

### ==========================================================================
### EMBEDDING SETTINGS
### ==========================================================================

EMBEDDING_PROVIDER=${OPENAI_API_KEY}
EMBEDDING_MODEL=text-embedding-3-large
EMBEDDING_DIMENSIONS=1536
EMBEDDING_BATCH_SIZE=100
AGENTICAL_EMBEDDING_PROVIDER=${OPENAI_API_KEY}
AGENTICAL_EMBEDDING_MODEL=text-embedding-ada-002
AGENTICAL_EMBEDDING_API_KEY=${OPENAI_API_KEY}
AGENTICAL_EMBEDDING_DIMENSION=1536

### ==========================================================================
### ENVIRONMENT SETTINGS
### ==========================================================================

NODE_ENV=development
AGENTICAL_ENV=development
PORT=3000
LOG_LEVEL=info
DEBUG=false
AGENTICAL_DEBUG=true

### ==========================================================================
### LOGFIRE CONFIGURATION
### ==========================================================================

LOGFIRE_PROJECT_URL=https://logfire-us.pydantic.dev/devq-ai/devq-ai
LOGFIRE_API_URL=https://logfire-us.pydantic.dev
LOGFIRE_PROJECT=devq-ai

### ==========================================================================
### MCP (MODEL CONTEXT PROTOCOL) CONFIGURATION
### ==========================================================================

MCP_SERVER_HOST=localhost
MCP_SERVER_PORT=8080
MCP_REGISTRY_URL=https://registry.mcp-protocol.org
MCP_DEBUG=true
MCP_LOG_LEVEL=info

### ==========================================================================
### MONITORING & TELEMETRY
### ==========================================================================

OPENTELEMETRY_ENDPOINT=http://localhost:4317

### ==========================================================================
### SLACK CONFIGURATION
### ==========================================================================

SLACK_CHANNEL_IDS=C08UH4VKEM7
SLACK_TEAM_ID=C06GWGQS4B0

### ==========================================================================
### VERSION CONTROL
### ==========================================================================

GITHUB_API_TOKEN=${GITHUB_PAT}
GITHUB_TOKEN=${GITHUB_PAT}
GITHUB_PERSONAL_ACCESS_TOKEN=${GITHUB_PAT}

GITHUB_MONOREPO=https://github.com/devq-ai
GITHUB_AGENTS=https://github.com/devq-ai/agentical
GITHUB_BUILDER=https://github.com/devq-ai/devgen
GITHUB_KNOWLEDGE=https://github.com/devq-ai/ptolemies
GITHUB_MCPhttps://github.com/devq-ai/mcp
