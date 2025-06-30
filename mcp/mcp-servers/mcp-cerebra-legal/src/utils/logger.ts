import chalk from 'chalk';

/**
 * Logger utility for consistent logging throughout the application
 */
export class Logger {
  private static instance: Logger;
  private logLevel: LogLevel;
  
  /**
   * Private constructor to enforce singleton pattern
   */
  private constructor() {
    // Default to info level
    this.logLevel = LogLevel.INFO;
  }
  
  /**
   * Get the singleton instance
   */
  public static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }
  
  /**
   * Set the log level
   * @param level - The log level to set
   */
  public setLogLevel(level: LogLevel): void {
    this.logLevel = level;
  }
  
  /**
   * Log a debug message
   * @param message - The message to log
   * @param context - Optional context information
   */
  public debug(message: string, context?: any): void {
    if (this.logLevel <= LogLevel.DEBUG) {
      console.error(chalk.gray(`[DEBUG] ${message}`));
      if (context) {
        console.error(chalk.gray(JSON.stringify(context, null, 2)));
      }
    }
  }
  
  /**
   * Log an info message
   * @param message - The message to log
   * @param context - Optional context information
   */
  public info(message: string, context?: any): void {
    if (this.logLevel <= LogLevel.INFO) {
      console.error(chalk.blue(`[INFO] ${message}`));
      if (context) {
        console.error(chalk.blue(JSON.stringify(context, null, 2)));
      }
    }
  }
  
  /**
   * Log a warning message
   * @param message - The message to log
   * @param context - Optional context information
   */
  public warn(message: string, context?: any): void {
    if (this.logLevel <= LogLevel.WARN) {
      console.error(chalk.yellow(`[WARN] ${message}`));
      if (context) {
        console.error(chalk.yellow(JSON.stringify(context, null, 2)));
      }
    }
  }
  
  /**
   * Log an error message
   * @param message - The message to log
   * @param error - Optional error object
   * @param context - Optional context information
   */
  public error(message: string, error?: Error, context?: any): void {
    if (this.logLevel <= LogLevel.ERROR) {
      console.error(chalk.red(`[ERROR] ${message}`));
      if (error) {
        console.error(chalk.red(error.stack || error.message));
      }
      if (context) {
        console.error(chalk.red(JSON.stringify(context, null, 2)));
      }
    }
  }
  
  /**
   * Format a thought with borders and colors
   * @param thought - The thought content
   * @param category - The thought category
   * @param thoughtNumber - The thought number
   * @param totalThoughts - The total number of thoughts
   * @param isRevision - Whether this is a revision
   * @param revisesThoughtNumber - The thought number being revised
   * @returns Formatted thought string
   */
  public formatThought(
    thought: string,
    category: string,
    thoughtNumber: number,
    totalThoughts: number,
    isRevision?: boolean,
    revisesThoughtNumber?: number
  ): string {
    let prefix = '';
    let context = '';
    let color = chalk.blue;
    
    // Determine color and prefix based on category
    switch (category) {
      case 'ansc_contestation':
        color = chalk.magenta;
        prefix = 'ANSC Analysis';
        break;
      case 'consumer_protection':
        color = chalk.green;
        prefix = 'Consumer Protection';
        break;
      case 'contract_analysis':
        color = chalk.cyan;
        prefix = 'Contract Analysis';
        break;
      case 'legal_reasoning':
        color = chalk.blue;
        prefix = 'Legal Reasoning';
        break;
      default:
        color = chalk.blue;
        prefix = 'Thought';
    }
    
    // Add revision information if applicable
    if (isRevision) {
      prefix = chalk.yellow(`${prefix} (Revision)`);
      context = ` (revising thought ${revisesThoughtNumber})`;
    }
    
    const header = `${prefix} ${thoughtNumber}/${totalThoughts}${context}`;
    const border = '─'.repeat(Math.max(header.length, thought.length) + 4);
    
    return `
┌${border}┐
│ ${color(header)} │
├${border}┤
│ ${thought.padEnd(border.length - 2)} │
└${border}┘`;
  }
}

/**
 * Log levels enum
 */
export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

// Export a default instance
export const logger = Logger.getInstance();