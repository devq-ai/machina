#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { 
  GetInstagramPostsTool, 
  GetInstagramProfileTool, 
  GetInstagramMediaTool,
  InstagramHealthCheckTool 
} from './tools.js';

class InstagramMcpServer {
  private server: McpServer;
  private tools: Array<InstanceType<typeof GetInstagramPostsTool | typeof GetInstagramProfileTool | typeof GetInstagramMediaTool | typeof InstagramHealthCheckTool>> = [];

  constructor() {
    this.server = new McpServer({
      name: "instagram-mcp",
      version: "1.0.0"
    });

    this.setupGracefulShutdown();
    this.initializeTools();
  }

  private initializeTools() {
    console.error('[INFO] Initializing Instagram MCP tools...');
    
    // Initialize all tools
    const tools = [
      new GetInstagramPostsTool(),
      new GetInstagramProfileTool(), 
      new GetInstagramMediaTool(),
      new InstagramHealthCheckTool()
    ];

    // Register each tool with the server
    tools.forEach(tool => {
      this.tools.push(tool);
      tool.register(this.server);
      console.error(`[INFO] Registered tool: ${tool.name}`);
    });

    console.error(`[INFO] Successfully registered ${tools.length} Instagram tools`);
  }

  private setupGracefulShutdown() {
    const shutdown = async (signal: string) => {
      console.error(`[INFO] Received ${signal}, shutting down gracefully...`);
      try {
        // Add any cleanup logic here
        console.error('[INFO] Instagram MCP server shutdown complete');
        process.exit(0);
      } catch (error) {
        console.error('[ERROR] Error during shutdown:', error);
        process.exit(1);
      }
    };

    process.on('SIGINT', () => shutdown('SIGINT'));
    process.on('SIGTERM', () => shutdown('SIGTERM'));
    
    // Handle uncaught exceptions
    process.on('uncaughtException', (error) => {
      console.error('[ERROR] Uncaught exception:', error);
      process.exit(1);
    });

    process.on('unhandledRejection', (reason) => {
      console.error('[ERROR] Unhandled rejection:', reason);
      process.exit(1);
    });
  }

  async start() {
    try {
      console.error('[INFO] Starting Instagram MCP server...');
      
      // Log configuration
      const { config } = await import('./config.js');
      console.error('[INFO] Server configuration:', {
        headless: config.headless,
        timeout: config.timeout,
        outputDir: config.outputDir,
        chromeUserDataDir: config.chromeUserDataDir ? 'configured' : 'not_configured'
      });

      // Connect to stdio transport
      const transport = new StdioServerTransport();
      await this.server.connect(transport);
      
      console.error('[INFO] Instagram MCP server started successfully');
      console.error('[INFO] Available tools:', this.tools.map(t => t.name));
      console.error('[INFO] Server ready for requests via stdio transport');
      
    } catch (error) {
      console.error('[ERROR] Failed to start Instagram MCP server:', error);
      process.exit(1);
    }
  }
}

// Create and start the server
const server = new InstagramMcpServer();
server.start().catch(error => {
  console.error('[FATAL] Server startup failed:', error);
  process.exit(1);
});