/**
 * LegalKnowledgeBase class for storing and retrieving legal domain knowledge
 */
export class LegalKnowledgeBase {
  private domainGuidance: Record<string, string> = {
    ansc_contestation: `Guidance for ANSC contestation analysis:
1. Identify the specific procurement law provisions that apply
2. Check if all required information about the contestation is collected
3. Verify compliance with ANSC precedents and legal standards
4. Ensure all elements of the legal test are addressed
5. Consider both the claimant's arguments and the contracting authority's position
6. Analyze the proportionality and justification of the challenged requirements
7. Reference relevant ANSC decisions that establish precedent`,

    consumer_protection: `Guidance for consumer protection analysis:
1. Identify applicable consumer protection laws and regulations
2. Analyze burden of proof requirements for each party
3. Verify compliance with warranty and product safety requirements
4. Ensure all consumer rights have been properly considered
5. Examine the terms and conditions of any warranty or guarantee
6. Consider the timeline of events and any applicable limitation periods
7. Assess the adequacy of the retailer/manufacturer's response`,

    contract_analysis: `Guidance for contract analysis:
1. Identify the applicable Civil Code provisions
2. Analyze the key contractual clauses and their enforceability
3. Check for potential legal issues or ambiguities
4. Ensure all contractual requirements are properly addressed
5. Consider the intent of the parties and the context of the agreement
6. Identify any potentially unfair or unenforceable terms
7. Assess the remedies available in case of breach`,

    legal_reasoning: `Guidance for general legal reasoning:
1. Identify the applicable legal framework
2. Analyze the facts in light of relevant legal provisions
3. Consider precedents and established legal principles
4. Evaluate arguments from all parties involved
5. Apply logical reasoning to reach a well-supported conclusion
6. Consider potential counterarguments and address them
7. Provide clear recommendations based on legal analysis`
  };
  
  private domainTemplates: Record<string, string> = {
    ansc_contestation: `Template for ANSC contestation analysis:

1. Key Claims:
   - [Describe claimant's main arguments]
   - [Cite specific legal provisions referenced]
   - [Describe contracting authority's position]

2. Legal Framework:
   - [List applicable laws and articles]
   - [Reference relevant ANSC decisions/precedents]
   - [Note any applicable EU directives or principles]

3. Analysis:
   - [Evaluate each claim against legal requirements]
   - [Assess evidence and documentation]
   - [Compare with similar ANSC decisions]

4. Conclusion:
   - [Provide assessment of likely outcome]
   - [Recommend response strategy]
   - [Identify any additional information needed]`,

    consumer_protection: `Template for consumer protection analysis:

1. Consumer Claim:
   - [Describe product/service issue]
   - [Note warranty terms and conditions]
   - [Describe retailer/manufacturer response]

2. Legal Framework:
   - [List applicable consumer protection laws]
   - [Identify burden of proof provisions]
   - [Reference relevant case precedents]

3. Analysis:
   - [Analyze warranty terms against legal requirements]
   - [Evaluate burden of proof allocation]
   - [Assess evidence provided by both parties]

4. Recommendation:
   - [Provide assessment of consumer's position]
   - [Recommend specific actions]
   - [Cite legal basis for recommendations]`,

    contract_analysis: `Template for contract analysis:

1. Contract Overview:
   - [Identify parties to the contract]
   - [Describe key terms and obligations]
   - [Note any unusual or potentially problematic clauses]

2. Legal Framework:
   - [List applicable Civil Code provisions]
   - [Reference relevant contract law principles]
   - [Note any industry-specific regulations]

3. Analysis:
   - [Evaluate enforceability of key provisions]
   - [Identify potential legal risks]
   - [Assess clarity and completeness of terms]

4. Recommendations:
   - [Suggest modifications or clarifications]
   - [Outline risk mitigation strategies]
   - [Provide guidance on implementation or enforcement]`,

    legal_reasoning: `Template for general legal analysis:

1. Issue Identification:
   - [Clearly state the legal question or issue]
   - [Identify key facts relevant to the analysis]
   - [Note any preliminary considerations]

2. Legal Framework:
   - [Identify applicable laws and regulations]
   - [Reference relevant precedents]
   - [Note legal principles that apply]

3. Analysis:
   - [Apply law to facts]
   - [Consider alternative interpretations]
   - [Evaluate strengths and weaknesses of arguments]

4. Conclusion:
   - [Provide reasoned legal opinion]
   - [Recommend course of action]
   - [Note any limitations or additional considerations]`
  };
  
  private domainQuestionTemplates: Record<string, string[]> = {
    ansc_contestation: [
      "What specific provisions of Law 131/2015 are relevant to this contestation?",
      "Are there any ANSC precedent decisions that address similar technical specifications?",
      "What documentation has the contracting authority provided to justify the specifications?",
      "Has the claimant provided evidence that the specifications are unnecessarily restrictive?",
      "What is the timeline for submitting a response to this contestation?",
      "Are there any procedural issues with how the contestation was filed?",
      "What remedies is the claimant seeking in this contestation?"
    ],
    
    consumer_protection: [
      "What are the exact terms of the warranty as stated in the documentation?",
      "Has the retailer provided any evidence to support their claim of improper use?",
      "When exactly did the product failure occur relative to the purchase date?",
      "Are there any similar cases or precedents regarding this type of product failure?",
      "What specific remedy is the consumer seeking (repair, replacement, refund)?",
      "Is there any documentation of previous complaints about the same product?",
      "Has an independent technical examination of the product been conducted?"
    ],
    
    contract_analysis: [
      "What are the key obligations of each party under this contract?",
      "Are there any ambiguous terms that require clarification?",
      "What termination provisions exist in the contract?",
      "Are there any potentially unenforceable clauses in this agreement?",
      "What dispute resolution mechanisms are specified in the contract?",
      "Are there any implied terms that should be considered?",
      "What are the consequences of breach specified in the contract?"
    ],
    
    legal_reasoning: [
      "What are the key facts that need to be established for this analysis?",
      "Which legal provisions are most relevant to this situation?",
      "Are there any precedents that should be considered?",
      "What counterarguments should be anticipated?",
      "What additional information would strengthen this legal position?",
      "What are the potential risks associated with this legal approach?",
      "What timeline considerations apply to this legal matter?"
    ]
  };
  
  private domainCompletionTemplates: Record<string, string> = {
    ansc_contestation: `Legal Analysis Summary:

Based on the analysis of contestation #[ID], regarding [brief description]:

1. Key Findings:
   - [Finding 1]
   - [Finding 2]
   - [Finding 3]

2. Legal Assessment:
   - [Assessment based on relevant laws and precedents]

3. Recommended Action:
   - [Specific action recommendation]
   - [Legal basis for recommendation]

4. Next Steps:
   - [Procedural next steps]
   - [Timeline considerations]
   - [Documentation requirements]`,

    consumer_protection: `Consumer Protection Analysis:

Regarding consumer complaint #[ID] about [product/service]:

1. Factual Assessment:
   - [Assessment of consumer's claim]
   - [Assessment of retailer's response]
   - [Evaluation of evidence provided]

2. Legal Position:
   - [Analysis under relevant consumer protection laws]
   - [Application of warranty provisions]
   - [Burden of proof considerations]

3. Recommended Action:
   - [Specific action recommendation]
   - [Legal basis for recommendation]

4. Next Steps:
   - [Communication strategy]
   - [Documentation requirements]
   - [Timeline for resolution]`,

    contract_analysis: `Contract Analysis Report:

Regarding [contract name/number] between [parties]:

1. Key Provisions Assessment:
   - [Assessment of critical clauses]
   - [Identification of legal risks]
   - [Evaluation of enforceability]

2. Legal Implications:
   - [Analysis under relevant contract law]
   - [Potential liability considerations]
   - [Rights and obligations assessment]

3. Recommended Action:
   - [Specific recommendations for modification/implementation]
   - [Risk mitigation strategies]
   - [Legal basis for recommendations]

4. Implementation Guidance:
   - [Practical steps for implementation]
   - [Documentation requirements]
   - [Monitoring considerations]`,

    legal_reasoning: `Legal Analysis Report:

Regarding [legal issue]:

1. Factual Summary:
   - [Key facts established]
   - [Relevant background information]
   - [Parties involved]

2. Legal Assessment:
   - [Application of relevant laws]
   - [Consideration of precedents]
   - [Evaluation of legal arguments]

3. Recommended Position:
   - [Legal conclusion]
   - [Justification for position]
   - [Consideration of alternatives]

4. Action Plan:
   - [Specific next steps]
   - [Timeline considerations]
   - [Resource requirements]`
  };
  
  /**
   * Gets guidance for a specific legal domain
   * @param domain - The legal domain
   * @returns Domain-specific guidance text
   */
  public getGuidance(domain: string): string {
    return this.domainGuidance[domain] || this.domainGuidance["legal_reasoning"];
  }
  
  /**
   * Gets a template for a specific legal domain
   * @param domain - The legal domain
   * @returns Domain-specific template text
   */
  public getTemplate(domain: string): string {
    return this.domainTemplates[domain] || this.domainTemplates["legal_reasoning"];
  }
  
  /**
   * Gets question templates for a specific legal domain
   * @param domain - The legal domain
   * @returns Array of domain-specific question templates
   */
  public getQuestionTemplates(domain: string): string[] {
    return this.domainQuestionTemplates[domain] || this.domainQuestionTemplates["legal_reasoning"];
  }
  
  /**
   * Gets a completion template for a specific legal domain
   * @param domain - The legal domain
   * @returns Domain-specific completion template
   */
  public getCompletionTemplate(domain: string): string {
    return this.domainCompletionTemplates[domain] || this.domainCompletionTemplates["legal_reasoning"];
  }
  
  /**
   * Adds new guidance for a specific domain
   * @param domain - The domain name
   * @param guidance - The guidance text
   */
  public addGuidance(domain: string, guidance: string): void {
    this.domainGuidance[domain] = guidance;
  }
  
  /**
   * Adds a new template for a specific domain
   * @param domain - The domain name
   * @param template - The template text
   */
  public addTemplate(domain: string, template: string): void {
    this.domainTemplates[domain] = template;
  }
  
  /**
   * Adds question templates for a specific domain
   * @param domain - The domain name
   * @param templates - Array of question templates
   */
  public addQuestionTemplates(domain: string, templates: string[]): void {
    this.domainQuestionTemplates[domain] = templates;
  }
  
  /**
   * Adds a completion template for a specific domain
   * @param domain - The domain name
   * @param template - The completion template text
   */
  public addCompletionTemplate(domain: string, template: string): void {
    this.domainCompletionTemplates[domain] = template;
  }
}