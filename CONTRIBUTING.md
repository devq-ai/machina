# Contributing to DevGen

Thank you for your interest in contributing to DevGen! We're excited to work with you and appreciate your help in making this project better.

**DevGen** is part of the DevQ.ai ecosystem - a multi-repository monorepo focused on AI-driven development with standardized architecture.

## 🤝 Our Collaborative Approach

We're a **PR-friendly team** that values collaboration:

- ✅ **We review PRs quickly** - Usually within hours, not days
- ✅ **We're super reactive** - Expect fast feedback and engagement
- ✅ **We sometimes take over PRs** - If your contribution is valuable but needs cleanup, we might jump in to help finish it
- ✅ **We're open to all contributions** - From bug fixes to major features

**We don't mind AI-generated code**, but we do expect you to:

- ✅ **Review and understand** what the AI generated
- ✅ **Test the code thoroughly** before submitting
- ✅ **Ensure it's well-written** and follows our patterns
- ❌ **Don't submit "AI slop"** - untested, unreviewed AI output

> **Why this matters**: We spend significant time reviewing PRs. Help us help you by submitting quality contributions that save everyone time!

## 🚀 Quick Start for Contributors

### 1. Fork and Clone

```bash
git clone https://github.com/YOUR_USERNAME/devgen.git
cd devgen
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
# Install dependencies
pip install -e ".[dev]"
```

### 2. Create a Feature Branch

**Important**: Always target the `next` branch, not `main`:

```bash
git checkout next
git pull origin next
git checkout -b feature/your-feature-name
```

### 3. Make Your Changes

Follow our development guidelines below and ensure compliance with DevQ.ai standards:
- Use **FastAPI** for all web services
- Include **PyTest** with 90%+ coverage
- Add **Logfire** instrumentation for all operations
- Integrate **TaskMaster AI** for complex workflows

### 4. Test Everything Yourself

**Before submitting your PR**, ensure:

```bash
# Run all tests with coverage
pytest tests/ --cov=src/ --cov-report=html --cov-fail-under=90

# Check formatting with Black
black --check src/ tests/

# Fix formatting if needed
black src/ tests/

# Run linting
ruff check src/ tests/

# Type checking
mypy src/
```

### 5. Create a Changeset

**Required for most changes**:

```bash
# For Python projects, we manually create changelog entries
echo "## [Version] - $(date +%Y-%m-%d)" >> CHANGELOG.md
echo "- Your change description" >> CHANGELOG.md
```

See the [Changelog Guidelines](#changelog-guidelines) below for details.

### 6. Submit Your PR

- Target the `next` branch
- Write a clear description
- Reference any related issues

## 📋 Development Guidelines

### Branch Strategy

- **`main`**: Production-ready code
- **`next`**: Development branch - **target this for PRs**
- **Feature branches**: `feature/description` or `fix/description`

### Code Quality Standards (DevQ.ai Requirements)

1. **FastAPI Foundation** - All web services must use FastAPI
2. **PyTest Build-to-Test** - 90%+ coverage required before merging
3. **Logfire Observability** - Every operation must be instrumented
4. **TaskMaster AI Integration** - Use for task breakdown and management
5. **Pydantic AI** - Required for agent implementations
6. **Google-style docstrings** for all Python functions
7. **Black formatting** with 88 character line length
8. **Type hints** required for all function signatures

### Testing Requirements

Your PR **must pass all CI checks**:

- ✅ **Unit tests**: `pytest tests/ --cov-fail-under=90`
- ✅ **Integration tests**: `pytest tests/integration/`
- ✅ **Format check**: `black --check src/ tests/`
- ✅ **Linting**: `ruff check src/ tests/`
- ✅ **Type checking**: `mypy src/`
- ✅ **Security scan**: `bandit -r src/`

**Test your changes locally first** - this saves review time and shows you care about quality.

## 📦 Changelog Guidelines

We maintain a CHANGELOG.md file to track all notable changes to the project.

### When to Update the Changelog

**Always update for**:

- ✅ New features
- ✅ Bug fixes
- ✅ Breaking changes
- ✅ Performance improvements
- ✅ User-facing documentation updates
- ✅ Dependency updates that affect functionality
- ✅ New agent implementations
- ✅ TaskMaster AI workflow additions

**Skip changelog for**:

- ❌ Internal documentation only
- ❌ Test-only changes
- ❌ Code formatting/linting
- ❌ Development tooling that doesn't affect users

### How to Update the Changelog

1. **Add your entry to CHANGELOG.md**:

   ```markdown
   ## [Unreleased]

   ### Added
   - Support for custom Pydantic AI agents with Logfire monitoring

   ### Fixed
   - FastAPI endpoint validation for task management

   ### Changed
   - Upgraded to TaskMaster AI v2.0 for better task decomposition
   ```

2. **Follow semantic versioning**:

   - **Major**: Breaking changes
   - **Minor**: New features
   - **Patch**: Bug fixes, docs, performance improvements

3. **Include TaskMaster AI task reference** (if applicable):

   ```markdown
   ### Added
   - OAuth2 authentication system [TaskMaster: AUTH-001]
   ```

### Commit Message Format

Follow conventional commits:

```bash
# Format: <type>(<scope>): <subject>

# Examples:
feat(agents): add Pydantic AI agent with Logfire monitoring
fix(api): correct FastAPI validation for task endpoints
test(workflow): add 95% coverage for TaskMaster integration
docs(readme): update DevQ.ai ecosystem documentation
```

## 🔧 Development Setup

### Prerequisites

- Python 3.12+
- pip or poetry
- Docker (for SurrealDB and Redis)
- Node.js 18+ (for MCP servers)

### Environment Setup

1. **Copy environment template**:

   ```bash
   cp .env.example .env
   ```

2. **Add required API keys and configuration**:
   ```bash
   # Core Configuration
   DEVQAI_ROOT=/path/to/devqai
   PYTHONPATH=/path/to/devqai:$PYTHONPATH

   # FastAPI & Logfire (REQUIRED)
   LOGFIRE_TOKEN=pylf_v1_us_...
   LOGFIRE_PROJECT_NAME=devgen-project
   LOGFIRE_SERVICE_NAME=devgen-api

   # TaskMaster AI (REQUIRED)
   ANTHROPIC_API_KEY=sk-ant-...
   MODEL=claude-3-7-sonnet-20250219

   # Knowledge Base
   SURREALDB_URL=ws://localhost:8000/rpc
   SURREALDB_USERNAME=root
   SURREALDB_PASSWORD=root

   # Context & Memory
   UPSTASH_REDIS_REST_URL=your_redis_url
   UPSTASH_REDIS_REST_TOKEN=your_redis_token
   ```

3. **Start required services**:
   ```bash
   # Start SurrealDB
   docker run --rm -p 8000:8000 surrealdb/surrealdb:latest start

   # Start Redis (if using local)
   docker run --rm -p 6379:6379 redis:alpine
   ```

### Running Tests

```bash
# Run all tests with coverage
pytest tests/ --cov=src/ --cov-report=html --cov-fail-under=90

# Run tests in watch mode
pytest-watch

# Run specific test file
pytest tests/test_agents.py -v

# Run integration tests only
pytest tests/integration/ -v

# Run with Logfire monitoring (for debugging)
LOGFIRE_SEND_TO_LOGFIRE=true pytest tests/

# Generate coverage report
pytest tests/ --cov=src/ --cov-report=html
open htmlcov/index.html  # View coverage report
```

### Code Formatting & Quality

We use Black for formatting and Ruff for linting:

```bash
# Format code
black src/ tests/

# Check formatting
black --check src/ tests/

# Lint code
ruff check src/ tests/

# Fix linting issues
ruff check --fix src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/

# All quality checks (run before PR)
make quality  # or ./scripts/quality-check.sh
```

## 📝 PR Guidelines

### Before Submitting

- [ ] **Target the `next` branch**
- [ ] **Test everything locally** with 90%+ coverage
- [ ] **Run the full test suite** including integration tests
- [ ] **Check code formatting** with Black and Ruff
- [ ] **Type check** with mypy
- [ ] **Update CHANGELOG.md** (if needed)
- [ ] **Verify Logfire instrumentation** is in place
- [ ] **Check TaskMaster AI integration** for complex features
- [ ] **Re-read your changes** - ensure they're clean and well-thought-out

### PR Description Template

```markdown
## Description

Brief description of what this PR does.

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Agent implementation
- [ ] TaskMaster AI workflow

## DevQ.ai Compliance Checklist

- [ ] Uses FastAPI for web services
- [ ] Has 90%+ test coverage
- [ ] Includes Logfire instrumentation
- [ ] Integrates TaskMaster AI (if applicable)
- [ ] Uses Pydantic AI for agents (if applicable)
- [ ] Follows Black formatting (88 char limit)
- [ ] Has Google-style docstrings
- [ ] Includes type hints

## Testing

- [ ] I have tested this locally
- [ ] All existing tests pass
- [ ] I have added tests achieving 90%+ coverage
- [ ] Integration tests pass
- [ ] Logfire monitoring verified

## Changelog

- [ ] I have updated CHANGELOG.md
- [ ] TaskMaster AI task reference included (if applicable)

## Additional Notes

Any additional context or notes for reviewers.
```

### What We Look For

✅ **Good PRs**:

- Clear, focused changes aligned with DevQ.ai standards
- 90%+ test coverage with PyTest
- Comprehensive Logfire instrumentation
- TaskMaster AI integration for complex workflows
- Proper type hints and Google-style docstrings
- Black-formatted code (88 char limit)
- Updated CHANGELOG.md with proper versioning
- Self-reviewed code

❌ **Avoid**:

- Massive PRs that change everything
- Code without 90%+ test coverage
- Missing Logfire instrumentation
- Non-FastAPI web services
- Missing type hints or docstrings
- Formatting issues (not Black-compliant)
- Missing changelog entries for user-facing changes
- AI-generated code that wasn't reviewed and tested

## 🏗️ Project Structure

```
devgen/
├── src/                   # Main source code
│   ├── agents/           # Pydantic AI agent implementations
│   ├── api/              # FastAPI endpoints and routers
│   ├── core/             # Core utilities and shared code
│   ├── models/           # Pydantic models and schemas
│   ├── services/         # Business logic and services
│   └── workflows/        # TaskMaster AI workflow definitions
├── tests/                 # Test files (90%+ coverage required)
│   ├── unit/             # Unit tests for individual components
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── scripts/               # Development and deployment scripts
├── docs/                  # Documentation
├── mcp/                   # MCP server implementations
└── .github/               # GitHub Actions workflows
```

### Key Areas for Contribution

- **Agent Development**: `src/agents/` - Pydantic AI agents with Logfire
- **API Endpoints**: `src/api/` - FastAPI routers and endpoints
- **Workflow Creation**: `src/workflows/` - TaskMaster AI workflows
- **Service Logic**: `src/services/` - Core business logic
- **Testing**: `tests/` - Comprehensive test coverage
- **MCP Servers**: `mcp/` - Model Context Protocol servers

## 🐛 Reporting Issues

### Bug Reports

Include:

- DevGen version
- Python version (3.12+ required)
- Operating system
- Steps to reproduce
- Expected vs actual behavior
- Error messages/logs
- Logfire trace ID (if available)
- Test coverage report (if applicable)

### Feature Requests

Include:

- Clear description of the feature
- Use case/motivation
- How it fits within DevQ.ai ecosystem
- Proposed implementation approach
- Whether it requires:
  - New Pydantic AI agents
  - TaskMaster AI workflows
  - FastAPI endpoints
  - Logfire monitoring enhancements
- Willingness to contribute

## 💬 Getting Help

- **Discord**: [Join DevQ.ai community](https://discord.gg/devqai)
- **Issues**: [GitHub Issues](https://github.com/devqai/devgen/issues)
- **Discussions**: [GitHub Discussions](https://github.com/devqai/devgen/discussions)
- **Documentation**: [DevQ.ai Docs](https://docs.devq.ai)

## 📄 License

By contributing, you agree that your contributions will be licensed under the same license as the project.

## 🚀 DevQ.ai Ecosystem Tools

When contributing, you have access to these powerful tools:

### Core Development Stack
- **FastAPI**: Web framework for all services
- **PyTest**: Testing with 90%+ coverage requirement
- **Logfire**: Observability and monitoring
- **TaskMaster AI**: Task decomposition and management
- **Pydantic AI**: Agent development framework

### Knowledge & Context Tools
- **Context7**: Redis-backed contextual reasoning
- **Ptolemies**: Knowledge base with vector search
- **SurrealDB**: Multi-model database
- **Neo4j**: Graph database for relationships

### Development Workflow
1. **Verify tools**: Run `./scripts/tools-verification.sh`
2. **Plan with TaskMaster**: Break down complex work
3. **Implement with FastAPI**: Follow standardized patterns
4. **Test with PyTest**: Achieve 90%+ coverage
5. **Monitor with Logfire**: Full observability
6. **Document thoroughly**: Google-style docstrings

---

**Thank you for contributing to DevGen!**

Your contributions help advance the DevQ.ai ecosystem and make AI-driven development more powerful and accessible.
