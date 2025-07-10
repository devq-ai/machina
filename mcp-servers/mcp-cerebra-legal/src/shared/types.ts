/**
 * Common types used throughout the application
 */
import { TextContent, ImageContent, EmbeddedResource } from '@modelcontextprotocol/sdk/types.js';

/**
 * Legal think tool input data
 */
export interface LegalThinkInput {
  thought: string;
  category?: string;
  references?: string[];
  isRevision?: boolean;
  revisesThoughtNumber?: number;
  requestGuidance?: boolean;
  requestTemplate?: boolean;
  thoughtNumber: number;
  totalThoughts: number;
  nextThoughtNeeded: boolean;
}

/**
 * Legal think tool response data
 */
export interface LegalThinkResponse {
  thoughtNumber: number;
  totalThoughts: number;
  nextThoughtNeeded: boolean;
  detectedDomain: string;
  guidance?: string;
  template?: string;
  feedback?: string;
  thoughtHistoryLength: number;
}

/**
 * Legal ask followup question input data
 */
export interface LegalAskFollowupQuestionInput {
  question: string;
  options?: string[];
  context?: string;
}

/**
 * Legal ask followup question response data
 */
export interface LegalAskFollowupQuestionResponse {
  question: string;
  options: string[];
  detectedDomain: string;
}

/**
 * Legal attempt completion input data
 */
export interface LegalAttemptCompletionInput {
  result: string;
  command?: string;
  context?: string;
}

/**
 * Legal attempt completion response data
 */
export interface LegalAttemptCompletionResponse {
  result: string;
  command?: string;
  detectedDomain: string;
  formattedCitations: string[];
}

/**
 * Stored thought data
 */
export interface ThoughtData extends LegalThinkInput {
  id: string;
  timestamp: Date;
  detectedDomain: string;
}

/**
 * Error response
 */
export interface ErrorResponse {
  error: string;
  status: 'failed';
}

/**
 * MCP tool response
 */
export interface ToolResponse {
  content: (TextContent | ImageContent | EmbeddedResource)[];
  isError?: boolean;
}