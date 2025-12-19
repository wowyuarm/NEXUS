/**
 * Markdown Preprocessor Utility
 * 
 * Handles preprocessing of Markdown content to fix compatibility issues
 * with Chinese full-width punctuation marks in bold syntax.
 * 
 * Problem: When AI outputs **"content"** or **「content」**, the CommonMark parser
 * cannot recognize the bold syntax boundaries due to Unicode properties of
 * full-width punctuation marks (" " or 「 」), causing the syntax to display as raw text.
 * 
 * Solution: Swap the position of ** and full-width quotes to make them compatible
 * with Markdown parsers.
 */

/**
 * Preprocesses Markdown content to fix bold syntax with Chinese full-width punctuation.
 * 
 * Transformations:
 * - **"content"** → "**content**"
 * - **「content」** → 「**content**」
 * 
 * Features:
 * - Non-greedy matching to handle multiple bold blocks in one line
 * - Stream-aware: handles incomplete strings gracefully
 * - Preserves all other Markdown syntax
 * 
 * @param content - Raw Markdown content string
 * @returns Preprocessed Markdown content
 */
export function preprocessMarkdownBold(content: string): string {
  if (!content) return content;

  // Pattern explanation:
  // \*\* - Match opening **
  // ([""「]) - Capture group 1: opening full-width quote (double or corner bracket)
  // (.*?) - Capture group 2: content (non-greedy)
  // ([""」]) - Capture group 3: closing full-width quote (must match opening type)
  // \*\* - Match closing **
  //
  // The pattern uses non-greedy matching (.*?) to prevent matching across multiple bold blocks
  
  // Handle double quotes: **"content"** → "**content**"
  let processed = content.replace(
    /\*\*(["""])(.*?)(["""])\*\*/g,
    (match, openQuote, content, closeQuote) => {
      // Verify quotes are properly paired
      const isValidPair = 
        (openQuote === '"' && closeQuote === '"') ||
        (openQuote === '"' && closeQuote === '"') ||
        (openQuote === '"' && closeQuote === '"');
      
      if (!isValidPair) {
        return match; // Return original if quotes don't match
      }
      
      return `${openQuote}**${content}**${closeQuote}`;
    }
  );

  // Handle corner brackets: **「content」** → 「**content**」
  processed = processed.replace(
    /\*\*([「『])(.*?)([」』])\*\*/g,
    (match, openQuote, content, closeQuote) => {
      // Verify brackets are properly paired
      const isValidPair = 
        (openQuote === '「' && closeQuote === '」') ||
        (openQuote === '『' && closeQuote === '』');
      
      if (!isValidPair) {
        return match; // Return original if brackets don't match
      }
      
      return `${openQuote}**${content}**${closeQuote}`;
    }
  );

  return processed;
}

/**
 * Stream-aware version of preprocessMarkdownBold.
 * 
 * When processing streaming content, incomplete patterns at the end of the string
 * are preserved to avoid breaking partial syntax during streaming.
 * 
 * @param content - Raw Markdown content string (possibly incomplete)
 * @param isStreaming - Whether the content is currently being streamed
 * @returns Preprocessed Markdown content
 */
export function preprocessMarkdownBoldStreaming(
  content: string,
  isStreaming: boolean
): string {
  if (!content) return content;
  
  // If not streaming, use standard preprocessing
  if (!isStreaming) {
    return preprocessMarkdownBold(content);
  }

  // For streaming content, we need to be careful about incomplete patterns at the end
  // Check if the content ends with a potentially incomplete bold pattern
  const incompletePatterns = [
    /\*\*[""「『].*$/,  // Starts with ** and opening quote but no closing
    /\*\*$/,            // Just ** at the end
    /\*$/,              // Just * at the end
  ];

  const hasIncompletePattern = incompletePatterns.some(pattern => pattern.test(content));

  if (hasIncompletePattern) {
    // Find the last complete sentence/line and only process that part
    // Keep the potentially incomplete part unchanged
    const lastCompleteIndex = Math.max(
      content.lastIndexOf('\n'),
      content.lastIndexOf('。'),
      content.lastIndexOf('！'),
      content.lastIndexOf('？'),
      content.lastIndexOf('.'),
      content.lastIndexOf('!'),
      content.lastIndexOf('?')
    );

    if (lastCompleteIndex > 0) {
      const completePart = content.slice(0, lastCompleteIndex + 1);
      const incompletePart = content.slice(lastCompleteIndex + 1);
      
      return preprocessMarkdownBold(completePart) + incompletePart;
    }
    
    // If no complete sentence found, return original to avoid breaking streaming
    return content;
  }

  // No incomplete pattern, safe to process everything
  return preprocessMarkdownBold(content);
}
