import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeKatex from 'rehype-katex';
import rehypeHighlight from 'rehype-highlight';
import 'katex/dist/katex.min.css';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

/** 代码块渲染 */
const CodeBlock: React.FC<{ language?: string; children: React.ReactNode }> = ({ language, children }) => (
  <pre className="md-code-block" data-language={language || 'text'}>
    <code className={`md-code ${language ? `language-${language}` : ''}`}>
      {children}
    </code>
  </pre>
);

/** 内联代码 */
const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="md-inline-code">{children}</code>
);

export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, className = '' }) => {
  return (
    <div className={`markdown-body ${className}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeKatex, rehypeHighlight]}
        components={{
          code({ className: cls, children }) {
            const match = /language-(\w+)/.exec(cls || '');
            const isInline = !match && !String(children).includes('\n');
            if (isInline) {
              return <InlineCode>{children}</InlineCode>;
            }
            return <CodeBlock language={match?.[1]}>{String(children).replace(/\n$/, '')}</CodeBlock>;
          },
          pre({ children }) {
            return <>{children}</>;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};