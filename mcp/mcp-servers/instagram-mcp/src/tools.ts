import { z } from 'zod';
import { BaseTool } from './base-tool.js';
import { InstagramClient } from './instagram-client.js';

const client = new InstagramClient();

export class GetInstagramPostsTool extends BaseTool {
  name = "get_instagram_posts";
  description = "Fetch recent posts from an Instagram profile with optional media downloading";
  schema = z.object({
    username: z.string().min(1).describe("Instagram username (without @)"),
    limit: z.number().min(1).max(50).default(10).describe("Number of posts to fetch (1-50)"),
    include_media: z.boolean().default(false).describe("Download media files to local storage"),
    output_dir: z.string().optional().describe("Custom output directory for media files")
  });

  async execute({ username, limit, include_media, output_dir }: z.infer<typeof this.schema>) {
    try {
      this.logInfo(`Fetching ${limit} posts for @${username}`, { include_media, output_dir });
      
      // Set custom output directory if provided
      if (output_dir) {
        // Update config temporarily
        const { config } = await import('./config.js');
        config.outputDir = output_dir;
      }
      
      const posts = await client.getPosts(username, limit);
      
      if (include_media && posts.length > 0) {
        this.logInfo(`Downloading media for ${posts.length} posts`);
        
        for (const post of posts) {
          for (let i = 0; i < post.mediaUrls.length; i++) {
            const mediaUrl = post.mediaUrls[i];
            const extension = post.mediaType === 'video' ? 'mp4' : 'jpg';
            const filename = `${username}_${post.id}_${i}.${extension}`;
            
            try {
              const filePath = await client.downloadMedia(mediaUrl, filename);
              this.logInfo(`Media downloaded: ${filePath}`);
            } catch (error) {
              const errorMessage = error instanceof Error ? error.message : String(error);
              this.logError(`Failed to download media for post ${post.id}`, errorMessage);
            }
          }
        }
      }
      
      const result = {
        username,
        posts,
        total: posts.length,
        media_downloaded: include_media,
        timestamp: new Date().toISOString()
      };
      
      this.logInfo(`Successfully fetched ${posts.length} posts for @${username}`);
      
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify(result, null, 2)
        }]
      };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.logError(`Failed to fetch Instagram posts for @${username}`, errorMessage);
      throw new Error(`Instagram fetch failed: ${errorMessage}`);
    }
  }
}

export class GetInstagramProfileTool extends BaseTool {
  name = "get_instagram_profile";
  description = "Get detailed information about an Instagram profile including stats and bio";
  schema = z.object({
    username: z.string().min(1).describe("Instagram username (without @)"),
    include_avatar: z.boolean().default(false).describe("Download profile avatar image")
  });

  async execute({ username, include_avatar }: z.infer<typeof this.schema>) {
    try {
      this.logInfo(`Fetching profile information for @${username}`, { include_avatar });
      
      const profile = await client.getProfile(username);
      
      let avatarPath: string | undefined;
      if (include_avatar && profile.profilePicUrl) {
        try {
          const filename = `${username}_avatar.jpg`;
          avatarPath = await client.downloadMedia(profile.profilePicUrl, filename);
          this.logInfo(`Profile avatar downloaded: ${avatarPath}`);
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : String(error);
          this.logError(`Failed to download avatar for @${username}`, errorMessage);
        }
      }
      
      const result = {
        ...profile,
        avatar_downloaded: !!avatarPath,
        avatar_path: avatarPath,
        timestamp: new Date().toISOString()
      };
      
      this.logInfo(`Successfully fetched profile for @${username}`, { 
        followers: profile.followers, 
        posts: profile.posts 
      });
      
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify(result, null, 2)
        }]
      };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.logError(`Failed to fetch Instagram profile for @${username}`, errorMessage);
      throw new Error(`Profile fetch failed: ${errorMessage}`);
    }
  }
}

export class GetInstagramMediaTool extends BaseTool {
  name = "get_instagram_media";
  description = "Download specific media from Instagram posts by URL";
  schema = z.object({
    media_urls: z.array(z.string().url()).describe("Array of Instagram media URLs to download"),
    output_dir: z.string().optional().describe("Custom output directory for downloaded files"),
    filename_prefix: z.string().optional().describe("Prefix for downloaded filenames")
  });

  async execute({ media_urls, output_dir, filename_prefix }: z.infer<typeof this.schema>) {
    try {
      this.logInfo(`Downloading ${media_urls.length} media files`, { output_dir, filename_prefix });
      
      // Set custom output directory if provided
      if (output_dir) {
        const { config } = await import('./config.js');
        config.outputDir = output_dir;
      }
      
      const downloaded: Array<{ url: string; filename: string; path: string; success: boolean; error?: string }> = [];
      
      for (let i = 0; i < media_urls.length; i++) {
        const mediaUrl = media_urls[i];
        const prefix = filename_prefix || 'instagram_media';
        const extension = mediaUrl.includes('.mp4') ? 'mp4' : 'jpg';
        const filename = `${prefix}_${i + 1}.${extension}`;
        
        try {
          const filePath = await client.downloadMedia(mediaUrl, filename);
          downloaded.push({
            url: mediaUrl,
            filename,
            path: filePath,
            success: true
          });
          this.logInfo(`Media downloaded: ${filename}`);
        } catch (error) {
          downloaded.push({
            url: mediaUrl,
            filename,
            path: '',
            success: false,
            error: error instanceof Error ? error.message : String(error)
          });
          const errorMessage = error instanceof Error ? error.message : String(error);
          this.logError(`Failed to download media: ${mediaUrl}`, errorMessage);
        }
      }
      
      const successful = downloaded.filter(d => d.success).length;
      const failed = downloaded.length - successful;
      
      const result = {
        downloaded_files: downloaded,
        summary: {
          total: media_urls.length,
          successful,
          failed
        },
        timestamp: new Date().toISOString()
      };
      
      this.logInfo(`Media download completed: ${successful}/${media_urls.length} successful`);
      
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify(result, null, 2)
        }]
      };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.logError(`Failed to download Instagram media`, errorMessage);
      throw new Error(`Media download failed: ${errorMessage}`);
    }
  }
}

export class InstagramHealthCheckTool extends BaseTool {
  name = "instagram_health_check";
  description = "Check the health and configuration of the Instagram MCP server";
  schema = z.object({
    test_connection: z.boolean().default(true).describe("Test browser connection to Instagram")
  });

  async execute({ test_connection }: z.infer<typeof this.schema>) {
    try {
      this.logInfo("Running Instagram MCP server health check");
      
      const { config } = await import('./config.js');
      
      const healthInfo = {
        server_status: "healthy",
        configuration: {
          chrome_user_data_dir: config.chromeUserDataDir || "not_configured",
          timeout: config.timeout,
          retry_attempts: config.retryAttempts,
          output_dir: config.outputDir,
          headless: config.headless,
          viewport: config.viewport
        },
        environment: {
          node_version: process.version,
          platform: process.platform,
          arch: process.arch
        },
        connection_test: null as any
      };
      
      if (test_connection) {
        try {
          await client.initialize();
          healthInfo.connection_test = {
            status: "success",
            message: "Browser connection established successfully"
          };
          this.logInfo("Browser connection test passed");
        } catch (error) {
          healthInfo.connection_test = {
            status: "failed",
            message: error instanceof Error ? error.message : String(error)
          };
          const errorMessage = error instanceof Error ? error.message : String(error);
          this.logError("Browser connection test failed", errorMessage);
        } finally {
          await client.close();
        }
      }
      
      return {
        content: [{
          type: "text" as const,
          text: JSON.stringify(healthInfo, null, 2)
        }]
      };
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      this.logError("Health check failed", errorMessage);
      throw new Error(`Health check failed: ${errorMessage}`);
    }
  }
}