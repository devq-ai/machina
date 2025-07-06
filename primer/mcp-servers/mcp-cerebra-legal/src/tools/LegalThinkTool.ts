import { v4 as uuidv4 } from 'uuid';
import { DomainDetector } from '../shared/DomainDetector.js';
import { LegalKnowledgeBase } from '../shared/LegalKnowledgeBase.js';
import { CitationFormatter } from '../shared/CitationFormatter.js';
import { LegalThinkInput, ThoughtData } from '../shared/types.js';
import { logger } from '../utils/logger.js';

/**
 * LegalThinkTool class for implementing the legal_think tool
 */
export class LegalThinkTool {
  private thoughtHistory: ThoughtData[] = [];
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
    
    logger.info('LegalThinkTool initialized');
  }
  
  /**
   * Process a thought request
   * @param input - The input data
   * @returns Tool response
   */
  public processThought(input: unknown): { content: Array<{ type: string; text: string }>; isError?: boolean } {
    try {
      logger.debug('Processing thought request', input);
      
      // Validate input
      const validatedInput = this.validateThoughtData(input as LegalThinkInput);
      
      // Create thought data with ID and timestamp
      const thoughtData: ThoughtData = {
        ...validatedInput,
        id: uuidv4(),
        timestamp: new Date(),
        detectedDomain: validatedInput.category || this.domainDetector.detectDomain(validatedInput.thought)
      };
      
      // Add to thought history
      this.thoughtHistory.push(thoughtData);
      
      // Determine if guidance or templates should be provided
      let guidance = undefined;
      let template = undefined;
      let feedback = undefined;
      
      if (validatedInput.requestGuidance || this.shouldProvideGuidance(validatedInput)) {
        guidance = this.legalKnowledgeBase.getGuidance(thoughtData.detectedDomain);
      }
      
      if (validatedInput.requestTemplate || this.shouldProvideTemplate(validatedInput)) {
        template = this.legalKnowledgeBase.getTemplate(thoughtData.detectedDomain);
      }
      
      // Format citations in the thought
      if (validatedInput.references && validatedInput.references.length > 0) {
        validatedInput.references = validatedInput.references.map(reference => 
          this.citationFormatter.formatLegalCitation(reference, thoughtData.detectedDomain)
        );
      }
      
      // Format the thought for logging
      const formattedThought = logger.formatThought(
        validatedInput.thought,
        thoughtData.detectedDomain,
        validatedInput.thoughtNumber,
        validatedInput.totalThoughts,
        validatedInput.isRevision,
        validatedInput.revisesThoughtNumber
      );
      
      // Log the formatted thought
      console.error(formattedThought);
      
      // Analyze thought quality
      feedback = this.analyzeThoughtQuality(validatedInput.thought, thoughtData.detectedDomain);
      
      // Prepare response
      const response = {
        thoughtNumber: validatedInput.thoughtNumber,
        totalThoughts: validatedInput.totalThoughts,
        nextThoughtNeeded: validatedInput.nextThoughtNeeded,
        detectedDomain: thoughtData.detectedDomain,
        guidance,
        template,
        feedback,
        thoughtHistoryLength: this.thoughtHistory.length
      };
      
      logger.debug('Thought processed successfully', response);
      
      return {
        content: [{
          type: "text",
          text: JSON.stringify(response, null, 2)
        }]
      };
    } catch (error) {
      // Log and handle errors
      logger.error('Error processing thought', error as Error);
      
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
   * Validate thought data
   * @param input - The input to validate
   * @returns Validated input
   * @throws Error if validation fails
   */
  private validateThoughtData(input: LegalThinkInput): LegalThinkInput {
    if (!input) {
      throw new Error('Input is required');
    }
    
    if (!input.thought || typeof input.thought !== 'string') {
      throw new Error('Thought must be a non-empty string');
    }
    
    if (!input.thoughtNumber || typeof input.thoughtNumber !== 'number' || input.thoughtNumber < 1) {
      throw new Error('Thought number must be a positive number');
    }
    
    if (!input.totalThoughts || typeof input.totalThoughts !== 'number' || input.totalThoughts < 1) {
      throw new Error('Total thoughts must be a positive number');
    }
    
    if (typeof input.nextThoughtNeeded !== 'boolean') {
      throw new Error('Next thought needed must be a boolean');
    }
    
    // If this is a revision, ensure revisesThoughtNumber is provided
    if (input.isRevision && (!input.revisesThoughtNumber || input.revisesThoughtNumber < 1)) {
      throw new Error('Revises thought number must be a positive number when isRevision is true');
    }
    
    return {
      thought: input.thought,
      category: input.category,
      references: input.references || [],
      isRevision: input.isRevision || false,
      revisesThoughtNumber: input.revisesThoughtNumber,
      requestGuidance: input.requestGuidance || false,
      requestTemplate: input.requestTemplate || false,
      thoughtNumber: input.thoughtNumber,
      totalThoughts: input.totalThoughts,
      nextThoughtNeeded: input.nextThoughtNeeded
    };
  }
  
  /**
   * Determine if guidance should be provided
   * @param input - The thought input
   * @returns Whether guidance should be provided
   */
  private shouldProvideGuidance(input: LegalThinkInput): boolean {
    // Provide guidance for the first thought
    if (input.thoughtNumber === 1) {
      return true;
    }
    
    // Provide guidance if the thought is short (likely needs help)
    if (input.thought.length < 100) {
      return true;
    }
    
    return false;
  }
  
  /**
   * Determine if a template should be provided
   * @param input - The thought input
   * @returns Whether a template should be provided
   */
  private shouldProvideTemplate(input: LegalThinkInput): boolean {
    // Provide template for the first thought
    if (input.thoughtNumber === 1) {
      return true;
    }
    
    // Provide template if the thought is very short (likely needs structure)
    if (input.thought.length < 50) {
      return true;
    }
    
    return false;
  }
  
  /**
   * Analyze thought quality and provide feedback
   * @param thought - The thought content
   * @param domain - The detected domain
   * @returns Feedback or undefined if no issues found
   */
  private analyzeThoughtQuality(thought: string, domain: string): string | undefined {
    const feedback: string[] = [];
    
    // Check for missing elements based on domain
    if (domain === "ansc_contestation") {
      if (!thought.includes("Law 131/2015") && !thought.includes("procurement law")) {
        feedback.push("Consider citing specific procurement law provisions");
      }
      if (!thought.includes("precedent") && !thought.includes("decision")) {
        feedback.push("Consider referencing relevant ANSC precedent decisions");
      }
      if (!thought.includes("technical specification") && !thought.includes("award criteria")) {
        feedback.push("Consider addressing the specific procurement elements being challenged");
      }
    } else if (domain === "consumer_protection") {
      if (!thought.includes("warranty") && !thought.includes("guarantee")) {
        feedback.push("Consider addressing warranty or guarantee terms");
      }
      if (!thought.includes("burden of proof")) {
        feedback.push("Consider addressing burden of proof requirements");
      }
      if (!thought.includes("Consumer Protection Law")) {
        feedback.push("Consider citing specific consumer protection legislation");
      }
    } else if (domain === "contract_analysis") {
      if (!thought.includes("clause") && !thought.includes("provision")) {
        feedback.push("Consider addressing specific contractual clauses or provisions");
      }
      if (!thought.includes("Civil Code")) {
        feedback.push("Consider referencing relevant Civil Code provisions");
      }
      if (!thought.includes("obligation") && !thought.includes("liability")) {
        feedback.push("Consider addressing obligations or liabilities of the parties");
      }
    }
    
    // Check general quality issues
    if (thought.split("\n").length < 3) {
      feedback.push("Consider structuring your analysis into clear sections");
    }
    
    if (!thought.includes("1.") && !thought.includes("2.") && !thought.includes("•")) {
      feedback.push("Consider using numbered points or bullet points for clarity");
    }
    
    return feedback.length > 0 ? feedback.join("\n") : undefined;
  }
  
  /**
   * Get the thought history
   * @returns Array of thought data
   */
  public getThoughtHistory(): ThoughtData[] {
    return [...this.thoughtHistory];
  }
  
  /**
   * Clear the thought history
   */
  public clearThoughtHistory(): void {
    this.thoughtHistory = [];
    logger.info('Thought history cleared');
  }
}