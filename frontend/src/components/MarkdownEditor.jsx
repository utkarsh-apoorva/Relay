import React, { useRef, useState } from 'react'
import MarkdownRenderer from './MarkdownRenderer'

export default function MarkdownEditor({
  value = '',
  onChange,
  placeholder = '',
  minRows = 4,
}) {
  const [mode, setMode] = useState('write')
  const textareaRef = useRef(null)

  const insertMarkdown = (before, after = '', atBlockStart = false) => {
    const ta = textareaRef.current
    if (!ta) return
    const start = ta.selectionStart
    const end = ta.selectionEnd
    const selected = value.slice(start, end)

    if (atBlockStart) {
      const lineStart = value.lastIndexOf('\n', start - 1) + 1
      const lineEnd = value.indexOf('\n', start)
      const line = value.slice(lineStart, lineEnd === -1 ? value.length : lineEnd)
      const newValue =
        value.slice(0, lineStart) +
        before +
        line +
        (after || '') +
        value.slice(lineEnd === -1 ? value.length : lineEnd)
      onChange(newValue)
      return
    }

    const newText = before + (selected || '') + after
    const newValue = value.slice(0, start) + newText + value.slice(end)
    onChange(newValue)
    setTimeout(() => {
      ta.focus()
      const newPos = start + before.length + (selected.length || 0) + after.length
      ta.setSelectionRange(newPos, newPos)
    }, 0)
  }

  const handleToolbar = (action) => {
    switch (action) {
      case 'bold':    insertMarkdown('**', '**'); break
      case 'italic':  insertMarkdown('*', '*'); break
      case 'h1':      insertMarkdown('# ', '', true); break
      case 'h2':      insertMarkdown('## ', '', true); break
      case 'ul':      insertMarkdown('- ', '', true); break
      case 'ol':      insertMarkdown('1. ', '', true); break
      case 'code':    insertMarkdown('```\n', '\n```'); break
      case 'link':    insertMarkdown('[', '](url)'); break
    }
  }

  return (
    <div className="md-editor">
      <div className="md-editor-toolbar">
        <div className="md-editor-toolbar-left">
          {[
            { key: 'bold',   label: 'B',   style: { fontWeight: 700 } },
            { key: 'italic', label: 'I',   style: { fontStyle: 'italic' } },
            { key: 'h1',     label: 'H1' },
            { key: 'h2',     label: 'H2' },
            { key: 'ul',     label: '•' },
            { key: 'ol',     label: '1.' },
            { key: 'code',   label: '</>' },
            { key: 'link',   label: '🔗' },
          ].map(({ key, label, style }) => (
            <button
              key={key}
              type="button"
              className="md-editor-btn"
              onClick={() => handleToolbar(key)}
              style={style}
              title={key}
            >
              {label}
            </button>
          ))}
        </div>
        <div className="md-editor-toggle">
          <button
            type="button"
            className={mode === 'write' ? 'active' : ''}
            onClick={() => setMode('write')}
          >
            Write
          </button>
          <button
            type="button"
            className={mode === 'preview' ? 'active' : ''}
            onClick={() => setMode('preview')}
          >
            Preview
          </button>
        </div>
      </div>
      <div className="md-editor-body">
        {mode === 'write' ? (
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            rows={minRows}
            className="md-editor-textarea"
          />
        ) : (
          <div className="md-editor-preview">
            <MarkdownRenderer content={value} />
          </div>
        )}
      </div>
    </div>
  )
}
