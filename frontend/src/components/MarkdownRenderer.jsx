import React from "react";
import ReactMarkdown from "react-markdown";

const ATTRIBUTION_PATTERN = /^## \[([^\]|]+)\|([^\]]+)\]/;
const ATTRIBUTION_COLORS = ['#7c6aff', '#f0a732', '#2adfaa', '#f05252', '#60a5fa', '#ec4899'];

function getAgentColor(name) {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return ATTRIBUTION_COLORS[Math.abs(hash) % ATTRIBUTION_COLORS.length];
}

function hexToRgb(hex) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `${r}, ${g}, ${b}`;
}

function formatAttributionTimestamp(ts) {
  try {
    const d = new Date(ts);
    if (isNaN(d.getTime())) return ts;
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} hours ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)} days ago`;
    return d.toLocaleDateString('en-GB', {day: '2-digit', month: 'short', year: 'numeric'});
  } catch {
    return ts;
  }
}

function splitAttributionBlocks(content) {
  if (!content) return [];
  const blocks = [];
  const parts = content.split(/(?=^## \[)/gm);
  for (const part of parts) {
    if (part.startsWith('## [')) {
      const match = part.match(/^## \[([^\]|]+)\|([^\]]+)\]/);
      if (match) {
        blocks.push({
          type: 'attribution',
          agentName: match[1].trim(),
          timestamp: match[2].trim(),
          raw: part,
        });
      } else {
        blocks.push({ type: 'plain', raw: part });
      }
    } else if (part.trim()) {
      blocks.push({ type: 'plain', raw: part });
    }
  }
  return blocks;
}

export default function MarkdownRenderer({ content, className = "" }) {
  if (!content) return null;

  const blocks = splitAttributionBlocks(content);

  return (
    <div className={`md-content ${className}`}>
      {blocks.map((block, i) => {
        if (block.type === 'attribution') {
          const agentColor = getAgentColor(block.agentName);
          return (
            <div
              key={i}
              className="md-attribution-block"
              style={{ '--agent-color-rgb': hexToRgb(agentColor) }}
            >
              <ReactMarkdown
                components={{
                  h1: ({ children, ...props }) => {
                    const text = String(children);
                    const match = text.match(ATTRIBUTION_PATTERN);
                    if (match) {
                      return (
                        <div className="md-attribution-heading">
                          <span className="md-attribution-agent">{match[1].trim()}</span>
                          <span className="md-attribution-timestamp">{formatAttributionTimestamp(match[2].trim())}</span>
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
                          <span className="md-attribution-timestamp">{formatAttributionTimestamp(match[2].trim())}</span>
                        </div>
                      );
                    }
                    return <h2 className="md-h2" {...props}>{children}</h2>;
                  },
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
                  a: ({ href, children }) => (
                    <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
                      {children}
                    </a>
                  ),
                  ul: ({ children }) => <ul className="md-ul">{children}</ul>,
                  ol: ({ children }) => <ol className="md-ol">{children}</ol>,
                  li: ({ children }) => <li className="md-li">{children}</li>,
                  blockquote: ({ children }) => (
                    <blockquote className="md-blockquote">{children}</blockquote>
                  ),
                  table: ({ children }) => (
                    <div className="md-table-wrapper">
                      <table className="md-table">{children}</table>
                    </div>
                  ),
                  th: ({ children }) => <th className="md-th">{children}</th>,
                  td: ({ children }) => <td className="md-td">{children}</td>,
                }}
              >
                {block.raw}
              </ReactMarkdown>
            </div>
          );
        }

        return (
          <ReactMarkdown
            key={i}
            components={{
              h1: ({ children, ...props }) => {
                const text = String(children);
                const match = text.match(ATTRIBUTION_PATTERN);
                if (match) {
                  return (
                    <div className="md-attribution-heading">
                      <span className="md-attribution-agent">{match[1].trim()}</span>
                      <span className="md-attribution-timestamp">{formatAttributionTimestamp(match[2].trim())}</span>
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
                      <span className="md-attribution-timestamp">{formatAttributionTimestamp(match[2].trim())}</span>
                    </div>
                  );
                }
                return <h2 className="md-h2" {...props}>{children}</h2>;
              },
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
              a: ({ href, children }) => (
                <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
                  {children}
                </a>
              ),
              ul: ({ children }) => <ul className="md-ul">{children}</ul>,
              ol: ({ children }) => <ol className="md-ol">{children}</ol>,
              li: ({ children }) => <li className="md-li">{children}</li>,
              blockquote: ({ children }) => (
                <blockquote className="md-blockquote">{children}</blockquote>
              ),
              table: ({ children }) => (
                <div className="md-table-wrapper">
                  <table className="md-table">{children}</table>
                </div>
              ),
              th: ({ children }) => <th className="md-th">{children}</th>,
              td: ({ children }) => <td className="md-td">{children}</td>,
            }}
          >
            {block.raw}
          </ReactMarkdown>
        );
      })}
    </div>
  );
}
