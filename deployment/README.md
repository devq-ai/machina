# MCP Servers Deployment Guide

Simple deployment guide for running MCP servers with Docker Compose.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+
- Environment variables configured in `.env` file

## Quick Start

1. **Set up environment variables**

   Copy the example environment file and update with your values:
   ```bash
   cd deployment/docker
   cp .env.example .env
   # Edit .env with your API keys and configuration
   ```

2. **Start the servers**

   ```bash
   cd deployment/docker
   docker-compose up -d
   ```

3. **Check server status**

   ```bash
   docker-compose ps
   docker-compose logs -f
   ```

4. **Run integration tests**

   From the machina directory:
   ```bash
   python run_integration_tests.py
   ```

## Available MCP Servers

| Server | Port | Description |
|--------|------|-------------|
| stripe-mcp | 8001 | Stripe payment processing |
| shopify-mcp | 8002 | Shopify e-commerce integration |
| darwin-mcp | 8003 | Genetic algorithm optimization |
| docker-mcp | 8004 | Docker container management |
| fastmcp-mcp | 8005 | FastMCP framework |
| bayes-mcp | 8006 | Bayesian inference |
| upstash-mcp | 8007 | Upstash Redis/Vector database |
| calendar-mcp | 8008 | Google Calendar integration |
| gmail-mcp | 8009 | Gmail integration |
| gcp-mcp | 8010 | Google Cloud Platform |
| github-mcp | 8011 | GitHub repository management |
| memory-mcp | 8012 | Persistent memory storage |
| logfire-mcp | 8013 | Logfire observability |
| mcp-cerebra-legal | 8014 | Enterprise legal reasoning and analysis |

## Testing

### Run all tests
```bash
python run_integration_tests.py
```

### Run tests without Docker
```bash
python run_integration_tests.py --no-docker
```

### Keep servers running after tests
```bash
python run_integration_tests.py --keep-running
```

### Run specific tests
```bash
cd machina
python -m pytest tests/integration/test_mcp_servers.py -v
```

## Managing Servers

### Start specific servers
```bash
docker-compose up -d stripe-mcp shopify-mcp
```

### Stop all servers
```bash
docker-compose down
```

### View logs
```bash
# All servers
docker-compose logs -f

# Specific server
docker-compose logs -f stripe-mcp
```

### Restart a server
```bash
docker-compose restart stripe-mcp
```

## Environment Variables

Each server may require specific environment variables. See `.env.example` for the complete list. Key variables include:

- `STRIPE_API_KEY` - Stripe API key
- `SHOPIFY_ACCESS_TOKEN` - Shopify access token
- `GITHUB_TOKEN` - GitHub personal access token
- `GOOGLE_CALENDAR_CREDENTIALS` - Google Calendar service account
- `UPSTASH_REDIS_REST_URL` - Upstash Redis URL
- `LOGFIRE_TOKEN` - Logfire API token

## Troubleshooting

### Server won't start
- Check Docker logs: `docker-compose logs <server-name>`
- Verify environment variables are set correctly
- Ensure ports are not already in use

### Connection refused errors
- Wait for servers to fully start (10-15 seconds)
- Check if Docker containers are running: `docker ps`
- Verify network connectivity

### API errors
- Check that API keys/tokens are valid
- Review server logs for detailed error messages
- Ensure required services (Redis, PostgreSQL) are running

## Development

### Building images
```bash
docker-compose build
```

### Running with local code changes
Mount your local code as a volume in docker-compose.yml:
```yaml
volumes:
  - ../../mcp_implementations:/app/mcp_implementations
```

### Accessing server shells
```bash
docker exec -it stripe-mcp /bin/bash
```

## Support

For issues or questions:
1. Check server logs
2. Verify environment configuration
3. Review integration test output
4. See implementation documentation in `/mcp_implementations`
