/**
 * CitationFormatter class for formatting and extracting legal citations
 */
export class CitationFormatter {
  // Regular expressions for detecting different types of citations
  private citationPatterns: Record<string, RegExp> = {
    law: /(?:Law|Legea)\s+(?:No\.\s*)?(\d+(?:\/\d+)?)/i,
    article: /(?:Art(?:icle|icolul)?\.?\s+)(\d+(?:\(\d+\))?(?:\s*[a-z])?)/i,
    decision: /(?:Decision|Decizia|ANSC\s+Decision)\s+(?:No\.\s*)?#?(\d+(?:\/\d+)?)/i,
    caseNumber: /#(\d+)/i,
    directive: /(?:Directive|Directiva)\s+(?:No\.\s*)?(\d+(?:\/\d+)?\/[A-Z]+)/i,
    civilCode: /(?:Civil\s+Code|Codul\s+Civil)/i
  };

  /**
   * Formats a legal citation according to standards
   * @param citation - The citation text to format
   * @param domain - The legal domain for context
   * @returns Formatted citation
   */
  public formatLegalCitation(citation: string, domain: string): string {
    // Format based on domain and citation type
    if (domain === "ansc_contestation") {
      // Format ANSC-specific citations
      citation = this.formatAnscCitation(citation);
    } else if (domain === "consumer_protection") {
      // Format consumer protection citations
      citation = this.formatConsumerCitation(citation);
    } else if (domain === "contract_analysis") {
      // Format contract-related citations
      citation = this.formatContractCitation(citation);
    }
    
    return citation;
  }
  
  /**
   * Extracts potential citations from text
   * @param text - The text to analyze
   * @returns Array of extracted citations
   */
  public extractCitations(text: string): string[] {
    const citations: string[] = [];
    
    // Check for law citations
    const lawMatches = text.match(new RegExp(this.citationPatterns.law.source, 'gi'));
    if (lawMatches) {
      citations.push(...lawMatches);
    }
    
    // Check for article citations
    const articleMatches = text.match(new RegExp(this.citationPatterns.article.source, 'gi'));
    if (articleMatches) {
      citations.push(...articleMatches);
    }
    
    // Check for decision citations
    const decisionMatches = text.match(new RegExp(this.citationPatterns.decision.source, 'gi'));
    if (decisionMatches) {
      citations.push(...decisionMatches);
    }
    
    // Check for case number citations
    const caseMatches = text.match(new RegExp(this.citationPatterns.caseNumber.source, 'gi'));
    if (caseMatches) {
      citations.push(...caseMatches);
    }
    
    // Check for directive citations
    const directiveMatches = text.match(new RegExp(this.citationPatterns.directive.source, 'gi'));
    if (directiveMatches) {
      citations.push(...directiveMatches);
    }
    
    // Check for Civil Code citations
    const civilCodeMatches = text.match(new RegExp(this.citationPatterns.civilCode.source, 'gi'));
    if (civilCodeMatches) {
      citations.push(...civilCodeMatches);
    }
    
    // Remove duplicates and return
    return [...new Set(citations)];
  }
  
  /**
   * Formats ANSC-specific citations
   * @param citation - The citation to format
   * @returns Formatted citation
   */
  private formatAnscCitation(citation: string): string {
    // Format Law 131/2015 citations
    if (citation.match(/Law\s+131\/2015/i)) {
      citation = citation.replace(/Law\s+131\/2015/i, "Law No. 131/2015 on Public Procurement");
    }
    
    // Format ANSC decision citations
    const decisionMatch = citation.match(/ANSC\s+Decision\s+#?(\d+)(?:\/(\d+))?/i);
    if (decisionMatch) {
      const decisionNumber = decisionMatch[1];
      const year = decisionMatch[2] || new Date().getFullYear();
      citation = citation.replace(/ANSC\s+Decision\s+#?(\d+)(?:\/(\d+))?/i, `ANSC Decision No. ${decisionNumber}/${year}`);
    }
    
    // Format EU directive citations
    const directiveMatch = citation.match(/Directive\s+(\d+)\/(\d+)\/([A-Z]+)/i);
    if (directiveMatch) {
      const [_, number, year, org] = directiveMatch;
      citation = citation.replace(/Directive\s+(\d+)\/(\d+)\/([A-Z]+)/i, `${org} Directive ${number}/${year}`);
    }
    
    return citation;
  }
  
  /**
   * Formats consumer protection citations
   * @param citation - The citation to format
   * @returns Formatted citation
   */
  private formatConsumerCitation(citation: string): string {
    // Format Consumer Protection Law citations
    if (citation.match(/Consumer\s+Protection\s+Law/i)) {
      citation = citation.replace(/Consumer\s+Protection\s+Law/i, "Consumer Protection Law");
    }
    
    // Format case citations
    const caseMatch = citation.match(/Case\s+#?(\d+)(?:\/(\d+))?/i);
    if (caseMatch) {
      const caseNumber = caseMatch[1];
      const year = caseMatch[2] || new Date().getFullYear();
      citation = citation.replace(/Case\s+#?(\d+)(?:\/(\d+))?/i, `Case No. ${caseNumber}/${year}`);
    }
    
    return citation;
  }
  
  /**
   * Formats contract-related citations
   * @param citation - The citation to format
   * @returns Formatted citation
   */
  private formatContractCitation(citation: string): string {
    // Format Civil Code citations
    if (citation.match(/Civil\s+Code/i)) {
      citation = citation.replace(/Civil\s+Code/i, "Civil Code");
    }
    
    // Format article citations
    const articleMatch = citation.match(/Art(?:icle)?\.?\s+(\d+)(?:\((\d+)\))?(?:\s+([a-z]))?/i);
    if (articleMatch) {
      const [_, article, paragraph, point] = articleMatch;
      let formattedCitation = `Article ${article}`;
      
      if (paragraph) {
        formattedCitation += `, paragraph (${paragraph})`;
      }
      
      if (point) {
        formattedCitation += `, point ${point})`;
      }
      
      citation = citation.replace(/Art(?:icle)?\.?\s+(\d+)(?:\((\d+)\))?(?:\s+([a-z]))?/i, formattedCitation);
    }
    
    return citation;
  }
  
  /**
   * Adds a new citation pattern
   * @param name - The pattern name
   * @param pattern - The RegExp pattern
   */
  public addCitationPattern(name: string, pattern: RegExp): void {
    this.citationPatterns[name] = pattern;
  }
}