import { z } from 'zod';
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

export abstract class BaseTool {
  abstract name: string;
  abstract description: string;
  abstract schema: z.ZodObject<any>;

  register(server: McpServer) {
    server.tool(
      this.name,
      this.description,
      this.schema.shape,
      this.execute.bind(this)
    );
  }

  abstract execute(args: z.infer<typeof this.schema>): Promise<{
    content: Array<{ type: "text"; text: string }>;
  }>;

  protected logInfo(message: string, data?: any) {
    console.error(`[INFO] [${this.name}] ${message}`, data ? JSON.stringify(data) : '');
  }

  protected logError(message: string, error?: any) {
    console.error(`[ERROR] [${this.name}] ${message}`, error?.message || error || '');
  }

  protected logDebug(message: string, data?: any) {
    if (process.env.INSTAGRAM_DEBUG === 'true') {
      console.error(`[DEBUG] [${this.name}] ${message}`, data ? JSON.stringify(data) : '');
    }
  }
}