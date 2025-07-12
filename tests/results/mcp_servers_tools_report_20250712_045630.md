# MCP Servers Tools Report

Generated: 2025-07-12T04:56:30.126722

## Summary

- **Total Servers**: 13
- **Successful Initializations**: 13
- **Servers with Tools Capability**: 13
- **Servers with Working tools/list**: 13

## Tool Details

### surrealdb_mcp (10 tools)

- **surrealdb_health_check**: Check SurrealDB connectivity and database status.
- **execute_sql_query**: Execute a custom SurrealDB SQL query.
- **create_record**: Create a new record in a SurrealDB table.
- **select_records**: Select records from a SurrealDB table.
- **update_record**: Update a record in a SurrealDB table.
- **delete_record**: Delete a record from a SurrealDB table.
- **create_graph_relation**: Create a graph relationship between two records.
- **vector_search**: Perform vector similarity search.
- **get_database_schema**: Get the database schema information.
- **count_records**: Count records in a table with optional filter.

### sequential_thinking_mcp (9 tools)

- **thinking_health_check**: Check sequential thinking engine health.
- **create_thinking_workflow**: Create a new sequential thinking workflow.
- **add_thinking_step**: Add a thinking step to a workflow.
- **execute_thinking_step**: Execute a specific thinking step.
- **get_workflow_status**: Get the status of a thinking workflow.
- **analyze_problem**: Analyze a problem and optionally generate thinking steps.
- **execute_workflow**: Execute all steps in a thinking workflow.
- **list_workflows**: List all thinking workflows.
- **get_reasoning_templates**: Get templates for different reasoning modes.

### registry_mcp (8 tools)

- **registry_health_check**: Check registry health and return status.
- **list_servers**: List all registered MCP servers with optional filtering.
- **get_server_info**: Get detailed information about a specific server.
- **get_production_servers**: Get all servers marked as required in production.
- **get_server_status**: Get comprehensive server status and statistics.
- **search_servers**: Search servers by filename, description, or repository.
- **validate_registry**: Validate registry data for consistency and completeness.
- **get_framework_stats**: Get statistics about framework distribution.

### server_template (5 tools)

- **health_check**: Check server health and return status.
- **get_server_info**: Get detailed server information.
- **echo_message**: Echo a message the specified number of times.
- **list_capabilities**: List all available server capabilities.
- **test_error_handling**: Test error handling capabilities.

### docker_mcp (7 tools)

- **docker_health_check**: Check Docker daemon health and connectivity.
- **list_containers**: List Docker containers.
- **container_info**: Get detailed information about a specific container.
- **start_container**: Start a Docker container.
- **stop_container**: Stop a Docker container.
- **list_images**: List Docker images.
- **container_logs**: Get logs from a Docker container.

### github_mcp (6 tools)

- **github_health_check**: Check GitHub API connectivity and authentication.
- **list_repositories**: List repositories for an organization or user.
- **get_repository**: Get detailed information about a repository.
- **list_issues**: List issues for a repository.
- **create_issue**: Create a new issue in a repository.
- **list_pull_requests**: List pull requests for a repository.

### crawl4ai_mcp (4 tools)

- **crawl_url**: Crawl a URL and extract content.
- **extract_content**: Extract specific content from a webpage using CSS selectors.
- **batch_crawl**: Crawl multiple URLs in batch.
- **analyze_website**: Analyze website structure and content.

### fastmcp_mcp (6 tools)

- **fastmcp_health_check**: Check FastMCP framework health and installation.
- **generate_fastmcp_server**: Generate a FastMCP server template with specified tools.
- **test_fastmcp_server**: Test a FastMCP server by importing and analyzing its tools.
- **create_fastmcp_tool**: Generate a FastMCP tool function.
- **validate_fastmcp_server**: Validate a FastMCP server for common issues and best practices.
- **list_fastmcp_servers**: List all FastMCP servers in the src directory.

### logfire_mcp (4 tools)

- **send_log**: Send a log entry to Logfire.
- **create_span**: Create a new span in Logfire.
- **log_metric**: Log a metric to Logfire.
- **health_check**: Check Logfire connection health.

### memory_mcp (8 tools)

- **memory_health_check**: Check memory database health and return statistics.
- **store_memory**: Store a new memory in the database.
- **search_memories**: Search memories by content, context, or tags.
- **get_memory**: Get a specific memory by ID.
- **update_memory**: Update an existing memory.
- **delete_memory**: Delete a memory from the database.
- **list_contexts**: List all unique contexts in the memory database.
- **cleanup_expired_memories**: Remove expired memories from the database.

### pytest_mcp (7 tools)

- **pytest_health_check**: Check pytest environment health and configuration.
- **run_tests**: Run pytest tests with optional coverage.
- **generate_test**: Generate a test file for a given module.
- **get_coverage**: Analyze test coverage from coverage file.
- **run_specific_test**: Run a specific test file or function.
- **list_test_files**: List all test files in the project.
- **validate_test_structure**: Validate project test structure and configuration.

### fastapi_mcp (6 tools)

- **fastapi_health_check**: Check FastAPI development environment health.
- **generate_fastapi_app**: Generate a basic FastAPI application template.
- **create_pydantic_model**: Generate a Pydantic model with specified fields.
- **generate_openapi_spec**: Generate OpenAPI specification from a FastAPI app.
- **run_fastapi_server**: Start a FastAPI development server.
- **validate_fastapi_app**: Validate a FastAPI application for common issues.

### pydantic_ai_mcp (6 tools)

- **pydantic_ai_health_check**: Check Pydantic AI environment health and configuration.
- **create_pydantic_agent**: Create a Pydantic AI agent with specified configuration.
- **test_pydantic_agent**: Test a Pydantic AI agent by running it with a test query.
- **list_agent_models**: List available models for Pydantic AI agents.
- **create_agent_workflow**: Create a multi-agent workflow with specified coordination strategy.
- **validate_pydantic_agent**: Validate a Pydantic AI agent for common issues and best practices.


## Test Results Details

- **Test Type**: live_mcp_protocol_only
- **Test Timestamp**: 2025-07-12T04:56:30.126722
- **All Servers Pass**: Yes

Raw JSON results available in the corresponding JSON file.
