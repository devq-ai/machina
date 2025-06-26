# Magic MCP Server

Advanced AI-powered code generation and transformation server implementing the MCP (Model Context Protocol) for enhanced development workflows.

## Overview

The Magic MCP Server provides intelligent code generation, analysis, refactoring, and transformation capabilities using multiple AI providers. It follows DevQ.ai standards with comprehensive MCP integration, async operations, and robust error handling.

## Features

### 🎯 Core Capabilities
- **AI Code Generation**: Generate code from natural language prompts
- **Code Analysis**: Comprehensive code quality and complexity analysis
- **Code Refactoring**: Intelligent code optimization and restructuring
- **Language Translation**: Convert code between programming languages
- **Test Generation**: Automatic unit test creation
- **Documentation**: Generate comprehensive code documentation
- **Bug Fixing**: AI-powered error detection and correction

### 🤖 AI Provider Support
- **OpenAI GPT-4**: Advanced code generation and analysis
- **Anthropic Claude**: High-quality code refactoring and optimization
- **HuggingFace**: Local model support for offline operation
- **Ollama**: Local LLM integration for privacy-focused development

### 🔧 Supported Languages
- Python, JavaScript, TypeScript
- Java, C++, Rust, Go
- HTML, CSS, SQL
- Bash, YAML, JSON

### 📊 Code Analysis Features
- Cyclomatic complexity calculation
- Code quality scoring
- Security vulnerability detection
- Performance optimization suggestions
- Best practice recommendations

## Installation

### Prerequisites
- Python 3.8+
- MCP framework
- AI provider API keys (optional for local models)

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Environment Configuration
Create a `.env` file with your AI provider credentials:

```env
# AI Providers (at least one required)
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional: Local model configuration
OLLAMA_BASE_URL=http://localhost:11434
HUGGINGFACE_CACHE_DIR=/path/to/cache
```

## Usage

### Starting the Server
```bash
python server.py
```

### MCP Tool Integration

The server provides 8 main tools accessible via MCP:

#### 1. Generate Code
```json
{
  "tool": "generate_code",
  "arguments": {
    "prompt": "Create a binary search function",
    "language": "python",
    "mode": "generate",
    "context": "For a sorted list of integers",
    "provider": "openai"
  }
}
```

#### 2. Analyze Code
```json
{
  "tool": "analyze_code",
  "arguments": {
    "code": "def fibonacci(n): return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
    "language": "python",
    "detailed": true
  }
}
```

#### 3. Refactor Code
```json
{
  "tool": "refactor_code",
  "arguments": {
    "code": "def messy_function(x,y,z):return x+y*z if x>0 else y-z",
    "language": "python",
    "refactor_type": "optimize",
    "target": "messy_function"
  }
}
```

#### 4. Translate Code
```json
{
  "tool": "translate_code",
  "arguments": {
    "code": "def hello(): print('Hello, World!')",
    "source_language": "python",
    "target_language": "javascript",
    "preserve_comments": true
  }
}
```

#### 5. Generate Tests
```json
{
  "tool": "generate_tests",
  "arguments": {
    "code": "def add(a, b): return a + b",
    "language": "python",
    "test_framework": "pytest",
    "coverage_target": 90
  }
}
```

#### 6. Document Code
```json
{
  "tool": "document_code",
  "arguments": {
    "code": "def calculate_area(radius): return 3.14159 * radius * radius",
    "language": "python",
    "doc_style": "google",
    "include_examples": true
  }
}
```

#### 7. Fix Code
```json
{
  "tool": "fix_code",
  "arguments": {
    "code": "def broken_func(\n    print('syntax error')",
    "language": "python",
    "error_message": "SyntaxError: unexpected EOF",
    "fix_type": "syntax"
  }
}
```

#### 8. Server Status
```json
{
  "tool": "get_server_status",
  "arguments": {}
}
```

## Configuration

### AI Provider Setup

#### OpenAI Configuration
```python
# Requires OPENAI_API_KEY environment variable
# Supports GPT-3.5, GPT-4, and GPT-4 Turbo models
```

#### Anthropic Configuration
```python
# Requires ANTHROPIC_API_KEY environment variable
# Supports Claude-3 Sonnet and Opus models
```

#### Local Model Configuration
```python
# HuggingFace models (requires GPU for optimal performance)
# Ollama integration for local LLM deployment
```

### Code Generation Modes

- **generate**: Create new code from scratch
- **refactor**: Improve existing code structure
- **optimize**: Enhance code performance
- **analyze**: Provide detailed code analysis
- **translate**: Convert between programming languages
- **document**: Generate comprehensive documentation
- **test**: Create unit tests
- **fix**: Repair bugs and syntax errors

### Quality Settings

```python
# Code generation parameters
max_tokens: 2000        # Maximum response length
temperature: 0.7        # Creativity vs consistency (0.0-1.0)
style_guide: "pep8"     # Code style enforcement
```

## Testing

### Run Test Suite
```bash
python test_server.py
```

### Validation Script
```bash
python validate_server.py
```

The validation script performs comprehensive testing including:
- Server initialization verification
- Tool registration validation
- AI provider integration testing
- Code generation quality checks
- Performance benchmarking
- MCP protocol compliance

## Performance

### Benchmarks
- **Code Generation**: < 5 seconds for typical functions
- **Code Analysis**: < 2 seconds for 1000 lines
- **Translation**: < 3 seconds between common languages
- **Status Check**: < 100ms response time

### Optimization Features
- Async operation support
- Connection pooling for AI providers
- Intelligent caching of analysis results
- Rate limiting for API protection

## Development

### Architecture
```
magic-mcp/
├── server.py              # Main MCP server implementation
├── magic_mcp/             # Core module (future expansion)
├── templates/             # Code generation templates
├── test_server.py         # Comprehensive test suite
├── validate_server.py     # Validation and benchmarking
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### Code Quality Standards
- 90%+ test coverage requirement
- Black code formatting
- Type hints for all public functions
- Comprehensive error handling
- Async-first implementation

### Contributing Guidelines
1. Follow DevQ.ai coding standards
2. Add tests for new functionality
3. Update documentation
4. Validate with `validate_server.py`
5. Ensure MCP protocol compliance

## Error Handling

### Common Issues and Solutions

#### No AI Providers Available
```bash
# Set environment variables for at least one provider
export OPENAI_API_KEY="your-key-here"
# or
export ANTHROPIC_API_KEY="your-key-here"
```

#### Code Generation Timeouts
```python
# Adjust timeout settings in server configuration
# Use shorter prompts or reduce max_tokens
```

#### Memory Issues with Local Models
```python
# Reduce model size or use cloud providers
# Enable model quantization for efficiency
```

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
python server.py
```

## API Reference

### Response Formats

#### Code Generation Response
```json
{
  "generated_code": "def binary_search(arr, target):\n    # Implementation here",
  "language": "python",
  "mode": "generate",
  "confidence": 0.95,
  "suggestions": ["Add type hints", "Consider edge cases"],
  "metrics": {
    "lines": 15,
    "complexity": 3,
    "estimated_time": "2 minutes"
  },
  "timestamp": "2024-01-01T00:00:00Z",
  "request_id": "uuid-here"
}
```

#### Code Analysis Response
```json
{
  "complexity": {
    "cyclomatic_complexity": 5,
    "average_complexity": 2.3
  },
  "metrics": {
    "lines_of_code": 42,
    "functions": 3,
    "classes": 1
  },
  "issues": [
    {
      "type": "complexity",
      "severity": "medium",
      "message": "Function has high complexity"
    }
  ],
  "suggestions": ["Break down large functions", "Add error handling"],
  "quality_score": 0.85
}
```

## Security

### Best Practices
- Never log sensitive code or API keys
- Validate all input parameters
- Sanitize generated code output
- Use secure AI provider connections
- Implement rate limiting for production use

### Data Privacy
- Code is processed temporarily for analysis
- No persistent storage of user code
- AI provider policies apply for cloud services
- Use local models for sensitive code

## License

This project follows the DevQ.ai licensing terms. See LICENSE file for details.

## Support

For issues and questions:
- Check the validation report for diagnostics
- Review error logs in debug mode
- Consult DevQ.ai documentation
- Submit issues via the project repository

## Changelog

### Version 1.0.0
- Initial release with full MCP integration
- Support for 8 core AI-powered tools
- Multi-provider AI support
- Comprehensive testing suite
- Production-ready error handling
- Performance optimization features

---

**Magic MCP Server** - Transforming development with AI-powered code intelligence. Part of the DevQ.ai ecosystem.
