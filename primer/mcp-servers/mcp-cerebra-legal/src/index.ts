#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import {
  CallToolRequestSchema,
  ListToolsRequestSchema,
  Tool,
} from '@modelcontextprotocol/sdk/types.js';
import chalk from 'chalk';

/**
 * Tool definitions
 */
const LEGAL_THINK_TOOL: Tool = {
  name: "legal_think",
  description: `A powerful tool for structured legal reasoning that helps analyze complex legal issues.
This tool provides domain-specific guidance and templates for different legal areas including ANSC contestations, consumer protection, and contract analysis.

When to use this tool:
- Breaking down complex legal problems into structured steps
- Analyzing legal requirements and compliance
- Verifying that all elements of a legal test are addressed
- Building comprehensive legal arguments with proper citations

Key features:
- Automatic detection of legal domains
- Domain-specific guidance and templates
- Support for legal citations and references
- Revision capabilities for refining legal arguments
- Thought quality feedback`,
  inputSchema: {
    type: "object",
    properties: {
      thought: {
        type: "string",
        description: "The main legal reasoning content"
      },
      category: {
        type: "string",
        enum: [
          "analysis", 
          "planning", 
          "verification", 
          "legal_reasoning", 
          "ansc_contestation",
          "consumer_protection",
          "contract_analysis"
        ],
        description: "Category of legal reasoning (optional, will be auto-detected if not provided)"
      },
      references: {
        type: "array",
        items: {
          type: "string"
        },
        description: "References to laws, regulations, precedents, or previous thoughts (optional)"
      },
      isRevision: {
        type: "boolean",
        description: "Whether this thought revises a previous legal reasoning (optional)"
      },
      revisesThoughtNumber: {
        type: "integer",
        description: "The thought number being revised (if isRevision is true)"
      },
      requestGuidance: {
        type: "boolean",
        description: "Set to true to receive domain-specific legal guidance"
      },
      requestTemplate: {
        type: "boolean",
        description: "Set to true to receive a template for this type of legal reasoning"
      },
      thoughtNumber: {
        type: "integer",
        description: "Current thought number",
        minimum: 1
      },
      totalThoughts: {
        type: "integer",
        description: "Estimated total thoughts needed",
        minimum: 1
      },
      nextThoughtNeeded: {
        type: "boolean",
        description: "Whether another thought step is needed"
      }
    },
    required: ["thought", "thoughtNumber", "totalThoughts", "nextThoughtNeeded"]
  }
};

const LEGAL_ASK_FOLLOWUP_QUESTION_TOOL: Tool = {
  name: "legal_ask_followup_question",
  description: `A specialized tool for asking follow-up questions in legal contexts.
This tool helps gather additional information needed for legal analysis by formulating precise questions with domain-specific options.

When to use this tool:
- When you need additional information to complete a legal analysis
- When clarification is needed on specific legal points
- When gathering evidence or documentation for a legal case
- When exploring alternative legal interpretations

Key features:
- Automatic detection of legal domains
- Domain-specific question suggestions
- Legal terminology formatting
- Structured options for efficient information gathering`,
  inputSchema: {
    type: "object",
    properties: {
      question: {
        type: "string",
        description: "The legal question to ask the user"
      },
      options: {
        type: "array",
        items: {
          type: "string"
        },
        description: "An array of 2-5 options for the user to choose from (optional)"
      },
      context: {
        type: "string",
        description: "Additional context about the legal issue (optional)"
      }
    },
    required: ["question"]
  }
};

const LEGAL_ATTEMPT_COMPLETION_TOOL: Tool = {
  name: "legal_attempt_completion",
  description: `A specialized tool for presenting legal analysis results and conclusions.
This tool formats legal conclusions with proper structure, extracts and formats citations, and provides a professional legal document format.

When to use this tool:
- When presenting the final results of a legal analysis
- When summarizing legal findings and recommendations
- When providing a structured legal opinion
- When concluding a legal reasoning process

Key features:
- Automatic detection of legal domains
- Proper legal document formatting
- Citation extraction and formatting
- Structured sections for clear communication`,
  inputSchema: {
    type: "object",
    properties: {
      result: {
        type: "string",
        description: "The legal analysis result or conclusion"
      },
      command: {
        type: "string",
        description: "A CLI command to execute (optional)"
      },
      context: {
        type: "string",
        description: "Additional context about the legal issue (optional)"
      }
    },
    required: ["result"]
  }
};

/**
 * Legal domains and their patterns
 */
const legalDomainPatterns: Record<string, RegExp[]> = {
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
 * Domain-specific guidance
 */
const domainGuidance: Record<string, string> = {
  ansc_contestation: `Guidance for ANSC contestation analysis:
1. Identify the specific procurement law provisions that apply
2. Check if all required information about the contestation is collected
3. Verify compliance with ANSC precedents and legal standards
4. Ensure all elements of the legal test are addressed`,
  consumer_protection: `Guidance for consumer protection analysis:
1. Identify applicable consumer protection laws and regulations
2. Analyze burden of proof requirements for each party
3. Verify compliance with warranty and product safety requirements
4. Ensure all consumer rights have been properly considered`,
  contract_analysis: `Guidance for contract analysis:
1. Identify the applicable Civil Code provisions
2. Analyze the key contractual clauses and their enforceability
3. Check for potential legal issues or ambiguities
4. Ensure all contractual requirements are properly addressed`,
  legal_reasoning: `Guidance for general legal reasoning:
1. Identify the applicable legal framework
2. Analyze the facts in light of relevant legal provisions
3. Consider precedents and established legal principles
4. Evaluate arguments from all parties involved`
};

/**
 * Domain-specific templates
 */
const domainTemplates: Record<string, string> = {
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

/**
 * Domain-specific question templates
 */
const domainQuestionTemplates: Record<string, string[]> = {
  ansc_contestation: [
    "What specific provisions of Law 131/2015 are relevant to this contestation?",
    "Are there any ANSC precedent decisions that address similar technical specifications?",
    "What documentation has the contracting authority provided to justify the specifications?",
    "Has the claimant provided evidence that the specifications are unnecessarily restrictive?"
  ],
  consumer_protection: [
    "What are the exact terms of the warranty as stated in the documentation?",
    "Has the retailer provided any evidence to support their claim of improper use?",
    "When exactly did the product failure occur relative to the purchase date?",
    "Are there any similar cases or precedents regarding this type of product failure?"
  ],
  contract_analysis: [
    "What are the key obligations of each party under this contract?",
    "Are there any ambiguous terms that require clarification?",
    "What termination provisions exist in the contract?",
    "Are there any potentially unenforceable clauses in this agreement?"
  ],
  legal_reasoning: [
    "What are the key facts that need to be established for this analysis?",
    "Which legal provisions are most relevant to this situation?",
    "Are there any precedents that should be considered?",
    "What counterarguments should be anticipated?"
  ]
};

/**
 * Domain-specific completion templates
 */
const domainCompletionTemplates: Record<string, string> = {
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
 * Thought history
 */
const thoughtHistory: any[] = [];

/**
 * Detect domain based on text content
 */
function detectDomain(text: string): string {
  // Check each domain's patterns
  for (const [domain, patterns] of Object.entries(legalDomainPatterns)) {
    if (patterns.some(pattern => pattern.test(text))) {
      return domain;
    }
  }
  return "legal_reasoning"; // Default domain
}

/**
 * Format a thought with borders and colors
 */
function formatThought(
  thought: string,
  domain: string,
  thoughtNumber: number,
  totalThoughts: number,
  isRevision?: boolean,
  revisesThoughtNumber?: number
): string {
  let prefix = '';
  let context = '';
  let color = chalk.blue;
  
  // Determine color and prefix based on domain
  switch (domain) {
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

/**
 * Process a legal think request
 */
function processLegalThink(input: unknown): { content: Array<{ type: string; text: string }>; isError?: boolean } {
  try {
    const data = input as Record<string, unknown>;
    
    // Validate input
    if (!data.thought || typeof data.thought !== 'string') {
      throw new Error('Invalid thought: must be a string');
    }
    if (!data.thoughtNumber || typeof data.thoughtNumber !== 'number') {
      throw new Error('Invalid thoughtNumber: must be a number');
    }
    if (!data.totalThoughts || typeof data.totalThoughts !== 'number') {
      throw new Error('Invalid totalThoughts: must be a number');
    }
    if (typeof data.nextThoughtNeeded !== 'boolean') {
      throw new Error('Invalid nextThoughtNeeded: must be a boolean');
    }
    
    // Detect domain
    const domain = data.category as string || detectDomain(data.thought as string);
    
    // Add to thought history
    thoughtHistory.push({
      ...data,
      domain,
      timestamp: new Date()
    });
    
    // Determine if guidance or templates should be provided
    let guidance = undefined;
    let template = undefined;
    
    if (data.requestGuidance || data.thoughtNumber === 1) {
      guidance = domainGuidance[domain] || domainGuidance["legal_reasoning"];
    }
    
    if (data.requestTemplate || data.thoughtNumber === 1) {
      template = domainTemplates[domain] || domainTemplates["legal_reasoning"];
    }
    
    // Format the thought for logging
    const formattedThought = formatThought(
      data.thought as string,
      domain,
      data.thoughtNumber as number,
      data.totalThoughts as number,
      data.isRevision as boolean,
      data.revisesThoughtNumber as number
    );
    
    // Log the formatted thought
    console.error(formattedThought);
    
    // Prepare response
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          thoughtNumber: data.thoughtNumber,
          totalThoughts: data.totalThoughts,
          nextThoughtNeeded: data.nextThoughtNeeded,
          detectedDomain: domain,
          guidance,
          template,
          thoughtHistoryLength: thoughtHistory.length
        }, null, 2)
      }]
    };
  } catch (error) {
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
 * Process a legal ask followup question request
 */
function processLegalAskFollowupQuestion(input: unknown): { content: Array<{ type: string; text: string }>; isError?: boolean } {
  try {
    const data = input as Record<string, unknown>;
    
    // Validate input
    if (!data.question || typeof data.question !== 'string') {
      throw new Error('Invalid question: must be a string');
    }
    
    // Detect domain from question and context
    const textToAnalyze = data.context 
      ? `${data.question} ${data.context}`
      : data.question as string;
    const domain = detectDomain(textToAnalyze);
    
    // If no options provided, suggest domain-specific options
    let options = data.options as string[];
    if (!options || options.length === 0) {
      options = domainQuestionTemplates[domain] || domainQuestionTemplates["legal_reasoning"];
      options = options.slice(0, 4); // Return up to 4 options
    }
    
    // Format the question with legal terminology
    let question = data.question as string;
    
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
    
    // Prepare response
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          question,
          options,
          detectedDomain: domain
        }, null, 2)
      }]
    };
  } catch (error) {
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
 * Process a legal attempt completion request
 */
function processLegalAttemptCompletion(input: unknown): { content: Array<{ type: string; text: string }>; isError?: boolean } {
  try {
    const data = input as Record<string, unknown>;
    
    // Validate input
    if (!data.result || typeof data.result !== 'string') {
      throw new Error('Invalid result: must be a string');
    }
    
    // Detect domain from result and context
    const textToAnalyze = data.context 
      ? `${data.result} ${data.context}`
      : data.result as string;
    const domain = detectDomain(textToAnalyze);
    
    // Format the result with proper legal structure
    let result = data.result as string;
    
    // If result doesn't have a good structure, apply template
    if (!hasGoodStructure(result)) {
      result = applyTemplateStructure(result, domain);
    }
    
    // Prepare response
    return {
      content: [{
        type: "text",
        text: JSON.stringify({
          result,
          command: data.command,
          detectedDomain: domain,
          formattedCitations: []
        }, null, 2)
      }]
    };
  } catch (error) {
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
 * Check if the result already has a good structure
 */
function hasGoodStructure(result: string): boolean {
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
 * Apply a template structure to the result
 */
function applyTemplateStructure(result: string, domain: string): string {
  // Get domain-specific completion template
  const template = domainCompletionTemplates[domain] || domainCompletionTemplates["legal_reasoning"];
  
  // Add a title based on domain
  let formattedResult = '';
  
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
  
  // Add a brief introduction
  formattedResult += `${result}\n\n`;
  
  // Add template structure
  formattedResult += template.split('\n\n').slice(1).join('\n\n');
  
  return formattedResult;
}

// Create server
const server = new Server(
  {
    name: "mcp-cerebra-legal-server",
    version: "1.0.0",
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Set up error handling
server.onerror = (error) => {
  console.error('MCP Server error:', error);
};

process.on('SIGINT', async () => {
  console.error('Received SIGINT, shutting down...');
  await server.close();
  process.exit(0);
});

process.on('SIGTERM', async () => {
  console.error('Received SIGTERM, shutting down...');
  await server.close();
  process.exit(0);
});

process.on('uncaughtException', (error) => {
  console.error('Uncaught exception:', error);
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  console.error('Unhandled rejection:', reason);
  process.exit(1);
});

// Set up request handlers
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    LEGAL_THINK_TOOL,
    LEGAL_ASK_FOLLOWUP_QUESTION_TOOL,
    LEGAL_ATTEMPT_COMPLETION_TOOL
  ],
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  console.error(`Tool call request: ${request.params.name}`);
  
  if (request.params.name === "legal_think") {
    return processLegalThink(request.params.arguments);
  }
  
  if (request.params.name === "legal_ask_followup_question") {
    return processLegalAskFollowupQuestion(request.params.arguments);
  }
  
  if (request.params.name === "legal_attempt_completion") {
    return processLegalAttemptCompletion(request.params.arguments);
  }
  
  return {
    content: [{
      type: "text",
      text: `Unknown tool: ${request.params.name}`
    }],
    isError: true
  };
});

// Run the server
async function runServer() {
  try {
    const transport = new StdioServerTransport();
    await server.connect(transport);
    console.error('CerebraLegalServer running on stdio');
  } catch (error) {
    console.error('Failed to start server:', error);
    process.exit(1);
  }
}

runServer().catch((error) => {
  console.error('Fatal error running server:', error);
  process.exit(1);
});