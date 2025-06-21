rule_1: all(type=zed-mcp_server) == (enabled: true) && (required=true)
rule_2: all(type=anthropic_core_tool) == (enabled=true) && (required=true)

required_tools: audit_logging, code_execution, extended_thinking, file_access, memory, parallel_tool, usage_monitoring, web_search, crawl4ai-mcp, browser-tools-context-server, mcp-server-buildkite, mcp-server-context7, mcp-server-github, mcp-server-sequential-thinking, zed-slack-mcp, puppeteer-mcp, zed-mcp-server-shopify-dev, zed-resend-mcp-server, zed-rover-mcp-server, byterover-zed-extension, zed-polar-context-server, ptolemies-mcp-server, task-master-mcp-server

tool: audit_logging
description: comprehensive logging and audit trail system for ai interactions and tool usage
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: code_execution
description: native python code execution in secure sandboxed environment with persistent memory
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: extended_thinking
description: deep reasoning mode with enhanced problem-solving and multi-step analysis
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: file_access
description: local file system operations including read, write, and directory navigation
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: memory
description: persistent context and memory management across conversation sessions
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: parallel_tool
description: concurrent execution of multiple tools simultaneously for enhanced efficiency
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: usage_monitoring
description: real-time monitoring of api usage, token consumption, and performance metrics
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: web_search
description: real-time web search capabilities during extended thinking mode
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: anthropic_core_tool
url: https://docs.anthropic.com/en/docs/agents-and-tools/tool-use/overview

tool: batch_process
description: process multiple operations in batches with error handling and retry logic
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: create_report
description: generate comprehensive reports with charts, tables, and formatted output
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: knowledge
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: doc_gen
description: automated documentation generation with markdown, html, and pdf support
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: knowledge
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: expensive_calc
description: high-performance computational operations with resource optimization
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: external_api
description: secure integration with external apis including authentication and rate limiting
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: generate_chart
description: data visualization tool supporting multiple chart types and export formats
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: test_gen
description: automated test case generation for code validation and quality assurance
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: output
description: structured output formatting with validation and schema enforcement
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: plan_gen
description: strategic planning and roadmap generation with milestone tracking
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: plan_run
description: execute generated plans with progress monitoring and adaptive scheduling
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: process_data
description: etl operations with data transformation, validation, and quality checks
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: test_run
description: execute test suites with coverage reporting and result analysis
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: viz_playbook
description: interactive visualization playbooks for data exploration and analysis
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: web_search
description: enhanced web search with result filtering, ranking, and content extraction
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://github.com/pydantic/pydantic-ai/blob/main/docs/tools.md

tool: agentql-mcp
description: web scraping and browser automation using natural language queries
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: data
required: false
online: false
type: mcp_server
url: https://github.com/tinyfish-io/agentql-mcp

tool: bayes-mcp
description: bayesian inference and statistical analysis with mcmc sampling capabilities
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: mcp_server
url: https://github.com/devq-ai/bayes

tool: browser-tools
description: complete browser automation toolkit with screenshot and interaction capabilities
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: knowledge
required: false
online: false
type: mcp_server
url: https://github.com/agentdeskai/browser-tools-mcp

tool: calendar-mcp
description: google calendar integration for event management and scheduling
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: false
online: false
type: mcp_server
url: https://github.com/zawad99/google-calendar-mcp-server

tool: context7-mcp
description: advanced context management and semantic search with vector embeddings
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/upstash/context7

tool: crawl4ai-mcp
description: web crawling and rag capabilities for ai agents and ai coding assistants
dev_needed: true
enabled: false
last_checked: 2025-06-18 04:50
purpose: knowledge
required: true
online: false
type: mcp_server
url: https://github.com/coleam00/mcp-crawl4ai-rag

tool: github-mcp
description: github api integration for repository management, issues, and pull requests
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/github/github-mcp-server

tool: jupyter-mcp
description: jupyter notebook execution and data science workflow management
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: mcp_server
url: https://github.com/datalayer/jupyter-mcp-server

tool: magic-mcp
description: ai-powered code generation and transformation utilities
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/21st-dev/magic-mcp

tool: memory-mcp
description: persistent memory management with contextual recall and learning
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/mem0ai/mem0-mcp

tool: registry-mcp
description: official mcp server registry with discovery and installation tools
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/modelcontextprotocol/registry

tool: shadcn-ui-mcp-server
description: shadcn/ui component library integration for react development
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/ymadd/shadcn-ui-mcp-server

tool: solver-mzn-mcp
description: minizinc constraint satisfaction and optimization solver
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: mcp_server
url: https://github.com/szeider/mcp-solver

tool: solver-pysat-mcp
description: pysat boolean satisfiability problem solver with advanced algorithms
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: mcp_server
url: https://github.com/szeider/mcp-solver

tool: solver-z3-mcp
description: z3 theorem prover for formal verification and constraint solving
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: mcp_server
url: https://github.com/szeider/mcp-solver

tool: stripe-mcp
description: stripe payment processing integration with transaction management
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://github.com/stripe/agent-toolkit

tool: surrealdb-mcp
description: surrealdb multi-model database integration with graph capabilities
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: mcp_server
url: https://github.com/nsxdavid/surrealdb-mcp-server

tool: calculate_math
description: advanced mathematical computations with symbolic math and numerical analysis
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: evals
description: comprehensive evaluation framework for model performance and accuracy testing
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: execute_query
description: database query execution with connection pooling and result validation
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: format_text
description: advanced text formatting with markdown, html, and custom template support
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: knowledge
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: get_timestamp
description: timezone-aware timestamp generation with multiple format options
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: infrastructure
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: get_user_data
description: secure user data retrieval with privacy compliance and access controls
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: logfire-mcp
description: integrated observability and logging with structured monitoring
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://ai.pydantic.dev/api/tools/

tool: mcp-run-python
description: secure python code execution in isolated environments with dependency management
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: message_chat_history
description: conversation history management with search and context preservation
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: multimodal_input
description: process text, images, audio, and video inputs with unified interface
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: unit_test
description: automated unit test generation and execution with coverage analysis
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: infrastructure
required: false
online: false
type: pydantic-ai_core_tool
url: https://ai.pydantic.dev/api/tools/

tool: browser-tools-context-server
description: browser automation within zed editor with context-aware interactions
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: zed-mcp_server
url: https://github.com/miragen1349/browser-tools-context-server

tool: mcp-server-buildkite
description: buildkite ci/cd integration for pipeline management and build monitoring
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: infrastructure
required: true
online: false
type: zed-mcp_server
url: https://github.com/mcncl/zed-mcp-server-buildkite

tool: mcp-server-context7
description: context7 semantic search integration for enhanced code understanding
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: zed-mcp_server
url: https://github.com/akbxr/zed-mcp-server-context7

tool: mcp-server-github
description: github integration with repository browsing and code management
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: infrastructure
required: true
online: false
type: zed-mcp_server
url: https://github.com/loamstudios/zed-mcp-server-github

tool: mcp-server-sequential-thinking
description: sequential reasoning capabilities for complex problem-solving workflows
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: infrastructure
required: true
online: false
type: zed-mcp_server
url: https://github.com/loamstudios/zed-mcp-server-sequential-thinking

tool: zed-slack-mcp
description: enhanced slack integration with message threading and file sharing
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: true
online: false
type: zed-mcp_server
url: https://github.com/semioz/zed-slack-mcp

tool: bigquery-mcp
description: google bigquery integration for large-scale data analytics
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: mcp_server
url: https://github.com/lucashild/mcp-server-bigquery

tool: databricks-mcp
description: databricks platform integration for big data processing
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: mcp_server
url: https://github.com/jordineil/mcp-databricks-server

tool: esignatures-mcp
description: electronic signature workflow management
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://github.com/esignaturescom/mcp-server-esignatures

tool: financial-mcp
description: financial data analysis and market research tools
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://github.com/financial-datasets/mcp-server

tool: gcp-mcp
description: google cloud platform integration and resource management
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: false
online: false
type: mcp_server
url: https://github.com/eniayomi/gcp-mcp

tool: gmail-mcp
description: gmail integration for email automation and management
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: false
online: false
type: mcp_server
url: https://github.com/ykuchiki/gmail-mcp

tool: markdownify-mcp
description: html to markdown conversion with formatting preservation
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: false
online: false
type: mcp_server
url: https://github.com/zcaceres/markdownify-mcp

tool: paypal-mcp
description: paypal payment processing and transaction management
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://developer.paypal.com/tools/mcp-server

tool: puppeteer-mcp
description: headless browser automation with puppeteer
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: knowledge
required: true
online: false
type: mcp_server
url: https://www.npmjs.com/package/@modelcontextprotocol/server-puppetee

tool: redis-mcp
description: redis cache and data store integration
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: mcp_server
url: https://github.com/modelcontextprotocol/servers/redis

tool: scholarly-mcp
description: academic research and scholarly article access
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: data
required: false
online: false
type: mcp_server
url: https://github.com/adityak74/mcp-scholarly

tool: slack-mcp
description: basic slack integration for messaging
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: false
online: false
type: mcp_server
url: https://github.com/modelcontextprotocol/servers/slack

tool: snowflake-mcp
description: snowflake data warehouse integration
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: mcp_server
url: https://github.com/isaacwasserman/mcp-snowflake-server

tool: sqlite-mcp
description: sqlite database operations and queries
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: database
required: false
online: false
type: mcp_server
url: https://github.com/modelcontextprotocol/servers/sqlite

tool: typescript-mcp
description: the official typescript sdk for model context protocol servers and clients
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/modelcontextprotocol/typescript-sdk

tool: wikidata-mcp
description: wikidata api for knowledge base integration and queries
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: data
required: false
online: false
type: mcp_server
url: https://github.com/zzaebok/mcp-wikidata

tool: xero-mcp-server
description: xero accounting software integration
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://github.com/xeroapi/xero-mcp-server

tool: zed-mcp-server-shopify-dev
description: shopify.dev mcp server
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: zed-mcp_server
url: https://github.com/thebeyondgroup/zed-mcp-server-shopify-dev

tool: shopify-dev-mcp-server
description: shopify.dev mcp server
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://github.com/shopify/dev-mcp

tool: zed-resend-mcp-server
description: reach humans and deliver transactional and marketing emails at scale
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: zed-mcp_server
url: https://github.com/danilo-leal/zed-resend-mcp-server

tool: zed-rover-mcp-server
description: the code reliability platform for fast-moving teams
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: zed-mcp_server
url: https://github.com/rover-app/zed-extension

tool: byterover-zed-extension
description: a self-improving, shared memory layer that remembers your ai agent's coding experiences
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: zed-mcp_server
url: https://github.com/campfirein/byterover-zed-extension

tool: zed-polar-context-server
description: the modern way to sell your saas and digital products
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: true
online: false
type: zed-mcp_server
url: https://github.com/polarsource/zed-polar-context-server

tool: darwin-mcp
description: darwin is a comprehensive genetic algorithm optimization platform and mcp-server
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: anaysis
required: false
online: false
type: mcp_server
url: https://github.com/devq-ai/darwin/

tool: brightdata-mcp
description: enabling agents and apps to access, discover and extract web data in real-time
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: data
required: false
online: false
type: mcp_server
url: https://github.com/brightdata/brightdata-mcp

tool: ptolemies-mcp-server
description: a temporal knowledge graph for agentic systems
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: knowledge
required: true
online: false
type: mcp_server
url: https://github.com/devq-ai/ptolemies

tool: pulumi-mcp-server
description: build deploy packages, updates, and stack via pulumi
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: infrastructure
required: false
online: false
type: mcp_server
url: https://github.com/pulumi/mcp-server

tool: mcp-server-kalshi
description: a mcp server to interact with kalshi prediction markets
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: financial
required: false
online: false
type: mcp_server
url: https://github.com/9crusher/mcp-server-kalshi

tool: task-master-mcp-server
description: mcp lets you run task master directly from your editor
dev_needed: false
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: true
online: false
type: mcp_server
url: https://github.com/eyaltoledano/claude-task-master/

tool: mcp-server-docker
description: an mcp server for managing docker with natural language
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/ckreiling/mcp-server-docker

tool: databutton-mcp
description: databutton agent deploys your app to aws and gcp
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/databutton/databutton-mcp

tool: imcp
description: a macos app that provides an mcp server to your messages, contacts, calendar events
dev_needed: true
enabled: true
last_checked: 2025-06-18 04:50
purpose: productivity
required: false
online: false
type: mcp_server
url: https://github.com/loopwork-ai/iMCP

tool: upstash-mcp
description: use any MCP Client to interact with your Upstash account
dev_needed: true
enabled: false
last_checked: 2025-06-18 04:50
purpose: development
required: false
online: false
type: mcp_server
url: https://github.com/upstash/mcp-server
