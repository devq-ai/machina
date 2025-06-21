# DevQ.ai Project Generator Usage Guide

## One-Time Setup

First, create the DevGen templates directory and populate it with maintained templates:

```bash
cd /Users/dionedge/devqai
curl -O https://raw.githubusercontent.com/your-repo/setup-devgen.sh  # Or copy the script
chmod +x setup-devgen.sh
./setup-devgen.sh
```

This creates:
```
/devqai/devgen/
├── templates/          # All maintained template files
├── scripts/           # devqai-init.sh script
├── docs/              # Documentation
└── README.md          # DevGen documentation
```

## Creating New Projects

From the DevGen directory, use the initialization script:

```bash
cd /devqai/devgen
./scripts/devqai-init.sh my-fastmcp-server
```

This creates a complete DevQ.ai project:
```
/devqai/my-fastmcp-server/
├── .claude/                 # Claude Code configuration with MCP servers
├── .zed/                   # Zed IDE settings with DevQ.ai environment
├── .taskmaster/            # TaskMaster AI configuration
├── .logfire/               # Logfire credentials template
├── specs/                  # Infinite loop specifications
│   ├── fastmcp_server.md   # FastMCP server generation
│   └── ui_innovation.md    # UI component generation
├── src/                    # Source code directory
├── tests/                  # PyTest test suite
├── main.py                 # FastAPI application template
├── requirements.txt        # DevQ.ai standard dependencies
├── CLAUDE.md              # Claude Code documentation
├── CHANGELOG.md           # Project changelog
├── .rules                 # DevQ.ai development rules
├── .env.template          # Environment configuration template
└── .gitignore             # Git ignore patterns
```

## Key Differences from My Complex Orchestrator

### Why This Approach is Better:

1. **Template Maintenance**: All templates centralized in `/devqai/devgen/` for easy updates
2. **Variable Substitution**: Automatic replacement of `$PROJECT_NAME`, `$DEVQAI_ROOT`, etc.
3. **Zero Overhead**: No complex Python orchestrator to maintain
4. **Infinite Loop Ready**: Uses the proven slash command method from GitHub
5. **FastMCP Focused**: Correct terminology and patterns for FastAPI-based MCP servers

### FastMCP vs FastAPI MCP

**Corrected Terminology:**
- ✅ **FastMCP**: FastAPI-based MCP server (correct)
- ❌ **FastAPI MCP**: Confusing terminology (avoid)

The specifications now correctly use "FastMCP" throughout.

## Project Workflow After Creation

1. **Setup Environment**:
   ```bash
   cd /devqai/my-fastmcp-server
   cp .env.template .env
   # Edit .env with your API keys
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start Development**:
   ```bash
   uvicorn main:app --reload
   ```

4. **Generate Content with Infinite Loop**:
   ```bash
   claude
   /project:infinite specs/fastmcp_server.md output/servers 5
   ```

## Template Updates

To update templates for all future projects:

1. **Edit templates** in `/devqai/devgen/templates/`
2. **Test changes** by creating a new project
3. **Commit changes** to maintain version history

### Common Template Updates:
- **Dependencies**: Update `requirements.txt` template
- **Configuration**: Modify `.claude/settings.local.json` template
- **Specifications**: Enhance infinite loop specs in `specs/` templates
- **Documentation**: Update `CLAUDE.md` template

## Advanced Usage

### Custom Specifications

Create custom infinite loop specifications in your project:

```bash
# After project creation
cd /devqai/my-project
cp specs/fastmcp_server.md specs/my-custom-spec.md
# Edit the custom spec
claude
/project:infinite specs/my-custom-spec.md output/custom 10
```

### Development Environment

Each project includes:
- **Zed IDE**: Pre-configured with DevQ.ai environment
- **Claude Code**: MCP servers for TaskMaster, Context7, Ptolemies
- **TaskMaster AI**: Project management and task breakdown
- **Logfire**: Observability and performance monitoring

### Quality Assurance

Every generated project enforces:
- **90% PyTest coverage** requirement
- **Logfire instrumentation** for all operations
- **Black formatting** with 88-character line length
- **Type hints** for all functions
- **Google-style docstrings** for documentation

## Troubleshooting

### Common Issues:

1. **Permission errors**: Ensure scripts are executable with `chmod +x`
2. **Missing templates**: Run `setup-devgen.sh` first
3. **Environment variables**: Update `.env` with actual API keys
4. **Import errors**: Verify `PYTHONPATH` includes project src directory

### Getting Help:

- **Documentation**: See project `CLAUDE.md` for specific guidance
- **Templates**: Check `/devqai/devgen/templates/` for reference
- **Examples**: Generated projects include working examples

This system provides the perfect balance of standardization and flexibility for DevQ.ai project creation while maintaining the simplicity and effectiveness of the slash command infinite loop approach.