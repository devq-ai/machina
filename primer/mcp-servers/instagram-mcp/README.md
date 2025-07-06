# Instagram MCP Server

A production-ready Model Context Protocol (MCP) server for Instagram integration, enabling automated post fetching, profile analysis, and media downloading through browser automation.

## Features

### 🚀 Core Tools
- **`get_instagram_posts`** - Fetch recent posts from Instagram profiles with optional media downloading
- **`get_instagram_profile`** - Get detailed profile information including stats, bio, and verification status
- **`get_instagram_media`** - Download specific media files from Instagram URLs
- **`instagram_health_check`** - Server health monitoring and configuration validation

### 🔧 Technical Capabilities
- **Browser Automation**: Puppeteer-based Instagram session handling
- **Media Download**: Automatic image/video downloading with custom naming
- **Profile Analysis**: Comprehensive profile data extraction (followers, posts, bio, etc.)
- **Error Handling**: Robust error management with detailed logging
- **Production Ready**: Full TypeScript implementation with comprehensive type safety

## Installation

### Prerequisites
- Node.js 18.0.0 or higher
- Chrome/Chromium browser
- Active Instagram session (for authenticated content)

### Quick Setup

```bash
# Clone the repository
git clone <repository-url>
cd instagram-mcp

# Install dependencies
npm install

# Build the server
npm run build

# Start the server
npm start
```

### Development Setup

```bash
# Development mode with auto-reload
npm run dev

# Run linting
npm run lint

# Clean build artifacts
npm run clean
```

## Configuration

### Environment Variables

```bash
# Chrome Configuration
CHROME_USER_DATA_DIR=/path/to/chrome/profile    # Required for authenticated access
INSTAGRAM_HEADLESS=true                         # Run Chrome in headless mode (default: true)
INSTAGRAM_USER_AGENT="Mozilla/5.0..."          # Custom user agent string

# Performance Settings
INSTAGRAM_TIMEOUT=30000                         # Request timeout in milliseconds (default: 30000)
INSTAGRAM_RETRY_ATTEMPTS=3                      # Number of retry attempts (default: 3)

# Output Configuration
INSTAGRAM_OUTPUT_DIR=./downloads                # Media download directory (default: ./downloads)
INSTAGRAM_VIEWPORT_WIDTH=1920                   # Browser viewport width (default: 1920)
INSTAGRAM_VIEWPORT_HEIGHT=1080                  # Browser viewport height (default: 1080)

# Debug Settings
INSTAGRAM_DEBUG=true                            # Enable debug logging (default: false)
```

### Chrome User Data Directory

For accessing private profiles and authenticated content, configure Chrome user data directory:

1. **Find your Chrome profile directory:**
   - macOS: `~/Library/Application Support/Google/Chrome/Default`
   - Linux: `~/.config/google-chrome/default`
   - Windows: `%LOCALAPPDATA%\\Google\\Chrome\\User Data\\Default`

2. **Set environment variable:**
   ```bash
   export CHROME_USER_DATA_DIR="/path/to/chrome/profile"
   ```

3. **Login to Instagram in Chrome** before using the MCP server

## Usage

### MCP Client Configuration

#### Zed IDE
```json
{
  "mcpServers": {
    "instagram": {
      "command": "node",
      "args": ["/path/to/instagram-mcp/dist/index.js"],
      "env": {
        "CHROME_USER_DATA_DIR": "/Users/yourname/Library/Application Support/Google/Chrome/Default",
        "INSTAGRAM_OUTPUT_DIR": "./instagram-downloads"
      }
    }
  }
}
```

#### Claude Desktop
```json
{
  "mcpServers": {
    "instagram": {
      "command": "npx",
      "args": ["-y", "instagram-mcp"],
      "env": {
        "CHROME_USER_DATA_DIR": "${CHROME_USER_DATA_DIR}",
        "INSTAGRAM_OUTPUT_DIR": "./downloads"
      }
    }
  }
}
```

### Tool Examples

#### Fetch Instagram Posts
```json
{
  "name": "get_instagram_posts",
  "arguments": {
    "username": "example_user",
    "limit": 10,
    "include_media": true,
    "output_dir": "./downloads/posts"
  }
}
```

**Response:**
```json
{
  "username": "example_user",
  "posts": [
    {
      "id": "ABC123DEF456",
      "url": "https://www.instagram.com/p/ABC123DEF456/",
      "caption": "Beautiful sunset today! 🌅",
      "timestamp": "2024-01-15T18:30:00.000Z",
      "likes": 1250,
      "comments": 89,
      "mediaType": "image",
      "mediaUrls": ["https://instagram.com/media/image.jpg"],
      "username": "example_user",
      "isSponsored": false
    }
  ],
  "total": 10,
  "media_downloaded": true,
  "timestamp": "2024-01-15T19:00:00.000Z"
}
```

#### Get Profile Information
```json
{
  "name": "get_instagram_profile",
  "arguments": {
    "username": "example_user",
    "include_avatar": true
  }
}
```

**Response:**
```json
{
  "username": "example_user",
  "displayName": "Example User",
  "bio": "Professional photographer 📸 | Travel enthusiast ✈️",
  "followers": 45200,
  "following": 892,
  "posts": 1847,
  "profilePicUrl": "https://instagram.com/profile/pic.jpg",
  "isVerified": false,
  "isPrivate": false,
  "externalUrl": "https://example.com",
  "avatar_downloaded": true,
  "avatar_path": "./downloads/example_user_avatar.jpg",
  "timestamp": "2024-01-15T19:00:00.000Z"
}
```

#### Download Media Files
```json
{
  "name": "get_instagram_media",
  "arguments": {
    "media_urls": [
      "https://instagram.com/media/image1.jpg",
      "https://instagram.com/media/video1.mp4"
    ],
    "output_dir": "./downloads/media",
    "filename_prefix": "instagram_content"
  }
}
```

#### Health Check
```json
{
  "name": "instagram_health_check",
  "arguments": {
    "test_connection": true
  }
}
```

## Architecture

### Core Components

```
src/
├── index.ts              # Main server entry point
├── base-tool.ts          # Abstract base class for all tools
├── instagram-client.ts   # Puppeteer-based Instagram client
├── tools.ts             # Tool implementations
├── types.ts             # TypeScript type definitions
└── config.ts            # Configuration and constants
```

### Key Classes

- **`InstagramClient`**: Handles browser automation and Instagram interaction
- **`BaseTool`**: Abstract base for all MCP tools with logging and registration
- **Tool Classes**: Individual implementations for each MCP tool
- **`InstagramMcpServer`**: Main server orchestrator with graceful shutdown

### Error Handling

The server implements comprehensive error handling:

- **Network Errors**: Automatic retry with exponential backoff
- **Instagram Blocks**: Graceful degradation with clear error messages
- **Browser Issues**: Detailed logging and recovery mechanisms
- **File System Errors**: Proper cleanup and error reporting

## Troubleshooting

### Common Issues

#### "Profile not found" Error
- Verify the username is correct (without @ symbol)
- Check if the profile is private and requires authentication
- Ensure Chrome user data directory is configured

#### "Browser connection failed"
- Verify Chrome/Chromium is installed
- Check Chrome user data directory permissions
- Try running in non-headless mode for debugging

#### Media download failures
- Ensure output directory exists and is writable
- Check available disk space
- Verify network connectivity

#### Rate limiting
- Reduce request frequency
- Use Chrome user data directory with logged-in session
- Implement delays between requests

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
INSTAGRAM_DEBUG=true npm start
```

### Health Check

Use the health check tool to verify server configuration:

```json
{
  "name": "instagram_health_check",
  "arguments": {
    "test_connection": true
  }
}
```

## Security Considerations

### Data Privacy
- No Instagram credentials are stored or transmitted
- Uses existing Chrome session for authentication
- All data processing happens locally

### Rate Limiting
- Implements respectful request timing
- Follows Instagram's robots.txt guidelines
- Includes automatic retry with backoff

### File Security
- Media files are downloaded to configurable local directories
- No external data transmission beyond Instagram's API
- Proper file permission handling

## Development

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make changes and add tests
4. Run linting: `npm run lint`
5. Build and test: `npm run build && npm test`
6. Submit a pull request

### Code Style

- **TypeScript**: Strict mode enabled
- **Formatting**: ESLint with recommended rules
- **Documentation**: Comprehensive JSDoc comments
- **Testing**: Jest for unit and integration tests

### Architecture Decisions

- **Puppeteer over API**: Instagram's web interface is more stable than unofficial APIs
- **TypeScript**: Full type safety and better developer experience
- **Modular Design**: Each tool is a separate class for maintainability
- **Error-First**: Comprehensive error handling at every level

## License

MIT License - see LICENSE file for details.

## Changelog

### v1.0.0 (2024-01-15)
- Initial release
- Core Instagram tools implementation
- Browser automation with Puppeteer
- Comprehensive error handling
- Production-ready TypeScript implementation

---

**Built for the DevQ.ai Machina MCP Registry** | [Documentation](https://github.com/devqai/machina) | [Issues](https://github.com/devqai/machina/issues)