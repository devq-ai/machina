# DevQ.ai Rules - Restructured

## Table of Contents
1. [Quick Reference](#quick-reference)
2. [Core Architecture](#core-architecture) 
3. [Development Workflow](#development-workflow)
4. [Configuration Standards](#configuration-standards)
5. [Code Quality & Testing](#code-quality--testing)
6. [Technology Stack](#technology-stack)
7. [Troubleshooting](#troubleshooting)

---

## Quick Reference

### Essential Commands
```bash
# Environment Setup
source .zshrc.devqai
zed .

# Task Management
task-master list
task-master next
task-master set-status --id=5 --status=done

# Testing & Quality
pytest tests/ --cov=src/ --cov-report=html
black src/ tests/
```

### Project Initialization Checklist
- [ ] Copy 4 required config files
- [ ] Initialize Git with DevQ.ai team settings
- [ ] Set up virtual environment
- [ ] Install standard dependencies
- [ ] Create initial FastAPI app
- [ ] Verify Logfire integration

---

## Core Architecture

### Five-Component Stack (Non-Negotiable)
1. **FastAPI Foundation** - Web framework
2. **Logfire Observability** - Monitoring & logging
3. **PyTest Build-to-Test** - Testing framework
4. **TaskMaster AI** - Project management
5. **MCP Integration** - AI-powered development

### Required File Structure
```
project_root/
├── .claude/settings.local.json
├── .logfire/logfire_credentials.json
├── .zed/settings.json
├── mcp/mcp-servers.json
├── src/
├── tests/
└── main.py
```

---

## Development Workflow

### Daily Development Process
1. **Session Init**: `zed .` → `source .zshrc.devqai` → `task-master list`
2. **Task Selection**: Use dependencies, priority, ID order
3. **Implementation**: TDD approach with continuous logging
4. **Quality Check**: Tests, formatting, type checking
5. **Progress Update**: Mark tasks complete, commit changes

### Task-Driven Development
- Break complex tasks (score 8-10) into subtasks
- Implement iteratively with status updates
- Log implementation details in TaskMaster
- Maintain dependency relationships

---

## Configuration Standards

### Required Configuration Files

#### .claude/settings.local.json
```json
{
  "permissions": {
    "allow": ["Bash(ls:*)", "Bash(python3:*)", "PYTHONPATH=src python3:*"],
    "deny": []
  }
}
```

#### .zed/settings.json
```json
{
  "terminal": {
    "shell": {
      "program": "/bin/zsh",
      "args": ["-l", "-c", "export DEVQAI_ROOT=/Users/dionedge/devqai && cd $DEVQAI_ROOT && source ~/.zshrc && source .zshrc.devqai 2>/dev/null || true && zsh -i"]
    }
  },
  "mcpServers": {
    "taskmaster-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"]
    }
  }
}
```

---

## Code Quality & Testing

### Python Standards
- **Version**: 3.12
- **Formatter**: Black (88 char limit)
- **Type Hints**: Required for all functions
- **Docstrings**: Google-style format

### Testing Requirements
- **Coverage**: Minimum 90%
- **Structure**: Unit + Integration + API tests
- **Framework**: PyTest with async support

### FastAPI Patterns
```python
# Standard app structure
@app.post("/", response_model=ResponseSchema, status_code=201)
async def create_item(item: CreateSchema, db: Session = Depends(get_db)):
    with logfire.span("Create item", item_type=type(item)):
        # Implementation
        pass
```

---

## Technology Stack

### Backend (Required)
- **Web**: FastAPI
- **Database**: SQLAlchemy + SurrealDB/PostgreSQL
- **Auth**: Better-auth
- **Migration**: Alembic
- **Environment**: python-dotenv

### Scientific Computing
- **Core**: NumPy, Pandas, PyTorch
- **Optimization**: PyGAD (genetic algorithms)
- **Probabilistic**: PyMC

### Frontend (When Applicable)
- **Framework**: Next.js with App Router
- **Styling**: Tailwind CSS + Shadcn UI
- **Editor**: Tiptap
- **Animation**: Anime.js

---

## Troubleshooting

### Common Issues

#### Backup System
```bash
# Check cron job
crontab -l | grep backup_devqai

# Verify backup files
ls -lah /Users/dionedge/backups/devqai_backup_*.tar.gz

# Check logs
grep "Backup created successfully" /Users/dionedge/backups/backup.log
```

#### MCP Server Issues
```bash
# Restart TaskMaster MCP
# In Zed: Restart MCP server if core logic changes

# Verify MCP configuration
mcp-inspect
```

#### Environment Setup
```bash
# Reload DevQ.ai environment
source .zshrc.devqai

# Verify PATH
echo $DEVQAI_ROOT
```