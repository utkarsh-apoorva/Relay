import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import MarkdownRenderer from '../components/MarkdownRenderer'
import MarkdownEditor from '../components/MarkdownEditor'
import { api } from '../api/client'

export default function WikiPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [wiki, setWiki] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api(`/api/projects/${projectId}/wiki`)
      .then((w) => { setWiki(w); setDraft(w?.content || '') })
      .catch(() => setWiki(null))
      .finally(() => setLoading(false))
  }, [projectId])

  const startEdit = () => {
    setDraft(wiki?.content || '')
    setEditing(true)
  }

  const cancelEdit = () => {
    setEditing(false)
    setDraft(wiki?.content || '')
  }

  const saveWiki = async () => {
    setSaving(true)
    setError('')
    try {
      const updated = await api(`/api/projects/${projectId}/wiki`, {
        method: 'PUT',
        body: JSON.stringify({ content: draft }),
      })
      setWiki(updated)
      setEditing(false)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="wiki-loading">Loading wiki...</div>

  return (
    <div className="wiki-layout">
      <div className="wiki-header">
        <button className="wiki-back" onClick={() => navigate(`/projects/${projectId}`)}>
          ← Back to {wiki?.project_name || 'Project'}
        </button>
        <h1 className="wiki-title">{wiki?.project_name || 'Project'} Wiki</h1>
        <div className="wiki-actions">
          {!editing ? (
            <>
              {wiki && <span className="wiki-updated">Updated {new Date(wiki.updated_at).toLocaleDateString('en-GB', {day:'2-digit',month:'short',year:'numeric'})}</span>}
              <button className="primary-button" onClick={startEdit}>
                {wiki ? 'Edit' : 'Create'}
              </button>
            </>
          ) : (
            <>
              <button className="secondary-button" onClick={cancelEdit} disabled={saving}>Cancel</button>
              <button className="primary-button" onClick={saveWiki} disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </button>
            </>
          )}
        </div>
      </div>

      {error && <div className="project-inline-error">{error}</div>}

      {!wiki && !editing ? (
        <div className="wiki-empty">
          <p>No wiki yet.</p>
          <p className="wiki-empty-sub">Start building the project knowledge base.</p>
          <button className="primary-button" onClick={startEdit}>Create Wiki</button>
        </div>
      ) : editing ? (
        <div className="wiki-editor">
          <MarkdownEditor
            value={draft}
            onChange={setDraft}
            placeholder="Project documentation, decisions, and context..."
            minRows={12}
          />
        </div>
      ) : (
        <div className="wiki-content">
          <MarkdownRenderer content={wiki?.content || ''} />
        </div>
      )}
    </div>
  )
}
