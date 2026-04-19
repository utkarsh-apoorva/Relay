import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getApiKey } from '../api/client'

const STATUS_FILTERS = ['All', 'Online', 'Idle', 'Offline']

const statusColor = (status) => {
  if (status === 'Online') return '#2adfaa'
  if (status === 'Idle') return '#fcd34d'
  return '#4a4a55'
}

const relativeTime = (iso) => {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'Just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  return `${days}d ago`
}

function AgentCard({ agent }) {
  const capabilities = (agent.capabilities || []).filter(Boolean)
  const color = statusColor(agent.status)

  return (
    <div className="agent-card">
      <div className="agent-card__header">
        <div className="agent-card__avatar">
          {agent.avatar || agent.name?.[0] || '?'}
        </div>
        <div className="agent-card__info">
          <div className="agent-card__name">{agent.name}</div>
          <div className="agent-card__role">{agent.role}</div>
        </div>
        <div className="agent-card__status">
          <span className="agent-card__status-dot" style={{ background: color }} />
          {agent.status}
        </div>
      </div>

      <div className="agent-card__model">
        {agent.model}
        {agent.provider ? ` · ${agent.provider}` : ''}
      </div>

      {capabilities.length > 0 && (
        <div className="agent-card__capabilities">
          {capabilities.map((cap) => (
            <span key={cap} className="agent-card__capability">{cap}</span>
          ))}
        </div>
      )}

      <div className="agent-card__footer">
        <span>{agent.current_tasks || 0} active</span>
        <span className="muted">·</span>
        <span>{agent.total_tasks || 0} total</span>
        <span className="muted">·</span>
        <span className="agent-card__last-active">Last active: {relativeTime(agent.last_active)}</span>
      </div>
    </div>
  )
}

export default function AgentRegistryPage() {
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  const load = async () => {
    try {
      setError('')
      setLoading(true)
      const key = getApiKey()
      const rows = await api('/api/agents')
      setAgents(rows)
    } catch (err) {
      setError(err.message || String(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const filtered = agents.filter((agent) => {
    const matchesStatus = statusFilter === 'All' || agent.status === statusFilter
    const q = search.toLowerCase()
    const matchesSearch =
      !q ||
      (agent.name || '').toLowerCase().includes(q) ||
      (agent.role || '').toLowerCase().includes(q) ||
      (agent.model || '').toLowerCase().includes(q) ||
      (agent.provider || '').toLowerCase().includes(q) ||
      (agent.capabilities || []).some((c) => c.toLowerCase().includes(q))
    return matchesStatus && matchesSearch
  })

  return (
    <div className="agent-registry">
      <div className="agent-registry__header">
        <h1 className="agent-registry__title">Agents</h1>
        <p className="agent-registry__subtitle">Registered agents and their capabilities</p>
      </div>

      <div className="agent-registry__controls">
        <div className="agent-registry__filters">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              className={statusFilter === f ? 'project-tab active' : 'project-tab'}
              onClick={() => setStatusFilter(f)}
              type="button"
            >
              {f}
            </button>
          ))}
        </div>
        <input
          className="agent-registry__search"
          type="search"
          placeholder="Search agents..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {error ? <div className="error-banner">{error}</div> : null}

      {loading ? (
        <div className="agent-registry-loading">Loading agents…</div>
      ) : filtered.length === 0 ? (
        <div className="agent-registry-empty">
          {agents.length === 0
            ? 'No agents registered. Register an agent via the API to see it here.'
            : 'No agents match your filter.'}
        </div>
      ) : (
        <div className="agent-registry__grid">
          {filtered.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      )}
    </div>
  )
}