import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

const HUMAN_ID = import.meta.env.VITE_RELAY_HUMAN_ID || 'human'

export default function ProjectCreationPage() {
  const navigate = useNavigate()
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const [draft, setDraft] = useState({
    name: '',
    brief: '',
    lead_agent_id: '',
  })

  useEffect(() => {
    let alive = true
    api('/api/agents')
      .then((rows) => {
        if (!alive) return
        setAgents(rows)
        setDraft((current) => ({
          ...current,
          lead_agent_id: current.lead_agent_id || rows[0]?.id || '',
        }))
        setLoading(false)
      })
      .catch((err) => {
        if (!alive) return
        setError(err.message || String(err))
        setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [])

  const selectedAgent = useMemo(
    () => agents.find((agent) => String(agent.id) === String(draft.lead_agent_id)) || null,
    [agents, draft.lead_agent_id],
  )

  const submit = async (event) => {
    event.preventDefault()
    if (!draft.name.trim()) {
      setError('Project name is required.')
      return
    }
    if (!draft.brief.trim()) {
      setError('A brief is needed to orchestrate. Describe your goal.')
      return
    }
    if (!draft.lead_agent_id) {
      setError('Pick a lead agent to receive the orchestration task.')
      return
    }

    setSubmitting(true)
    setError('')

    let project = null
    try {
      project = await api('/api/projects', {
        method: 'POST',
        body: JSON.stringify({
          name: draft.name.trim(),
          description: draft.brief,
          status: 'Orchestrating',
          lead_agent_id: draft.lead_agent_id,
        }),
      })

      await api('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({
          project_id: Number(project.id),
          title: `Orchestrate: ${draft.name.trim()}`,
          description: draft.brief,
          assignee_id: draft.lead_agent_id,
          reporter_id: HUMAN_ID,
          priority: 'P0',
          status: 'To Do',
          tags: 'orchestration, system',
          comment: 'Project brief submitted via Start Orchestration.',
        }),
      })

      navigate(`/projects/${project.id}`)
    } catch (err) {
      if (project?.id) {
        try {
          await api(`/api/projects/${project.id}`, {
            method: 'PATCH',
            body: JSON.stringify({ status: 'Failed' }),
          })
        } catch {
          // best-effort rollback marker
        }
      }
      setError(err.message || String(err))
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="project-page-shell"><div className="project-page-card">Loading project creation...</div></div>
  }

  return (
    <div className="project-page-shell">
      <div className="project-create-wrap">
        <button className="project-back-link" onClick={() => navigate(-1)} type="button">← Cancel</button>

        <div className="project-page-card">
          <div className="eyebrow">Relay</div>
          <h1 className="project-create-title">New Project</h1>
          <p className="project-create-copy">
            Describe what you want to accomplish. The orchestrator will decompose your brief into a task plan.
          </p>

          <form className="project-create-form" onSubmit={submit}>
            <label className="field">
              <span className="field-label">Project Name</span>
              <input
                value={draft.name}
                onChange={(e) => setDraft((current) => ({ ...current, name: e.target.value }))}
                placeholder="Give this project a clear name"
                required
              />
            </label>

            <label className="field">
              <span className="field-label">Brief *</span>
              <textarea
                rows="8"
                value={draft.brief}
                onChange={(e) => setDraft((current) => ({ ...current, brief: e.target.value }))}
                placeholder="What's the goal? What context does the orchestrator need? What constraints exist?"
                required
              />
              <span className="field-hint">Markdown supported. Be specific, the orchestrator reads every word.</span>
            </label>

            <label className="field">
              <span className="field-label">Lead Agent</span>
              <select
                value={draft.lead_agent_id}
                onChange={(e) => setDraft((current) => ({ ...current, lead_agent_id: e.target.value }))}
              >
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>{agent.name}</option>
                ))}
              </select>
              <span className="field-hint">
                This agent receives the kickoff orchestration task.
                {selectedAgent ? ` Current: ${selectedAgent.name}.` : ''}
              </span>
            </label>

            {error ? <div className="project-inline-error">{error}</div> : null}

            <button className="primary-button project-create-cta" type="submit" disabled={submitting || !agents.length}>
              {submitting ? 'Starting...' : 'Start Orchestration'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
