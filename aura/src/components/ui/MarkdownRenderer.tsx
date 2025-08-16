// src/components/ui/MarkdownRenderer.tsx
// Markdown渲染器 - 遵循灰度中庸设计哲学，集成所有markdown相关组件
import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Copy, Check } from 'lucide-react';
import { cn } from '@/lib/utils';

// ===== 内部组件定义 =====

// 内联代码组件
interface InlineCodeProps {
  children: React.ReactNode;
  className?: string;
}

const InlineCode: React.FC<InlineCodeProps> = ({ children, className }) => {
  return (
    <code className={cn(
      'inline',
      'px-1.5 py-0.5',
      'text-base font-mono', // 从 text-sm 改为 text-base，稍微大一些
      'bg-muted/40 text-foreground',
      'rounded-sm',
      'break-words',
      className
    )}>
      {children}
    </code>
  );
};

// 代码块组件
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
      'group relative rounded-xl overflow-hidden my-4', // 添加外边距
      'bg-card/75 backdrop-blur-xl',
      'border border-border',
      'shadow-lg shadow-black/20',
      'transition-all duration-300',
      'hover:border-foreground/20 hover:shadow-xl hover:shadow-black/30',
      className
    )}>
      {/* 头部信息栏 */}
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
              'p-1.5 text-secondary-foreground/60 rounded',
              'opacity-0 group-hover:opacity-100 transition-all duration-200',
              'hover:text-secondary-foreground hover:bg-muted/50',
              'focus:outline-none focus:text-secondary-foreground focus:bg-muted/50'
            )}
            aria-label={copied ? "已复制" : "复制代码"}
          >
            <div className="transition-all duration-200">
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </div>
          </button>
        </div>
      )}

      {/* 代码内容区域 */}
      <div className="relative">
        {/* 复制按钮（无头部信息时显示） */}
        {!filename && !language && (
          <button
            onClick={handleCopy}
            className={cn(
              'absolute top-3 right-3 z-10 p-1.5 rounded',
              'text-secondary-foreground/60 bg-card/50 backdrop-blur-sm',
              'opacity-0 group-hover:opacity-100 transition-all duration-200',
              'hover:text-secondary-foreground hover:bg-muted/50',
              'focus:outline-none focus:text-secondary-foreground focus:bg-muted/50'
            )}
            aria-label={copied ? "已复制" : "复制代码"}
          >
            <div className="transition-all duration-200">
              {copied ? <Check size={14} /> : <Copy size={14} />}
            </div>
          </button>
        )}

        <pre className={cn(
          'overflow-x-auto p-4',
          'text-sm leading-relaxed',
          'font-mono',
          !filename && !language && 'pr-12' // 为复制按钮留出空间
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
                      {line || '\u00A0'} {/* 空行显示为不间断空格 */}
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

// 表格组件
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

// 主表格容器
const Table: React.FC<TableProps> = ({ children, className }) => (
  <div className="w-full overflow-x-auto my-4"> {/* 添加水平滚动和外边距 */}
    <table className={cn(
      'w-full border-collapse',
      'bg-card/30 backdrop-blur-sm',
      'border border-border/40',
      'rounded-lg overflow-hidden',
      'min-w-full', // 确保表格最小宽度
      className
    )}>
      {children}
    </table>
  </div>
);

// 表格头部
const TableHeader: React.FC<TableHeaderProps> = ({ children, className }) => (
  <thead className={cn(
    'bg-card/50 backdrop-blur-sm',
    'border-b border-border/40',
    className
  )}>
    {children}
  </thead>
);

// 表格主体
const TableBody: React.FC<TableBodyProps> = ({ children, className }) => (
  <tbody className={cn(className)}>
    {children}
  </tbody>
);

// 表格行
const TableRow: React.FC<TableRowProps> = ({ children, className }) => (
  <tr className={cn(
    'border-b border-border/20 last:border-b-0',
    'hover:bg-muted/20 transition-colors duration-200', // 修复：更明显的悬停效果
    className
  )}>
    {children}
  </tr>
);

// 表格头单元格
const TableHead: React.FC<TableHeadProps> = ({ children, className }) => (
  <th className={cn(
    'px-4 py-3 text-left',
    'text-sm font-semibold text-foreground',
    'border-r border-border/20 last:border-r-0',
    'whitespace-nowrap', // 防止标题换行
    className
  )}>
    {children}
  </th>
);

// 表格数据单元格
const TableCell: React.FC<TableCellProps> = ({ children, className }) => (
  <td className={cn(
    'px-4 py-3',
    'text-sm text-secondary-foreground',
    'border-r border-border/20 last:border-r-0',
    className
  )}>
    {children}
  </td>
);

interface MarkdownRendererProps {
  content: string;
  className?: string; // 添加可选的外部样式
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
          // 代码块组件
          code: ((props: { inline?: boolean; className?: string; children?: React.ReactNode; [key: string]: unknown }) => {
            const { inline, className, children } = props;
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : undefined;

            // 修复 inline 判断：如果没有换行符且没有语言类，则认为是行内代码
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

          // 自定义表格组件
          table: ({ children }) => (
            <Table>{children}</Table>
          ),

          thead: ({ children }) => <TableHeader>{children}</TableHeader>,
          tbody: ({ children }) => <TableBody>{children}</TableBody>,
          tr: ({ children }) => <TableRow>{children}</TableRow>,
          th: ({ children }) => <TableHead>{children}</TableHead>,
          td: ({ children }) => <TableCell>{children}</TableCell>,

          // 优化其他元素
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

          // 标题组件 - 添加锚点支持
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

// 无序列表组件 - 简化逻辑，依赖CSS处理嵌套
ul: ({ children }) => (
  <ul className="my-4 pl-0 list-none space-y-1.0">
    {children}
  </ul>
),

ol: ((props: { children?: React.ReactNode; start?: number; [key: string]: unknown }) => {
  const { children, start } = props;
  // 使用状态来跟踪计数器
  let counter = start || 1;

  return (
    <ol className="my-4 pl-0 list-none space-y-1.0">
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
      <span className="flex-shrink-0 text-secondary-foreground/70 select-none mr-2.5 flex items-center h-7">
        {isOrdered ? (
          <span className="text-sm font-medium min-w-[1.2rem] text-right inline-block">
            {listNumber}.
          </span>
        ) : (
          // 圆点在固定高度容器中垂直居中，与文本行高匹配
          <span className="w-1.5 h-1.5 bg-secondary-foreground/60 rounded-full" />
        )}
      </span>
      <div className="flex-1 min-w-0">
        {children}
      </div>
    </li>
  );
}) as React.ComponentType,

          // 链接组件 - 微妙的交互效果，符合灰度中庸哲学
          a: ({ href, children }) => (
            <a
              href={href}
              className={cn(
                'text-foreground underline decoration-secondary-foreground/30 decoration-1 underline-offset-2',
                'transition-all duration-300 ease-in-out',
                'hover:text-primary hover:decoration-secondary-foreground/50',
                'focus:outline-none focus:ring-1 focus:ring-secondary-foreground/20 focus:rounded-sm'
              )}
              target={href?.startsWith('http') ? '_blank' : undefined}
              rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
            >
              {children}
            </a>
          ),

          // 文本样式组件
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

          // 添加图片组件
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