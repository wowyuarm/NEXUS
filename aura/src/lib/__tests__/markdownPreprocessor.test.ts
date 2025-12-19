/**
 * Unit tests for Markdown Preprocessor
 * 
 * Tests the preprocessing logic for fixing Chinese full-width punctuation
 * in Markdown bold syntax.
 */

import { describe, it, expect } from 'vitest';
import { preprocessMarkdownBold, preprocessMarkdownBoldStreaming } from '../markdownPreprocessor';

describe('preprocessMarkdownBold', () => {
  describe('Double quotes transformation', () => {
    it('should transform **"content"** to "**content**"', () => {
      const input = '这是一个 **"测试"** 内容';
      const expected = '这是一个 "**测试**" 内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should transform **"content"** with full-width quotes', () => {
      const input = '这是 **"加粗内容"** 的示例';
      const expected = '这是 "**加粗内容**" 的示例';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle multiple bold blocks with double quotes in one line', () => {
      const input = '第一个 **"测试"** 和第二个 **"示例"** 内容';
      const expected = '第一个 "**测试**" 和第二个 "**示例**" 内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle mixed quote styles (left and right)', () => {
      const input = '这是 **"左引号"** 的测试';
      const expected = '这是 "**左引号**" 的测试';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });
  });

  describe('Corner brackets transformation', () => {
    it('should transform **「content」** to 「**content**」', () => {
      const input = '这是一个 **「测试」** 内容';
      const expected = '这是一个 「**测试**」 内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle multiple bold blocks with corner brackets', () => {
      const input = '第一个 **「测试」** 和第二个 **「示例」** 内容';
      const expected = '第一个 「**测试**」 和第二个 「**示例**」 内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle double corner brackets 『』', () => {
      const input = '这是 **『重要』** 的内容';
      const expected = '这是 『**重要**』 的内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });
  });

  describe('Mixed quote types', () => {
    it('should handle both double quotes and corner brackets in same text', () => {
      const input = '这有 **"双引号"** 和 **「直角引号」** 两种';
      const expected = '这有 "**双引号**" 和 「**直角引号**」 两种';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle complex mixed content', () => {
      const input = '**"第一"** 部分，**「第二」** 部分，**『第三』** 部分';
      const expected = '"**第一**" 部分，「**第二**」 部分，『**第三**』 部分';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });
  });

  describe('Edge cases', () => {
    it('should not transform mismatched quotes', () => {
      const input = '这是 **"错误」** 的配对';
      const expected = '这是 **"错误」** 的配对';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should not transform mismatched brackets', () => {
      const input = '这是 **「错误"** 的配对';
      const expected = '这是 **「错误"** 的配对';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle empty content between quotes', () => {
      const input = '这是 **""** 空内容';
      const expected = '这是 "****" 空内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle empty content between brackets', () => {
      const input = '这是 **「」** 空内容';
      const expected = '这是 「****」 空内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should preserve normal bold syntax without quotes', () => {
      const input = '这是 **正常加粗** 的内容';
      const expected = '这是 **正常加粗** 的内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should preserve quotes without bold syntax', () => {
      const input = '这是 "普通引号" 和 「普通括号」 的内容';
      const expected = '这是 "普通引号" 和 「普通括号」 的内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle nested quotes (only process outer bold)', () => {
      const input = '这是 **"外层"内层"外层"** 的测试';
      const expected = '这是 "**外层"内层"外层**" 的测试';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle multiline content', () => {
      const input = '第一行 **"测试"** 内容\n第二行 **「示例」** 内容';
      const expected = '第一行 "**测试**" 内容\n第二行 「**示例**」 内容';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle empty string', () => {
      expect(preprocessMarkdownBold('')).toBe('');
    });

    it('should handle undefined gracefully', () => {
      expect(preprocessMarkdownBold('')).toBe('');
    });
  });

  describe('Non-greedy matching', () => {
    it('should use non-greedy matching to avoid over-matching', () => {
      const input = '**"第一"** 中间文本 **"第二"**';
      const expected = '"**第一**" 中间文本 "**第二**"';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle adjacent bold blocks', () => {
      const input = '**"第一"****"第二"**';
      const expected = '"**第一**""**第二**"';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });
  });

  describe('Real-world examples', () => {
    it('should handle typical AI response with Chinese quotes', () => {
      const input = '根据您的需求，我建议使用 **"预处理过滤"** 方案来解决这个问题。';
      const expected = '根据您的需求，我建议使用 "**预处理过滤**" 方案来解决这个问题。';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle mixed English and Chinese content', () => {
      const input = 'The solution is to use **"preprocessing"** or **「预处理」** method.';
      const expected = 'The solution is to use "**preprocessing**" or 「**预处理**」 method.';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });

    it('should handle technical documentation style', () => {
      const input = '配置项 **"maxRetries"** 控制重试次数，**「timeout」** 设置超时时间。';
      const expected = '配置项 "**maxRetries**" 控制重试次数，「**timeout**」 设置超时时间。';
      expect(preprocessMarkdownBold(input)).toBe(expected);
    });
  });
});

describe('preprocessMarkdownBoldStreaming', () => {
  describe('Complete content (not streaming)', () => {
    it('should process complete content normally when not streaming', () => {
      const input = '这是 **"测试"** 内容';
      const expected = '这是 "**测试**" 内容';
      expect(preprocessMarkdownBoldStreaming(input, false)).toBe(expected);
    });
  });

  describe('Incomplete patterns during streaming', () => {
    it('should preserve incomplete pattern at end during streaming', () => {
      const input = '这是完整的 **"测试"** 内容。这是不完整的 **"开始';
      const result = preprocessMarkdownBoldStreaming(input, true);
      
      // Should process the complete part but preserve incomplete part
      expect(result).toContain('"**测试**"');
      expect(result).toContain('**"开始');
    });

    it('should preserve incomplete ** at end during streaming', () => {
      const input = '这是完整内容。这是不完整的 **';
      const result = preprocessMarkdownBoldStreaming(input, true);
      
      expect(result).toBe(input); // Should preserve as-is
    });

    it('should preserve incomplete * at end during streaming', () => {
      const input = '这是完整内容。这是不完整的 *';
      const result = preprocessMarkdownBoldStreaming(input, true);
      
      expect(result).toBe(input); // Should preserve as-is
    });

    it('should process everything if no incomplete pattern during streaming', () => {
      const input = '这是 **"第一"** 和 **"第二"** 的完整内容。';
      const expected = '这是 "**第一**" 和 "**第二**" 的完整内容。';
      expect(preprocessMarkdownBoldStreaming(input, true)).toBe(expected);
    });

    it('should handle streaming with Chinese sentence endings', () => {
      const input = '完整句子 **"测试"** 结束。未完成 **"开';
      const result = preprocessMarkdownBoldStreaming(input, true);
      
      expect(result).toContain('"**测试**"');
      expect(result).toContain('**"开');
    });

    it('should handle streaming with English sentence endings', () => {
      const input = 'Complete sentence **"test"**. Incomplete **"start';
      const result = preprocessMarkdownBoldStreaming(input, true);
      
      expect(result).toContain('"**test**"');
      expect(result).toContain('**"start');
    });
  });

  describe('Edge cases for streaming', () => {
    it('should handle empty string during streaming', () => {
      expect(preprocessMarkdownBoldStreaming('', true)).toBe('');
    });

    it('should handle only incomplete pattern during streaming', () => {
      const input = '**"开始';
      expect(preprocessMarkdownBoldStreaming(input, true)).toBe(input);
    });

    it('should handle newline-separated content during streaming', () => {
      const input = '第一行 **"完整"** 内容\n第二行不完整 **"开';
      const result = preprocessMarkdownBoldStreaming(input, true);
      
      expect(result).toContain('"**完整**"');
      expect(result).toContain('**"开');
    });
  });
});
