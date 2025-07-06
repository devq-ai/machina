import { ServerConfig } from './types.js';

export const config: ServerConfig = {
  chromeUserDataDir: process.env.CHROME_USER_DATA_DIR,
  timeout: parseInt(process.env.INSTAGRAM_TIMEOUT || '30000'),
  retryAttempts: parseInt(process.env.INSTAGRAM_RETRY_ATTEMPTS || '3'),
  outputDir: process.env.INSTAGRAM_OUTPUT_DIR || './downloads',
  headless: process.env.INSTAGRAM_HEADLESS !== 'false',
  userAgent: process.env.INSTAGRAM_USER_AGENT || 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  viewport: {
    width: parseInt(process.env.INSTAGRAM_VIEWPORT_WIDTH || '1920'),
    height: parseInt(process.env.INSTAGRAM_VIEWPORT_HEIGHT || '1080')
  }
};

export const INSTAGRAM_SELECTORS = {
  LOGIN_FORM: 'form[data-testid="royal_login_form"]',
  USERNAME_INPUT: 'input[name="username"]',
  PASSWORD_INPUT: 'input[name="password"]',
  LOGIN_BUTTON: 'button[type="submit"]',
  POST_ARTICLE: 'article[role="presentation"]',
  POST_LINK: 'a[href*="/p/"]',
  POST_IMAGE: 'img',
  POST_VIDEO: 'video',
  POST_CAPTION: '[data-testid="post-comment-text"]',
  POST_LIKES: 'button[data-testid="media-like-button"] + span',
  PROFILE_USERNAME: 'h2',
  PROFILE_BIO: '[data-testid="user-bio"]',
  PROFILE_STATS: 'ul > li',
  PROFILE_AVATAR: 'img[data-testid="user-avatar"]',
  NEXT_BUTTON: 'button[aria-label="Next"]',
  LOAD_MORE: 'button:has-text("Show more posts")'
} as const;