import { DomainDetector } from '../shared/DomainDetector.js';
import { LegalKnowledgeBase } from '../shared/LegalKnowledgeBase.js';
import { LegalAskFollowupQuestionInput, LegalAskFollowupQuestionResponse, ToolResponse } from '../shared/types.js';
import { logger } from '../utils/logger.js';

/**
 * LegalAskFollowupQuestionTool class for implementing the legal_ask_followup_question tool
 */
export class LegalAskFollowupQuestionTool {
  private domainDetector: DomainDetector;
  private legalKnowledgeBase: LegalKnowledgeBase;
  
  /**
   * Constructor
   * @param domainDetector - Domain detector instance
   * @param legalKnowledgeBase - Legal knowledge base instance
   */
  constructor(
    domainDetector: DomainDetector,
    legalKnowledgeBase: LegalKnowledgeBase
  ) {
    this.domainDetector = domainDetector;
    this.legalKnowledgeBase = legalKnowledgeBase;
    
    logger.info('LegalAskFollowupQuestionTool initialized');
  }
  
  /**
   * Process a question request
   * @param input - The input data
   * @returns Tool response
   */
  public processQuestion(input: unknown): ToolResponse {
    try {
      logger.debug('Processing question request', input);
      
      // Validate input
      const validatedInput = this.validateQuestionData(input as LegalAskFollowupQuestionInput);
      
      // Detect domain from question and context
      const textToAnalyze = validatedInput.context 
        ? `${validatedInput.question} ${validatedInput.context}`
        : validatedInput.question;
      const domain = this.domainDetector.detectDomain(textToAnalyze);
      
      // If no options provided, suggest domain-specific options
      let options = validatedInput.options;
      if (!options || options.length === 0) {
        options = this.suggestDomainSpecificOptions(validatedInput.question, domain);
      }
      
      // Format the question with legal terminology
      const formattedQuestion = this.formatLegalQuestion(validatedInput.question, domain);
      
      // Prepare response
      const response: LegalAskFollowupQuestionResponse = {
        question: formattedQuestion,
        options: options,
        detectedDomain: domain
      };
      
      logger.debug('Question processed successfully', response);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify(response, null, 2)
        }]
      };
    } catch (error) {
      // Log and handle errors
      logger.error('Error processing question', error as Error);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify({
            error: error instanceof Error ? error.message : String(error),
            status: 'failed'
          }, null, 2)
        }],
        isError: true
      };
    }
  }
  
  /**
   * Validate question data
   * @param input - The input to validate
   * @returns Validated input
   * @throws Error if validation fails
   */
  private validateQuestionData(input: LegalAskFollowupQuestionInput): LegalAskFollowupQuestionInput {
    if (!input) {
      throw new Error('Input is required');
    }
    
    if (!input.question || typeof input.question !== 'string') {
      throw new Error('Question must be a non-empty string');
    }
    
    // Validate options if provided
    if (input.options) {
      if (!Array.isArray(input.options)) {
        throw new Error('Options must be an array');
      }
      
      if (input.options.length > 0 && input.options.length < 2) {
        throw new Error('Options must contain at least 2 items');
      }
      
      if (input.options.length > 5) {
        throw new Error('Options must contain at most 5 items');
      }
      
      for (const option of input.options) {
        if (typeof option !== 'string' || option.trim() === '') {
          throw new Error('Each option must be a non-empty string');
        }
      }
    }
    
    return {
      question: input.question,
      options: input.options,
      context: input.context
    };
  }
  
  /**
   * Suggest domain-specific options based on the question and domain
   * @param question - The question
   * @param domain - The detected domain
   * @returns Array of suggested options
   */
  private suggestDomainSpecificOptions(question: string, domain: string): string[] {
    // Get domain-specific question templates
    const templates = this.legalKnowledgeBase.getQuestionTemplates(domain);
    
    // Select most relevant templates based on question
    const relevantTemplates = this.selectRelevantTemplates(question, templates);
    
    // Return up to 4 options
    return relevantTemplates.slice(0, 4);
  }
  
  /**
   * Select the most relevant templates based on the question
   * @param question - The question
   * @param templates - Available templates
   * @returns Array of relevant templates
   */
  private selectRelevantTemplates(question: string, templates: string[]): string[] {
    // Simple relevance scoring based on keyword matching
    const scoredTemplates = templates.map(template => {
      const words = question.toLowerCase().split(/\s+/);
      let score = 0;
      
      for (const word of words) {
        if (word.length > 3 && template.toLowerCase().includes(word)) {
          score += 1;
        }
      }
      
      return { template, score };
    });
    
    // Sort by score (descending)
    scoredTemplates.sort((a, b) => b.score - a.score);
    
    // Return templates
    return scoredTemplates.map(item => item.template);
  }
  
  /**
   * Format a question with appropriate legal terminology
   * @param question - The original question
   * @param domain - The detected domain
   * @returns Formatted question
   */
  private formatLegalQuestion(question: string, domain: string): string {
    // Add domain-specific legal terminology if not present
    if (domain === 'ansc_contestation') {
      if (!question.includes('procurement') && !question.includes('tender') && !question.includes('ANSC')) {
        question = question.replace(/specifications/i, 'procurement specifications');
        question = question.replace(/requirements/i, 'tender requirements');
      }
    } else if (domain === 'consumer_protection') {
      if (!question.includes('warranty') && !question.includes('consumer')) {
        question = question.replace(/product/i, 'consumer product');
        question = question.replace(/refund/i, 'consumer refund');
      }
    } else if (domain === 'contract_analysis') {
      if (!question.includes('clause') && !question.includes('contract')) {
        question = question.replace(/agreement/i, 'contractual agreement');
        question = question.replace(/terms/i, 'contractual terms');
      }
    }
    
    // Ensure question ends with a question mark
    if (!question.endsWith('?')) {
      question += '?';
    }
    
    return question;
  }
}