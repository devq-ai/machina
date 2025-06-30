/**
 * DomainDetector class for identifying legal domains based on text content
 */
export class DomainDetector {
  private legalDomainPatterns: Record<string, RegExp[]> = {
    ansc_contestation: [
      /contestation/i,
      /ANSC/i,
      /procurement/i,
      /tender/i,
      /Law 131\/2015/i,
      /technical specification/i,
      /award criteria/i
    ],
    consumer_protection: [
      /consumer/i,
      /warranty/i,
      /product/i,
      /refund/i,
      /Consumer Protection Law/i,
      /misleading/i,
      /advertising/i,
      /product safety/i
    ],
    contract_analysis: [
      /contract/i,
      /clause/i,
      /agreement/i,
      /Civil Code/i,
      /obligation/i,
      /contractual/i,
      /parties/i,
      /enforcement/i
    ]
  };
  
  /**
   * Detects the legal domain based on text content
   * @param text - The text to analyze
   * @returns The detected domain or "legal_reasoning" as default
   */
  public detectDomain(text: string): string {
    // Check each domain's patterns
    for (const [domain, patterns] of Object.entries(this.legalDomainPatterns)) {
      if (patterns.some(pattern => pattern.test(text))) {
        return domain;
      }
    }
    return "legal_reasoning"; // Default domain
  }
  
  /**
   * Adds a new domain with its detection patterns
   * @param domain - The domain name
   * @param patterns - Array of RegExp patterns for detection
   */
  public addDomain(domain: string, patterns: RegExp[]): void {
    this.legalDomainPatterns[domain] = patterns;
  }
  
  /**
   * Gets all available domains
   * @returns Array of domain names
   */
  public getAvailableDomains(): string[] {
    return Object.keys(this.legalDomainPatterns).concat(["legal_reasoning"]);
  }
}