// src/components/ui/MarkdownRenderer.tsx
// Markdown renderer - follows grayscale moderate design philosophy, integrates all markdown-related components
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';
import { TAILWIND } from '@/lib/motion';

// ===== Internal component definitions =====

// Inline code component
interface InlineCodeProps {
  children: React.ReactNode;
  className?: string;
}

const InlineCode: React.FC<InlineCodeProps> = ({ children, className }) => {
  return (
    <code className={cn(
      'inline',
      'px-1.5 py-0.5',
      'text-base font-mono',
      'bg-muted/40 text-foreground',
      'rounded-sm',
      'break-words',
      className
    )}>
      {children}
    </code>
  );
};

// Code block component
interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  showLineNumbers?: boolean;
  className?: string;
}

const CodeBlock: React.FC<CodeBlockProps> = ({
  code,
  language,
  filename,
  showLineNumbers = false,
  className
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  const lines = code.split('\n');

  return (
    <div className={cn(
      'group relative rounded-xl overflow-hidden my-4',
      'bg-card/75 backdrop-blur-xl',
      'border border-border',
      'shadow-md shadow-black/10',
      // Interactive: 150ms micro-feedback for hover (consistent with input & tool cards)
      TAILWIND.micro,
      'hover:border-border-hover',
      className
    )}>
      {/* Header information bar */}
      {(filename || language) && (
        <div className="flex items-center justify-between px-3 py-2 border-b border-border/50 bg-muted/30">
          <div className="flex items-center space-x-3">
            {filename && (
              <span className="text-sm font-medium text-foreground">
                {filename}
              </span>
            )}
            {language && (
              <span className="text-xs text-secondary-foreground font-mono uppercase tracking-wider">
                {language}
              </span>
            )}
          </div>

          <button
            onClick={handleCopy}
            className={cn(
              'p-1.5 text-secondary-foreground/70 rounded',
              TAILWIND.micro,
              // Show on hover: hidden by default, appears on group-hover
              'opacity-0 group-hover:opacity-100',
              'hover:text-secondary-foreground hover:bg-muted/50',
              // Fully suppress any focus/active rings
              'outline-none focus:outline-none focus-visible:outline-none active:outline-none',
              'ring-0 focus:ring-0 focus-visible:ring-0 active:ring-0',
              'appearance-none'
            )}
            aria-label={copied ? "Copied" : "Copy code"}
          >
            <div className="relative h-3.5 w-3.5">
              <Copy
                size={14}
                className={cn(
                  'absolute',
                  TAILWIND.transition,
                  copied
                    ? 'opacity-0 scale-50 rotate-90'
                    : 'opacity-100 scale-100 rotate-0'
                )}
              />
              <Check
                size={14}
                className={cn(
                  'absolute',
                  TAILWIND.transition,
                  copied
                    ? 'opacity-100 scale-100 rotate-0'
                    : 'opacity-0 scale-50 -rotate-90'
                )}
              />
            </div>
          </button>
        </div>
      )}

      {/* Code content area */}
      <div className="relative">
        {/* Copy button (shown when no header info) */}
        {!filename && !language && (
          <button
            onClick={handleCopy}
            className={cn(
              'absolute top-3 right-3 z-10 p-1.5 rounded',
              'text-secondary-foreground/70 bg-card/50 backdrop-blur-sm',
              TAILWIND.micro,
              // Show on hover: hidden by default, appears on group-hover
              'opacity-0 group-hover:opacity-100',
              'hover:text-secondary-foreground hover:bg-muted/50',
              // Fully suppress any focus/active rings
              'outline-none focus:outline-none focus-visible:outline-none active:outline-none',
              'ring-0 focus:ring-0 focus-visible:ring-0 active:ring-0',
              'appearance-none'
            )}
            aria-label={copied ? "Copied" : "Copy code"}
          >
            <div className="relative h-3.5 w-3.5">
              <Copy
                size={14}
                className={cn(
                  'absolute',
                  TAILWIND.transition,
                  copied
                    ? 'opacity-0 scale-50 rotate-90'
                    : 'opacity-100 scale-100 rotate-0'
                )}
              />
              <Check
                size={14}
                className={cn(
                  'absolute',
                  TAILWIND.transition,
                  copied
                    ? 'opacity-100 scale-100 rotate-0'
                    : 'opacity-0 scale-50 -rotate-90'
                )}
              />
            </div>
          </button>
        )}

        <pre className={cn(
          'overflow-x-auto px-3 py-3',
          'text-sm leading-relaxed',
          'font-mono',
          !filename && !language && 'pr-10'
        )}>
          <code className="text-foreground">
            {showLineNumbers ? (
              <div className="table w-full">
                {lines.map((line, index) => (
                  <div key={index} className="table-row">
                    <span className="table-cell pr-4 text-secondary-foreground/50 text-right select-none w-8 min-w-8">
                      {index + 1}
                    </span>
                    <span className="table-cell">
                      {line || '\u00A0'}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              code
            )}
          </code>
        </pre>
      </div>
    </div>
  );
};

// Table component
interface TableProps {
  children: React.ReactNode;
  className?: string;
}

interface TableHeaderProps {
  children: React.ReactNode;
  className?: string;
}

interface TableBodyProps {
  children: React.ReactNode;
  className?: string;
}

interface TableRowProps {
  children: React.ReactNode;
  className?: string;
}

interface TableHeadProps {
  children: React.ReactNode;
  className?: string;
}

interface TableCellProps {
  children: React.ReactNode;
  className?: string;
}

// Main table container
const Table: React.FC<TableProps> = ({ children, className }) => (
  <div className="w-full overflow-x-auto my-4"> {/* Add horizontal scrolling and margin */}
    <table className={cn(
      'w-full border-collapse',
      'bg-card/30 backdrop-blur-sm',
      'border border-border/40',
      'rounded-lg overflow-hidden',
      'min-w-full', // Ensure minimum table width
      className
    )}>
      {children}
    </table>
  </div>
);

// Table header
const TableHeader: React.FC<TableHeaderProps> = ({ children, className }) => (
  <thead className={cn(
    'bg-card/50 backdrop-blur-sm',
    'border-b border-border/40',
    className
  )}>
    {children}
  </thead>
);

// Table body
const TableBody: React.FC<TableBodyProps> = ({ children, className }) => (
  <tbody className={cn(className)}>
    {children}
  </tbody>
);

// Table row
const TableRow: React.FC<TableRowProps> = ({ children, className }) => (
  <tr className={cn(
    'border-b border-border/20 last:border-b-0',
    'hover:bg-muted/20',
    TAILWIND.micro, // Hover effect: 150ms micro-feedback
    className
  )}>
    {children}
  </tr>
);

// Table header cell
const TableHead: React.FC<TableHeadProps> = ({ children, className }) => (
  <th className={cn(
    'px-3 py-2 text-left',
    'text-sm font-semibold text-foreground',
    'border-r border-border/20 last:border-r-0',
    'whitespace-nowrap', // Prevent title wrapping
    className
  )}>
    {children}
  </th>
);

// Table data cell
const TableCell: React.FC<TableCellProps> = ({ children, className }) => (
  <td className={cn(
    'px-3 py-2',
    'text-sm text-secondary-foreground',
    'border-r border-border/20 last:border-r-0',
    className
  )}>
    {children}
  </td>
);

interface MarkdownRendererProps {
  content: string;
  className?: string; // Add optional external styles
}

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ 
  content, 
  className 
}) => {
  return (
    <div className={cn("w-full prose max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Code block component
          code: ((props: { inline?: boolean; className?: string; children?: React.ReactNode; [key: string]: unknown }) => {
            const { inline, className, children } = props;
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : undefined;

            // Fix inline detection: if no line breaks and no language class, consider it inline code
            const codeContent = String(children);
            const isInlineCode = inline !== false && (!codeContent.includes('\n') && !language);

            if (isInlineCode) {
              return <InlineCode {...props}>{children}</InlineCode>;
            }

            return (
              <CodeBlock
                code={codeContent.replace(/\n$/, '')}
                language={language}
                showLineNumbers={false}
                {...props}
              />
            );
          }) as React.ComponentType,

          // Custom table component
          table: ({ children }) => (
            <Table>{children}</Table>
          ),

          thead: ({ children }) => <TableHeader>{children}</TableHeader>,
          tbody: ({ children }) => <TableBody>{children}</TableBody>,
          tr: ({ children }) => <TableRow>{children}</TableRow>,
          th: ({ children }) => <TableHead>{children}</TableHead>,
          td: ({ children }) => <TableCell>{children}</TableCell>,

          // Optimize other elements
          p: ({ children }) => (
            <p className="text-foreground leading-relaxed mb-4 last:mb-0">
              {children}
            </p>
          ),

          blockquote: ({ children }) => (
            <blockquote className="border-l-4 border-primary/30 bg-muted/30 pl-4 py-2 italic text-secondary-foreground my-4 rounded-r">
              {children}
            </blockquote>
          ),

          hr: () => (
            <hr className="border-border my-8" />
          ),

          // Title component - Add anchor support
          h1: ({ children, id }) => (
            <h1 
              id={id}
              className="text-3xl font-bold text-foreground mb-6 mt-8 first:mt-0 leading-tight scroll-mt-16"
            >
              {children}
            </h1>
          ),

          h2: ({ children, id }) => (
            <h2 
              id={id}
              className="text-2xl font-semibold text-foreground mb-4 mt-6 first:mt-0 leading-tight scroll-mt-16"
            >
              {children}
            </h2>
          ),

          h3: ({ children, id }) => (
            <h3 
              id={id}
              className="text-xl font-semibold text-foreground mb-3 mt-5 first:mt-0 leading-tight scroll-mt-16"
            >
              {children}
            </h3>
          ),

          h4: ({ children, id }) => (
            <h4 
              id={id}
              className="text-lg font-semibold text-foreground mb-2 mt-4 first:mt-0 leading-tight scroll-mt-16"
            >
              {children}
            </h4>
          ),

          h5: ({ children, id }) => (
            <h5 
              id={id}
              className="text-base font-semibold text-foreground mb-2 mt-4 first:mt-0 leading-tight scroll-mt-16"
            >
              {children}
            </h5>
          ),

          h6: ({ children, id }) => (
            <h6 
              id={id}
              className="text-sm font-semibold text-secondary-foreground mb-2 mt-3 first:mt-0 leading-tight uppercase tracking-wider scroll-mt-16"
            >
              {children}
            </h6>
          ),

// Unordered list component - simplified logic, rely on CSS for nesting
ul: ({ children }) => (
  <ul className="my-2 pl-2 md:pl-3 list-none">
    {children}
  </ul>
),

ol: ((props: { children?: React.ReactNode; start?: number; [key: string]: unknown }) => {
  const { children, start } = props;
  // Use state to track counter
  let counter = start || 1;

  return (
    <ol className="my-2 pl-2 md:pl-3 list-none">
      {React.Children.map(children, (child, index) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<{ [key: string]: unknown }>, {
            ...(child.props || {}),
            key: index,
            'data-list-number': counter++,
            'data-is-ordered': true
          });
        }
        return child;
      })}
    </ol>
  );
}) as React.ComponentType,

li: ((allProps: { children?: React.ReactNode; [key: string]: unknown }) => {
  const { children, ...props } = allProps;
  const isOrdered = props['data-is-ordered'];
  const listNumber = props['data-list-number'] as number;

  return (
    <li className="flex text-foreground leading-relaxed">
      <span className="flex-shrink-0 text-secondary-foreground/70 select-none mr-3 flex items-center h-7">
        {isOrdered ? (
          <span className="text-sm font-medium min-w-[1.2rem] text-right inline-block">
            {listNumber}.
          </span>
        ) : (
          // Dot is vertically centered in a fixed height container, matching the text line height
          <span className="w-1.5 h-1.5 bg-secondary-foreground/60 rounded-full" />
        )}
      </span>
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </li>
  );
}) as React.ComponentType,

          // Link component - Subtle interactive effect, following grayscale moderation philosophy
          a: ({ href, children }) => (
            <a
              href={href}
              className={cn(
                'text-foreground underline decoration-secondary-foreground/30 decoration-1 underline-offset-2',
                TAILWIND.micro,
                'hover:text-primary hover:decoration-secondary-foreground/50',
                'focus:outline-none focus:ring-1 focus:ring-secondary-foreground/20 focus:rounded-sm'
              )}
              target={href?.startsWith('http') ? '_blank' : undefined}
              rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
            >
              {children}
            </a>
          ),

          // Text style component
          strong: ({ children }) => (
            <strong className="font-semibold text-foreground">
              {children}
            </strong>
          ),

          em: ({ children }) => (
            <em className="italic text-foreground">
              {children}
            </em>
          ),

          // Add image component
          img: ({ src, alt, title }) => (
            <img
              src={src}
              alt={alt}
              title={title}
              className="max-w-full h-auto rounded-lg border border-border my-4"
              loading="lazy"
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};