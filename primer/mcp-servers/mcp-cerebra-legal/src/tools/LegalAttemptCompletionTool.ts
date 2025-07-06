import { DomainDetector } from '../shared/DomainDetector.js';
import { LegalKnowledgeBase } from '../shared/LegalKnowledgeBase.js';
import { CitationFormatter } from '../shared/CitationFormatter.js';
import { LegalAttemptCompletionInput, LegalAttemptCompletionResponse, ToolResponse } from '../shared/types.js';
import { logger } from '../utils/logger.js';

/**
 * LegalAttemptCompletionTool class for implementing the legal_attempt_completion tool
 */
export class LegalAttemptCompletionTool {
  private domainDetector: DomainDetector;
  private legalKnowledgeBase: LegalKnowledgeBase;
  private citationFormatter: CitationFormatter;
  
  /**
   * Constructor
   * @param domainDetector - Domain detector instance
   * @param legalKnowledgeBase - Legal knowledge base instance
   * @param citationFormatter - Citation formatter instance
   */
  constructor(
    domainDetector: DomainDetector,
    legalKnowledgeBase: LegalKnowledgeBase,
    citationFormatter: CitationFormatter
  ) {
    this.domainDetector = domainDetector;
    this.legalKnowledgeBase = legalKnowledgeBase;
    this.citationFormatter = citationFormatter;
    
    logger.info('LegalAttemptCompletionTool initialized');
  }
  
  /**
   * Process a completion request
   * @param input - The input data
   * @returns Tool response
   */
  public processCompletion(input: unknown): ToolResponse {
    try {
      logger.debug('Processing completion request', input);
      
      // Validate input
      const validatedInput = this.validateCompletionData(input as LegalAttemptCompletionInput);
      
      // Detect domain from result and context
      const textToAnalyze = validatedInput.context 
        ? `${validatedInput.result} ${validatedInput.context}`
        : validatedInput.result;
      const domain = this.domainDetector.detectDomain(textToAnalyze);
      
      // Format the result with proper legal structure
      const formattedResult = this.formatLegalResult(validatedInput.result, domain);
      
      // Extract and format citations in the result
      const citations = this.citationFormatter.extractCitations(validatedInput.result);
      const formattedCitations = citations.map(citation => 
        this.citationFormatter.formatLegalCitation(citation, domain)
      );
      
      // Prepare response
      const response: LegalAttemptCompletionResponse = {
        result: formattedResult,
        command: validatedInput.command,
        detectedDomain: domain,
        formattedCitations: formattedCitations
      };
      
      logger.debug('Completion processed successfully', response);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify(response, null, 2)
        }]
      };
    } catch (error) {
      // Log and handle errors
      logger.error('Error processing completion', error as Error);
      
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
   * Validate completion data
   * @param input - The input to validate
   * @returns Validated input
   * @throws Error if validation fails
   */
  private validateCompletionData(input: LegalAttemptCompletionInput): LegalAttemptCompletionInput {
    if (!input) {
      throw new Error('Input is required');
    }
    
    if (!input.result || typeof input.result !== 'string') {
      throw new Error('Result must be a non-empty string');
    }
    
    // Validate command if provided
    if (input.command !== undefined && (typeof input.command !== 'string' || input.command.trim() === '')) {
      throw new Error('Command must be a non-empty string if provided');
    }
    
    return {
      result: input.result,
      command: input.command,
      context: input.context
    };
  }
  
  /**
   * Format a result with appropriate legal structure
   * @param result - The original result
   * @param domain - The detected domain
   * @returns Formatted result
   */
  private formatLegalResult(result: string, domain: string): string {
    // If result already has a good structure, return it as is
    if (this.hasGoodStructure(result)) {
      return result;
    }
    
    // Get domain-specific completion template
    const template = this.legalKnowledgeBase.getCompletionTemplate(domain);
    
    // Try to apply the template structure while preserving content
    return this.applyTemplateStructure(result, template, domain);
  }
  
  /**
   * Check if the result already has a good structure
   * @param result - The result to check
   * @returns Whether the result has a good structure
   */
  private hasGoodStructure(result: string): boolean {
    // Check for section headers (numbered or with clear titles)
    const hasNumberedSections = /\n\s*\d+\.\s+[A-Z]/.test(result);
    const hasTitledSections = /\n\s*[A-Z][a-zA-Z\s]+:/.test(result);
    
    // Check for bullet points
    const hasBulletPoints = /\n\s*[-•*]\s+/.test(result);
    
    // Check for clear paragraphs
    const hasClearParagraphs = result.split('\n\n').length >= 3;
    
    return (hasNumberedSections || hasTitledSections) && (hasBulletPoints || hasClearParagraphs);
  }
  
  /**
   * Apply a template structure to the result while preserving content
   * @param result - The original result
   * @param template - The template to apply
   * @param domain - The detected domain
   * @returns Formatted result
   */
  private applyTemplateStructure(result: string, template: string, domain: string): string {
    // Extract sections from the template
    const templateSections = this.extractTemplateSections(template);
    
    // Try to extract content for each section from the result
    const contentSections: Record<string, string> = {};
    
    for (const section of templateSections) {
      const content = this.extractContentForSection(result, section, domain);
      contentSections[section] = content;
    }
    
    // Build the formatted result
    let formattedResult = '';
    
    // Add a title based on domain
    switch (domain) {
      case 'ansc_contestation':
        formattedResult += 'Legal Analysis Summary:\n\n';
        break;
      case 'consumer_protection':
        formattedResult += 'Consumer Protection Analysis:\n\n';
        break;
      case 'contract_analysis':
        formattedResult += 'Contract Analysis Report:\n\n';
        break;
      default:
        formattedResult += 'Legal Analysis Report:\n\n';
    }
    
    // Add a brief introduction if we can extract one
    const introMatch = result.match(/^([^.!?]+[.!?])/);
    if (introMatch) {
      formattedResult += `${introMatch[1]}\n\n`;
    }
    
    // Add each section with its content
    for (let i = 0; i < templateSections.length; i++) {
      const section = templateSections[i];
      const content = contentSections[section];
      
      formattedResult += `${i + 1}. ${section}:\n${content}\n\n`;
    }
    
    return formattedResult.trim();
  }
  
  /**
   * Extract sections from a template
   * @param template - The template
   * @returns Array of section names
   */
  private extractTemplateSections(template: string): string[] {
    const sections: string[] = [];
    
    // Look for numbered sections
    const sectionMatches = template.match(/\d+\.\s+([A-Z][^:]+):/g);
    
    if (sectionMatches) {
      for (const match of sectionMatches) {
        const sectionName = match.replace(/\d+\.\s+/, '').replace(':', '');
        sections.push(sectionName);
      }
    }
    
    // If no sections found, use default sections
    if (sections.length === 0) {
      sections.push('Key Findings', 'Legal Assessment', 'Recommended Action', 'Next Steps');
    }
    
    return sections;
  }
  
  /**
   * Extract content for a specific section from the result
   * @param result - The original result
   * @param section - The section name
   * @param domain - The detected domain
   * @returns Content for the section
   */
  private extractContentForSection(result: string, section: string, domain: string): string {
    // Define keywords for each section by domain
    const sectionKeywords: Record<string, Record<string, string[]>> = {
      'ansc_contestation': {
        'Key Findings': ['finding', 'claim', 'specification', 'requirement', 'challenge'],
        'Legal Assessment': ['assessment', 'analysis', 'law', 'article', 'provision', 'legal', 'compliance'],
        'Recommended Action': ['recommend', 'action', 'strategy', 'approach', 'response'],
        'Next Steps': ['next', 'step', 'timeline', 'procedure', 'document', 'submit']
      },
      'consumer_protection': {
        'Factual Assessment': ['fact', 'claim', 'product', 'warranty', 'consumer', 'retailer'],
        'Legal Position': ['position', 'law', 'right', 'obligation', 'protection', 'legal'],
        'Recommended Action': ['recommend', 'action', 'strategy', 'approach', 'response'],
        'Next Steps': ['next', 'step', 'timeline', 'communication', 'document']
      },
      'contract_analysis': {
        'Key Provisions Assessment': ['provision', 'clause', 'term', 'condition', 'agreement'],
        'Legal Implications': ['implication', 'consequence', 'effect', 'risk', 'liability'],
        'Recommended Action': ['recommend', 'action', 'strategy', 'approach', 'modification'],
        'Implementation Guidance': ['implement', 'guidance', 'step', 'procedure', 'monitor']
      },
      'legal_reasoning': {
        'Factual Summary': ['fact', 'summary', 'background', 'situation', 'circumstance'],
        'Legal Assessment': ['assessment', 'analysis', 'law', 'legal', 'principle', 'precedent'],
        'Recommended Position': ['position', 'recommendation', 'conclusion', 'opinion'],
        'Action Plan': ['action', 'plan', 'step', 'timeline', 'resource']
      }
    };
    
    // Get keywords for this section and domain
    const domainKeywords = sectionKeywords[domain] || sectionKeywords['legal_reasoning'];
    const keywords = domainKeywords[section] || [];
    
    // Split result into paragraphs
    const paragraphs = result.split('\n').filter(p => p.trim().length > 0);
    
    // Score each paragraph for relevance to this section
    const scoredParagraphs = paragraphs.map(paragraph => {
      let score = 0;
      
      // Check for section name in paragraph
      if (paragraph.toLowerCase().includes(section.toLowerCase())) {
        score += 5;
      }
      
      // Check for keywords
      for (const keyword of keywords) {
        if (paragraph.toLowerCase().includes(keyword.toLowerCase())) {
          score += 1;
        }
      }
      
      return { paragraph, score };
    });
    
    // Sort by score (descending)
    scoredParagraphs.sort((a, b) => b.score - a.score);
    
    // Get top paragraphs
    const topParagraphs = scoredParagraphs.slice(0, 3).filter(p => p.score > 0);
    
    // If no relevant paragraphs found, create a placeholder
    if (topParagraphs.length === 0) {
      return `   - [${section} information not found in the original text]`;
    }
    
    // Format paragraphs as bullet points
    return topParagraphs.map(p => {
      const paragraph = p.paragraph.trim();
      
      // If paragraph already starts with a bullet point or dash, use it as is
      if (paragraph.startsWith('-') || paragraph.startsWith('•') || paragraph.startsWith('*')) {
        return `   ${paragraph}`;
      }
      
      // Otherwise, add a dash
      return `   - ${paragraph}`;
    }).join('\n');
  }
}