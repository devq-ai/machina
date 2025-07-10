import puppeteer, { Browser, Page } from 'puppeteer';
import { config, INSTAGRAM_SELECTORS } from './config.js';
import { InstagramPost, InstagramProfile } from './types.js';
import * as fs from 'fs-extra';
import * as path from 'path';

export class InstagramClient {
  private browser: Browser | null = null;
  private page: Page | null = null;
  private isInitialized = false;

  async initialize(): Promise<void> {
    if (this.isInitialized) return;

    try {
      console.error('[INFO] Initializing Instagram client...');
      
      const launchOptions: any = {
        headless: config.headless,
        args: [
          '--no-sandbox',
          '--disable-setuid-sandbox',
          '--disable-dev-shm-usage',
          '--disable-accelerated-2d-canvas',
          '--no-first-run',
          '--no-zygote',
          '--disable-gpu'
        ]
      };

      if (config.chromeUserDataDir) {
        launchOptions.userDataDir = config.chromeUserDataDir;
        console.error(`[INFO] Using Chrome user data directory: ${config.chromeUserDataDir}`);
      }

      this.browser = await puppeteer.launch(launchOptions);
      this.page = await this.browser.newPage();
      
      await this.page.setUserAgent(config.userAgent);
      await this.page.setViewport(config.viewport);
      
      // Set timeout
      this.page.setDefaultTimeout(config.timeout);
      
      this.isInitialized = true;
      console.error('[INFO] Instagram client initialized successfully');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new InstagramApiError(`Failed to initialize Instagram client: ${errorMessage}`, 'INIT_ERROR');
    }
  }

  async navigateToProfile(username: string): Promise<void> {
    if (!this.page) throw new InstagramApiError('Client not initialized', 'NOT_INITIALIZED');
    
    console.error(`[INFO] Navigating to profile: ${username}`);
    const profileUrl = `https://www.instagram.com/${username}/`;
    
    try {
      await this.page.goto(profileUrl, { waitUntil: 'networkidle2' });
      
      // Check if profile exists
      const notFound = await this.page.$('h2');
      const notFoundText = notFound ? await this.page.evaluate(el => el.textContent, notFound) : '';
      if (notFoundText?.includes("Sorry, this page isn't available.")) {
        throw new InstagramApiError(`Profile @${username} not found`, 'PROFILE_NOT_FOUND');
      }
      
      // Check if profile is private
      const isPrivate = await this.page.$('[data-testid="private-account-message"]');
      if (isPrivate) {
        console.error(`[WARN] Profile @${username} is private`);
      }
      
    } catch (error) {
      if (error instanceof InstagramApiError) throw error;
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new InstagramApiError(`Failed to navigate to profile: ${errorMessage}`, 'NAVIGATION_ERROR');
    }
  }

  async getProfile(username: string): Promise<InstagramProfile> {
    await this.initialize();
    await this.navigateToProfile(username);
    
    if (!this.page) throw new InstagramApiError('Client not initialized', 'NOT_INITIALIZED');
    
    try {
      console.error(`[INFO] Extracting profile data for @${username}`);
      
      const profile = await this.page.evaluate(() => {
        const getTextContent = (selector: string): string => {
          const element = document.querySelector(selector);
          return element?.textContent?.trim() || '';
        };
        
        const getNumber = (text: string): number => {
          const match = text.match(/([\\d,]+)/);
          return match ? parseInt(match[1].replace(/,/g, '')) : 0;
        };

        // Extract profile information
        const displayName = getTextContent('h2');
        const bio = getTextContent('[data-testid="user-bio"]');
        
        // Extract stats
        const statsElements = Array.from(document.querySelectorAll('ul > li'));
        let followers = 0, following = 0, posts = 0;
        
        statsElements.forEach((el: Element) => {
          const text = el.textContent || '';
          if (text.includes('posts')) posts = getNumber(text);
          if (text.includes('followers')) followers = getNumber(text);
          if (text.includes('following')) following = getNumber(text);
        });
        
        // Extract profile picture
        const profilePicElement = document.querySelector('img[data-testid="user-avatar"]') as HTMLImageElement;
        const profilePicUrl = profilePicElement?.src || '';
        
        // Check verification status
        const isVerified = !!document.querySelector('[title="Verified"]');
        
        // Check if private
        const isPrivate = !!document.querySelector('[data-testid="private-account-message"]');
        
        // External URL
        const externalLinkElement = document.querySelector('a[href*="l.instagram.com"]') as HTMLAnchorElement;
        const externalUrl = externalLinkElement?.href;
        
        return {
          displayName,
          bio,
          followers,
          following,
          posts,
          profilePicUrl,
          isVerified,
          isPrivate,
          externalUrl
        };
      });
      
      const result: InstagramProfile = {
        username,
        displayName: profile.displayName,
        bio: profile.bio,
        followers: profile.followers,
        following: profile.following,
        posts: profile.posts,
        profilePicUrl: profile.profilePicUrl,
        isVerified: profile.isVerified,
        isPrivate: profile.isPrivate,
        externalUrl: profile.externalUrl
      };
      
      console.error(`[INFO] Profile extracted: ${result.followers} followers, ${result.posts} posts`);
      return result;
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new InstagramApiError(`Failed to extract profile data: ${errorMessage}`, 'PROFILE_EXTRACTION_ERROR');
    }
  }

  async getPosts(username: string, limit: number = 10): Promise<InstagramPost[]> {
    await this.initialize();
    await this.navigateToProfile(username);
    
    if (!this.page) throw new InstagramApiError('Client not initialized', 'NOT_INITIALIZED');
    
    try {
      console.error(`[INFO] Extracting ${limit} posts for @${username}`);
      
      // Wait for posts to load
      await this.page.waitForSelector('article', { timeout: 10000 });
      
      const posts = await this.page.evaluate((limit: number) => {
        const postElements = Array.from(document.querySelectorAll('article a[href*="/p/"]')).slice(0, limit);
        
        return postElements.map((postLink: Element, index: number) => {
          const href = (postLink as HTMLAnchorElement).href;
          const postId = href.match(/\/p\/([^/]+)/)?.[1] || `post_${index}`;
          
          // Extract image/video
          const mediaElement = postLink.querySelector('img, video') as HTMLImageElement | HTMLVideoElement;
          const mediaUrl = mediaElement?.src || '';
          const mediaType = mediaElement?.tagName.toLowerCase() === 'video' ? 'video' : 'image';
          
          // Try to extract basic info from thumbnail view
          const altText = (mediaElement as HTMLImageElement)?.alt || '';
          
          return {
            id: postId,
            url: href,
            caption: altText,
            timestamp: new Date().toISOString(), // Placeholder - would need post detail page
            likes: 0, // Would need post detail page
            comments: 0, // Would need post detail page
            mediaType: mediaType as 'image' | 'video' | 'carousel',
            mediaUrls: [mediaUrl],
            username: window.location.pathname.split('/')[1],
            isSponsored: false
          };
        });
      }, limit);
      
      console.error(`[INFO] Extracted ${posts.length} posts`);
      return posts as InstagramPost[];
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new InstagramApiError(`Failed to extract posts: ${errorMessage}`, 'POSTS_EXTRACTION_ERROR');
    }
  }

  async downloadMedia(mediaUrl: string, filename: string): Promise<string> {
    if (!this.page) throw new InstagramApiError('Client not initialized', 'NOT_INITIALIZED');
    
    try {
      console.error(`[INFO] Downloading media: ${filename}`);
      
      // Ensure output directory exists
      await fs.ensureDir(config.outputDir);
      
      const filePath = path.join(config.outputDir, filename);
      
      // Navigate to media URL and download
      await this.page.goto(mediaUrl);
      const response = await this.page.goto(mediaUrl);
      
      if (response) {
        const buffer = await response.buffer();
        await fs.writeFile(filePath, buffer);
        console.error(`[INFO] Media downloaded: ${filePath}`);
        return filePath;
      }
      
      throw new Error('No response received');
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      throw new InstagramApiError(`Failed to download media: ${errorMessage}`, 'DOWNLOAD_ERROR');
    }
  }

  async close(): Promise<void> {
    if (this.browser) {
      console.error('[INFO] Closing Instagram client...');
      await this.browser.close();
      this.browser = null;
      this.page = null;
      this.isInitialized = false;
    }
  }
}

// Custom error class for Instagram API errors
class InstagramApiError extends Error {
  constructor(message: string, public code: string, public details?: any) {
    super(message);
    this.name = 'InstagramApiError';
  }
}