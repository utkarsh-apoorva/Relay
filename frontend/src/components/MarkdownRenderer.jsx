import React from "react";
import ReactMarkdown from "react-markdown";

const ATTRIBUTION_PATTERN = /^## \[([^\]|]+)\|([^\]]+)\]/;

function AttributionBlock({ children }) {
  return (
    <div className="attribution-block">
      {children}
    </div>
  );
}

function renderers() {
  return {
    // Custom code blocks with distinct styling
    code({ inline, className, children, ...props }) {
      if (inline) {
        return (
          <code className="md-inline-code" {...props}>
            {children}
          </code>
        );
      }
      return (
        <pre className="md-pre">
          <code className={className} {...props}>
            {children}
          </code>
        </pre>
      );
    },

    // Attribution block pattern: ## [Agent Name | Timestamp]
    heading({ children, level, ...props }) {
      const text = String(children);
      const match = text.match(ATTRIBUTION_PATTERN);
      if (match && level === 2) {
        const agentName = match[1].trim();
        const timestamp = match[2].trim();
        return (
          <h2 className="md-attribution-heading" {...props}>
            <span className="md-attribution-agent">{agentName}</span>
            <span className="md-attribution-timestamp">{timestamp}</span>
          </h2>
        );
      }
      return (
        <h1 className={`md-h${level}`} {...props}>
          {children}
        </h1>
      );
    },
  };
}

export default function MarkdownRenderer({ content, className = "" }) {
  if (!content) return null;

  return (
    <div className={`md-content ${className}`}>
      <ReactMarkdown
        components={{
          // Headings with attribution support
          h1: ({ children, ...props }) => {
            const text = String(children);
            const match = text.match(ATTRIBUTION_PATTERN);
            if (match) {
              return (
                <div className="md-attribution-heading">
                  <span className="md-attribution-agent">{match[1].trim()}</span>
                  <span className="md-attribution-timestamp">{match[2].trim()}</span>
                </div>
              );
            }
            return <h1 className="md-h1" {...props}>{children}</h1>;
          },
          h2: ({ children, ...props }) => {
            const text = String(children);
            const match = text.match(ATTRIBUTION_PATTERN);
            if (match) {
              return (
                <div className="md-attribution-heading">
                  <span className="md-attribution-agent">{match[1].trim()}</span>
                  <span className="md-attribution-timestamp">{match[2].trim()}</span>
                </div>
              );
            }
            return <h2 className="md-h2" {...props}>{children}</h2>;
          },

          // Code blocks
          pre: ({ children }) => <pre className="md-pre">{children}</pre>,
          code: ({ inline, className, children, ...props }) => {
            if (inline) {
              return <code className="md-inline-code" {...props}>{children}</code>;
            }
            return (
              <code className={`md-code ${className || ""}`} {...props}>
                {children}
              </code>
            );
          },

          // Links open in new tab
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
              {children}
            </a>
          ),

          // Lists
          ul: ({ children }) => <ul className="md-ul">{children}</ul>,
          ol: ({ children }) => <ol className="md-ol">{children}</ol>,
          li: ({ children }) => <li className="md-li">{children}</li>,

          // Blockquotes
          blockquote: ({ children }) => (
            <blockquote className="md-blockquote">{children}</blockquote>
          ),

          // Tables
          table: ({ children }) => (
            <div className="md-table-wrapper">
              <table className="md-table">{children}</table>
            </div>
          ),
          th: ({ children }) => <th className="md-th">{children}</th>,
          td: ({ children }) => <td className="md-td">{children}</td>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}