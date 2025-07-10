export interface InstagramPost {
  id: string;
  url: string;
  caption: string;
  timestamp: string;
  likes: number;
  comments: number;
  mediaType: 'image' | 'video' | 'carousel';
  mediaUrls: string[];
  username: string;
  isSponsored: boolean;
}

export interface InstagramProfile {
  username: string;
  displayName: string;
  bio: string;
  followers: number;
  following: number;
  posts: number;
  profilePicUrl: string;
  isVerified: boolean;
  isPrivate: boolean;
  externalUrl?: string;
}

export interface InstagramMediaInfo {
  url: string;
  type: 'image' | 'video';
  width: number;
  height: number;
  size?: number;
  filename: string;
}

export interface ServerConfig {
  chromeUserDataDir?: string;
  timeout: number;
  retryAttempts: number;
  outputDir: string;
  headless: boolean;
  userAgent: string;
  viewport: {
    width: number;
    height: number;
  };
}

export interface InstagramApiError extends Error {
  code: string;
  details?: any;
}