import React, { useEffect, useMemo, useState } from 'react'
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd'
import { useNavigate } from 'react-router-dom'
import { api, getApiKey, setApiKey as saveApiKey } from './api/client'
import MarkdownRenderer from './components/MarkdownRenderer'

const COLUMNS = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Done']
const VIEWS = [
  ['projects', 'Projects'],
  ['kanban', 'Kanban'],
  ['approval', 'Approval'],
  ['calendar', 'Calendar'],
  ['agents', 'Agents'],
  ['usage', 'Usage'],
]
const HUMAN_ID = import.meta.env.VITE_RELAY_HUMAN_ID || 'human'
const HUMAN_NAME = import.meta.env.VITE_RELAY_HUMAN_NAME || 'Human'

const blankTask = (projectId = '', sprintId = '') => ({
  id: null,
  project_id: projectId ? String(projectId) : '',
  sprint_id: sprintId ? String(sprintId) : '',
  title: '',
  description: '',
  assignee_id: HUMAN_ID,
  reporter_id: HUMAN_ID,
  priority: 'P2',
  status: 'Backlog',
  tags: '',
  due_date: '',
  comment: '',
})

const blankSprint = (projectId = '') => ({
  project_id: projectId ? String(projectId) : '',
  name: '',
  start_date: '',
  end_date: '',
})

const prettyDate = (value) => {
  if (!value) return 'No due date'
  const d = new Date(`${value}T00:00:00`)
  if (Number.isNaN(d.getTime())) return value
  return d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
}

const isoDate = (date) => date.toISOString().slice(0, 10)

function Modal({ title, onClose, children, footer }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="eyebrow">Relay</div>
            <h3>{title}</h3>
          </div>
          <button className="icon-button" onClick={onClose} type="button">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer ? <div className="modal-footer">{footer}</div> : null}
      </div>
    </div>
  )
}

function Field({ label, children, hint }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint ? <span className="field-hint">{hint}</span> : null}
    </label>
  )
}

export default function App() {
  const navigate = useNavigate()
  const [view, setView] = useState('projects')
  const [projects, setProjects] = useState([])
  const [agents, setAgents] = useState([])
  const [tasks, setTasks] = useState([])
  const [sprints, setSprints] = useState([])
  const [usage, setUsage] = useState({ rows: [], totals: [] })
  const [error, setError] = useState('')
  const [apiKey, setApiKeyState] = useState(getApiKey())
  const [apiKeyCollapsed, setApiKeyCollapsed] = useState(false)
  const [projectId, setProjectId] = useState('')
  const [sprintId, setSprintId] = useState('')
  const [calendarScope, setCalendarScope] = useState('all')
  const [selectedAgentId, setSelectedAgentId] = useState('')
  const [selectedTask, setSelectedTask] = useState(null)
  const [taskDraft, setTaskDraft] = useState(blankTask())
  const [sprintDraft, setSprintDraft] = useState(blankSprint())
  const [commentText, setCommentText] = useState('')
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [sprintModalOpen, setSprintModalOpen] = useState(false)
  const [approvalTargets, setApprovalTargets] = useState({})

  useEffect(() => {
    saveApiKey(apiKey)
  }, [apiKey])

  const load = async () => {
    try {
      setError('')
      const [projectRows, agentRows, taskRows, sprintRows, usageRows] = await Promise.all([
        api('/api/projects'),
        api('/api/agents'),
        api('/api/tasks'),
        api('/api/sprints'),
        api('/api/usage/tokens'),
      ])
      setProjects(projectRows)
      setAgents(agentRows)
      setTasks(taskRows)
      setSprints(sprintRows)
      setUsage(usageRows)
      if (!projectId && projectRows[0]) setProjectId(String(projectRows[0].id))
      if (projectId && !projectRows.some((project) => String(project.id) === String(projectId))) {
        setProjectId(projectRows[0] ? String(projectRows[0].id) : '')
      }
      if (selectedAgentId && !agentRows.some((agent) => String(agent.id) === String(selectedAgentId))) {
        setSelectedAgentId('')
      }
      if (calendarScope !== 'all' && !projectRows.some((project) => String(project.id) === String(calendarScope))) {
        setCalendarScope('all')
      }
      if (getApiKey().trim()) setApiKeyCollapsed(true)
    } catch (err) {
      setError(err.message || String(err))
    }
  }

  const submitApiKey = async (event) => {
    event.preventDefault()
    await load()
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!projectId && projects[0]) setProjectId(String(projects[0].id))
  }, [projectId, projects])

  useEffect(() => {
    if (projectId && sprintId) {
      const sprintStillValid = sprints.some(
        (sprint) => String(sprint.id) === String(sprintId) && String(sprint.project_id) === String(projectId),
      )
      if (!sprintStillValid) setSprintId('')
    }
  }, [projectId, sprintId, sprints])

  const currentProject = useMemo(
    () => projects.find((project) => String(project.id) === String(projectId)) || null,
    [projects, projectId],
  )
  const currentSprint = useMemo(
    () => sprints.find((sprint) => String(sprint.id) === String(sprintId)) || null,
    [sprints, sprintId],
  )
  const selectedAgent = useMemo(
    () => agents.find((agent) => String(agent.id) === String(selectedAgentId)) || null,
    [agents, selectedAgentId],
  )

  const projectTasks = useMemo(
    () => tasks.filter((task) => !projectId || String(task.project_id) === String(projectId)),
    [tasks, projectId],
  )
  const sprintTasks = useMemo(
    () => projectTasks.filter((task) => !sprintId || String(task.sprint_id || '') === String(sprintId)),
    [projectTasks, sprintId],
  )
  const kanbanTasks = sprintTasks
  const approvalTasks = useMemo(
    () => projectTasks.filter((task) => task.assignee_id === HUMAN_ID),
    [projectTasks],
  )
  const selectedAgentTasks = useMemo(
    () => (selectedAgentId ? tasks.filter((task) => task.assignee_id === selectedAgentId) : []),
    [tasks, selectedAgentId],
  )
  const calendarTasks = useMemo(() => {
    const source = calendarScope === 'all'
      ? tasks
      : tasks.filter((task) => String(task.project_id) === String(calendarScope))
    return source.filter((task) => task.due_date)
  }, [tasks, calendarScope])

  const board = useMemo(
    () => COLUMNS.map((column) => ({ name: column, items: kanbanTasks.filter((task) => task.status === column) })),
    [kanbanTasks],
  )

  const calendarDays = useMemo(() => {
    const start = new Date()
    start.setHours(0, 0, 0, 0)
    return Array.from({ length: 35 }, (_, index) => {
      const date = new Date(start)
      date.setDate(start.getDate() + index)
      const key = isoDate(date)
      return {
        key,
        date,
        tasks: calendarTasks.filter((task) => task.due_date === key),
      }
    })
  }, [calendarTasks])

  const totalTokens = usage.rows.reduce((sum, row) => sum + Number(row.tokens || 0), 0)
  const totalCost = usage.rows.reduce((sum, row) => sum + Number(row.estimated_cost || 0), 0)
  const approvalCount = approvalTasks.length

  const openProjectModal = () => {
    navigate('/projects/new')
  }

  const openSprintModal = () => {
    setSprintDraft(blankSprint(projectId || projects[0]?.id || ''))
    setSprintModalOpen(true)
  }

  const openTaskModal = (task = null) => {
    const baseProjectId = task ? String(task.project_id) : String(projectId || projects[0]?.id || '')
    const baseSprintId = task ? String(task.sprint_id || '') : String(sprintId || '')
    setSelectedTask(task)
    setCommentText('')
    setTaskDraft(
      task
        ? {
            id: task.id,
            project_id: baseProjectId,
            sprint_id: baseSprintId,
            title: task.title,
            description: task.description || '',
            assignee_id: task.assignee_id || HUMAN_ID,
            reporter_id: task.reporter_id || HUMAN_ID,
            priority: task.priority || 'P2',
            status: task.status || 'Backlog',
            tags: task.tags || '',
            due_date: task.due_date || '',
            comment: '',
          }
        : blankTask(baseProjectId, baseSprintId),
    )
    setTaskModalOpen(true)
  }

  const closeTaskModal = () => {
    setTaskModalOpen(false)
    setSelectedTask(null)
    setCommentText('')
  }

  const handleDragEnd = async (result) => {
    if (!result.destination) return
    if (result.destination.droppableId === result.source.droppableId) return
    await api(`/api/tasks/${Number(result.draggableId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: result.destination.droppableId }),
    })
    await load()
  }

  const saveTask = async (event) => {
    event.preventDefault()
    const payload = {
      project_id: Number(taskDraft.project_id),
      sprint_id: taskDraft.sprint_id ? Number(taskDraft.sprint_id) : undefined,
      title: taskDraft.title,
      description: taskDraft.description,
      assignee_id: taskDraft.assignee_id,
      reporter_id: taskDraft.reporter_id,
      priority: taskDraft.priority,
      status: taskDraft.status,
      tags: taskDraft.tags,
      due_date: taskDraft.due_date,
    }
    if (selectedTask) {
      await api(`/api/tasks/${selectedTask.id}`, { method: 'PATCH', body: JSON.stringify(payload) })
      if (commentText.trim()) {
        await api(`/api/tasks/${selectedTask.id}/comment`, {
          method: 'POST',
          body: JSON.stringify({ content: commentText.trim(), author_id: HUMAN_ID, author_type: 'human' }),
        })
      }
    } else {
      await api('/api/tasks', {
        method: 'POST',
        body: JSON.stringify({
          ...payload,
          comment: taskDraft.comment,
        }),
      })
    }
    await load()
    closeTaskModal()
  }

  const saveSprint = async (event) => {
    event.preventDefault()
    await api('/api/sprints', {
      method: 'POST',
      body: JSON.stringify({
        ...sprintDraft,
        project_id: Number(sprintDraft.project_id),
      }),
    })
    await load()
    setSprintModalOpen(false)
  }

  const archiveProject = async (project) => {
    await api(`/api/projects/${project.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: 'Completed' }),
    })
    await load()
  }

  const quickUpdateTask = async (taskId, patch) => {
    await api(`/api/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    })
    await load()
  }

  const rejectTask = async (task) => {
    const reason = window.prompt('Rejection reason (optional)')
    if (reason) {
      await api(`/api/tasks/${task.id}/comment`, {
        method: 'POST',
        body: JSON.stringify({ content: reason, author_id: HUMAN_ID, author_type: 'human' }),
      })
    }
    await quickUpdateTask(task.id, { status: 'Rejected' })
  }

  const approveTask = async (task) => {
    const target = approvalTargets[task.id] || agents[0]?.id || ''
    await quickUpdateTask(task.id, { assignee_id: target, status: 'To Do' })
  }

  const reassignTask = async (task) => {
    const target = approvalTargets[task.id] || agents[0]?.id || ''
    await quickUpdateTask(task.id, { assignee_id: target })
  }

  const people = [{ id: HUMAN_ID, name: HUMAN_NAME, avatar: '👤' }, ...agents]

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">🦞</div>
          <div>
            <div className="brand-name">Relay</div>
            <div className="muted">local coordination hub</div>
          </div>
        </div>

        {apiKeyCollapsed ? (
          <button className="panel api-key-toggle" onClick={() => setApiKeyCollapsed(false)} type="button">
            {'API Key > '}
          </button>
        ) : (
          <form className="panel" onSubmit={submitApiKey}>
            <div className="panel-title">API key</div>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKeyState(e.target.value)}
              spellCheck="false"
              autoComplete="off"
            />
            <div className="muted">Stored only for this browser session. Not bundled into the frontend.</div>
            <button className="primary-button" type="submit">Connect</button>
          </form>
        )}

        <div className="nav">
          {VIEWS.map(([id, label]) => (
            <button key={id} className={view === id ? 'nav-button active' : 'nav-button'} onClick={() => setView(id)}>
              {label}
            </button>
          ))}
        </div>

        <div className="panel">
          <div className="panel-title row-between">
            <span>Projects</span>
            <button className="ghost-button" onClick={openProjectModal} type="button">+ New</button>
          </div>
          <div className="stack">
            {projects.map((project) => (
              <button
                key={project.id}
                className={String(project.id) === String(projectId) ? 'project-chip active' : 'project-chip'}
                onClick={() => {
                  setProjectId(String(project.id))
                  setView('kanban')
                }}
                type="button"
              >
                <div className="row-between">
                  <strong>{project.name}</strong>
                  <span className={`status-pill ${project.status.toLowerCase()}`}>{project.status}</span>
                </div>
                <div className="muted">{project.task_count} tasks, {project['% done']}% done</div>
              </button>
            ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-title row-between">
            <span>Sprints</span>
            <button className="ghost-button" onClick={openSprintModal} type="button">+ New</button>
          </div>
          <div className="stack">
            {sprints
              .filter((sprint) => !projectId || String(sprint.project_id) === String(projectId))
              .map((sprint) => (
                <button
                  key={sprint.id}
                  className={String(sprint.id) === String(sprintId) ? 'project-chip active' : 'project-chip'}
                  onClick={() => {
                    setSprintId(String(sprint.id))
                    setView('kanban')
                  }}
                  type="button"
                >
                  <strong>{sprint.name}</strong>
                  <div className="muted">{prettyDate(sprint.start_date)} → {prettyDate(sprint.end_date)}</div>
                </button>
              ))}
          </div>
        </div>

        <div className="panel">
          <div className="panel-title">Approval queue</div>
          <div className="metric">{approvalCount}</div>
          <div className="muted">Tasks waiting on {HUMAN_NAME}</div>
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <div className="eyebrow">localhost:3000</div>
            <h1>{VIEWS.find(([id]) => id === view)?.[1] || 'Relay'}</h1>
            <div className="muted">
              {currentProject ? `${currentProject.name}` : 'All projects'}
              {currentSprint ? ` · ${currentSprint.name}` : ''}
            </div>
          </div>
          <div className="toolbar">
            <button className="primary-button" onClick={() => openTaskModal()} type="button">+ Task</button>
            <button className="secondary-button" onClick={openProjectModal} type="button">+ Project</button>
            <button className="secondary-button" onClick={openSprintModal} type="button">+ Sprint</button>
          </div>
        </header>

        <div className="filters panel">
          <Field label="Project">
            <select value={projectId} onChange={(e) => setProjectId(e.target.value)}>
              <option value="">All projects</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Sprint">
            <select value={sprintId} onChange={(e) => setSprintId(e.target.value)}>
              <option value="">All sprints</option>
              {sprints
                .filter((sprint) => !projectId || String(sprint.project_id) === String(projectId))
                .map((sprint) => (
                  <option key={sprint.id} value={sprint.id}>{sprint.name}</option>
                ))}
            </select>
          </Field>
          <Field label="Calendar scope">
            <select value={calendarScope} onChange={(e) => setCalendarScope(e.target.value)}>
              <option value="all">All projects</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>{project.name}</option>
              ))}
            </select>
          </Field>
          <Field label="Active agent">
            <select value={selectedAgentId} onChange={(e) => setSelectedAgentId(e.target.value)}>
              <option value="">All agents</option>
              {agents.map((agent) => (
                <option key={agent.id} value={agent.id}>{agent.name}</option>
              ))}
            </select>
          </Field>
        </div>

        {error ? <div className="error-banner">{error}</div> : null}

        {view === 'projects' ? (
          <section className="grid cards-2">
            {projects.map((project) => (
              <article className="card" key={project.id} onClick={() => { setProjectId(String(project.id)); setView('kanban') }}>
                <div className="row-between gap">
                  <div>
                    <div className="eyebrow">Project</div>
                    <h3>{project.name}</h3>
                  </div>
                  <span className={`status-pill ${project.status.toLowerCase()}`}>{project.status}</span>
                </div>
                <p className="muted">{project.description || 'No description yet.'}</p>
                <div className="stats-row">
                  <div><strong>{project.sprint_count}</strong><span>sprints</span></div>
                  <div><strong>{project.task_count}</strong><span>tasks</span></div>
                  <div><strong>{project['% done']}%</strong><span>done</span></div>
                  <div><strong>{project.lead_agent_name}</strong><span>lead</span></div>
                </div>
                <div className="row-between gap">
                  <div className="muted">Updated {prettyDate(project.last_updated?.slice?.(0, 10) || project.last_updated)}</div>
                  <button className="ghost-button" onClick={(e) => { e.stopPropagation(); archiveProject(project) }} type="button">
                    Archive
                  </button>
                </div>
              </article>
            ))}
          </section>
        ) : null}

        {view === 'kanban' ? (
          <DragDropContext onDragEnd={handleDragEnd}>
            <div className="board">
              {board.map((column) => (
                <section className="column card" key={column.name}>
                  <div className="row-between gap">
                    <h3>{column.name}</h3>
                    <span className="metric small">{column.items.length}</span>
                  </div>
                  <Droppable droppableId={column.name}>
                    {(provided) => (
                      <div ref={provided.innerRef} {...provided.droppableProps} className="dropzone">
                        {column.items.map((task, index) => (
                          <Draggable key={task.id} draggableId={String(task.id)} index={index}>
                            {(drag) => (
                              <article
                                ref={drag.innerRef}
                                {...drag.draggableProps}
                                {...drag.dragHandleProps}
                                className={`task-card${task.result_description || task.judgement ? ' task-card--done' : ''}`}
                                onClick={() => navigate(`/projects/${task.project_id}/tasks/${task.id}`)}
                              >
                                {/* Title + priority */}
                                <div className="row-between gap" style={{marginBottom: '6px'}}>
                                  <span className="task-card-title">{task.title}</span>
                                  <span className={`priority ${task.priority.toLowerCase()}`}>{task.priority}</span>
                                </div>

                                {/* Assignee */}
                                <div className="task-card-assignee">
                                  <span className="avatar avatar--sm">
                                    {(() => {
                                      const p = people.find((x) => x.id === task.assignee_id);
                                      return p?.avatar || '?';
                                    })()}
                                  </span>
                                  <span className="muted" style={{fontSize: '0.8rem'}}>
                                    {task.assignee_name || task.assignee_id || 'Unassigned'}
                                  </span>
                                  {/* Status dot */}
                                  <span className={`status-dot status-dot--${task.status.toLowerCase().replace(' ', '-')}"`} title={task.status} />
                                </div>

                                {/* Description first line */}
                                {task.description && (
                                  <p className="task-card-desc muted">
                                    {task.description.split('\n')[0].slice(0, 80)}
                                    {task.description.length > 80 ? '…' : ''}
                                  </p>
                                )}

                                {/* Content indicators */}
                                {(task.result_description || task.judgement || task.eval_brief) && (
                                  <div style={{ display: 'flex', gap: '12px', marginTop: '4px' }}>
                                    {task.result_description && <span style={{color: '#2adfaa', fontSize: '0.75rem'}} title="Has result">✓ Result </span>}
                                    {task.judgement && <span style={{color: '#7c6aff', fontSize: '0.75rem'}} title="Has judgement">✓ Judgement </span>}
                                    {task.eval_brief && <span style={{color: '#fbbf24', fontSize: '0.75rem'}} title="Has eval brief">✓ Eval brief </span>}
                                  </div>
                                )}
                              </article>
                            )}
                          </Draggable>
                        ))}
                        {provided.placeholder}
                      </div>
                    )}
                  </Droppable>
                </section>
              ))}
            </div>
          </DragDropContext>
        ) : null}

        {view === 'approval' ? (
          <section className="grid cards-2">
            {approvalTasks.map((task) => {
              const target = approvalTargets[task.id] || agents[0]?.id || ''
              return (
                <article className="card" key={task.id}>
                  <div className="row-between gap">
                    <div>
                      <div className="eyebrow">Awaiting approval</div>
                      <h3>{task.title}</h3>
                    </div>
                    <span className="status-pill pending">Queued</span>
                  </div>
                  <p className="muted">{task.description || 'No description.'}</p>
                  <div className="muted">{task.project_name} · {task.priority} · {prettyDate(task.due_date)}</div>
                  <Field label="Reassign to">
                    <select value={target} onChange={(e) => setApprovalTargets((current) => ({ ...current, [task.id]: e.target.value }))}>
                      {people.filter((person) => person.id !== HUMAN_ID).map((person) => (
                        <option key={person.id} value={person.id}>{person.name}</option>
                      ))}
                    </select>
                  </Field>
                  <div className="toolbar compact">
                    <button className="primary-button" onClick={() => approveTask(task)} type="button">Approve</button>
                    <button className="secondary-button" onClick={() => openTaskModal(task)} type="button">Modify</button>
                    <button className="secondary-button" onClick={() => reassignTask(task)} type="button">Reassign</button>
                    <button className="danger-button" onClick={() => rejectTask(task)} type="button">Reject</button>
                  </div>
                </article>
              )
            })}
          </section>
        ) : null}

        {view === 'calendar' ? (
          <section className="calendar-wrap">
            <div className="calendar-header">
              <div>
                <div className="eyebrow">Due dates</div>
                <h3>Read-only calendar</h3>
              </div>
              <div className="muted">{calendarScope === 'all' ? 'All projects' : projects.find((project) => String(project.id) === String(calendarScope))?.name}</div>
            </div>
            <div className="calendar-grid">
              {calendarDays.map((day) => (
                <div key={day.key} className="calendar-day">
                  <div className="calendar-day-head">
                    <strong>{day.date.toLocaleDateString('en-GB', { weekday: 'short' })}</strong>
                    <span>{day.date.getDate()}</span>
                  </div>
                  <div className="calendar-date">{day.key}</div>
                  <div className="stack">
                    {day.tasks.map((task) => (
                      <button key={task.id} className="calendar-task" onClick={() => openTaskModal(task)} type="button">
                        <strong>{task.title}</strong>
                        <div className="muted">{task.project_name} · {task.assignee_name}</div>
                      </button>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {view === 'agents' ? (
          <section className="agents-layout">
            <div className="grid cards-2">
              {agents.map((agent) => (
                <article
                  key={agent.id}
                  className={String(agent.id) === String(selectedAgentId) ? 'card agent-card active' : 'card agent-card'}
                  onClick={() => setSelectedAgentId(agent.id)}
                >
                  <div className="row-between gap">
                    <div className="avatar">{agent.avatar}</div>
                    <span className={`status-pill ${agent.status.toLowerCase()}`}>{agent.status}</span>
                  </div>
                  <h3>{agent.name}</h3>
                  <div className="muted">{agent.role}</div>
                  <div className="muted">{agent.model} · {agent.provider}</div>
                  <div className="stats-row">
                    <div><strong>{agent.current_tasks}</strong><span>active</span></div>
                    <div><strong>{agent.total_tasks}</strong><span>tasks</span></div>
                  </div>
                  <div className="muted">Last active {prettyDate(agent.last_active?.slice?.(0, 10) || agent.last_active)}</div>
                </article>
              ))}
            </div>
            <div className="panel">
              <div className="row-between gap">
                <div>
                  <div className="eyebrow">Assigned tasks</div>
                  <h3>{selectedAgent ? selectedAgent.name : 'Pick an agent'}</h3>
                </div>
                {selectedAgent ? <span className="metric small">{selectedAgentTasks.length}</span> : null}
              </div>
              <div className="stack">
                {selectedAgentTasks.map((task) => (
                  <button key={task.id} className="task-list-item" onClick={() => openTaskModal(task)} type="button">
                    <div className="row-between gap">
                      <strong>{task.title}</strong>
                      <span className={`priority ${task.priority.toLowerCase()}`}>{task.priority}</span>
                    </div>
                    <div className="muted">{task.project_name} · {task.status} · {prettyDate(task.due_date)}</div>
                  </button>
                ))}
                {!selectedAgent ? <div className="muted">Select an agent to inspect their tasks.</div> : null}
              </div>
            </div>
          </section>
        ) : null}

        {view === 'usage' ? (
          <section className="stack">
            <div className="grid cards-3">
              <article className="card metric-card">
                <div className="eyebrow">Tokens</div>
                <div className="big-metric">{totalTokens.toLocaleString()}</div>
              </article>
              <article className="card metric-card">
                <div className="eyebrow">Estimated cost</div>
                <div className="big-metric">${totalCost.toFixed(4)}</div>
              </article>
              <article className="card metric-card">
                <div className="eyebrow">Rows</div>
                <div className="big-metric">{usage.rows.length}</div>
              </article>
            </div>
            <div className="card overflow">
              <table className="table">
                <thead>
                  <tr>
                    <th>Agent</th>
                    <th>Model</th>
                    <th>Tokens</th>
                    <th>Est. cost</th>
                  </tr>
                </thead>
                <tbody>
                  {usage.rows.map((row, index) => (
                    <tr key={`${row.agent}-${row.model}-${index}`}>
                      <td>{row.agent}</td>
                      <td>{row.model}</td>
                      <td>{row.tokens.toLocaleString()}</td>
                      <td>${Number(row.estimated_cost || 0).toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        ) : null}
      </main>

      {taskModalOpen ? (
        <Modal
          title={selectedTask ? 'Edit task' : 'New task'}
          onClose={closeTaskModal}
          footer={
            <>
              <button className="secondary-button" onClick={closeTaskModal} type="button">Cancel</button>
              <button className="primary-button" onClick={saveTask} type="button">Save</button>
            </>
          }
        >
          <form className="modal-form" onSubmit={saveTask}>
            <div className="grid two-col">
              <Field label="Project">
                <select
                  value={taskDraft.project_id}
                  onChange={(e) => setTaskDraft((current) => ({ ...current, project_id: e.target.value }))}
                  required
                >
                  <option value="">Pick a project</option>
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>{project.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Sprint">
                <select value={taskDraft.sprint_id} onChange={(e) => setTaskDraft((current) => ({ ...current, sprint_id: e.target.value }))}>
                  <option value="">No sprint</option>
                  {sprints
                    .filter((sprint) => !taskDraft.project_id || String(sprint.project_id) === String(taskDraft.project_id))
                    .map((sprint) => (
                      <option key={sprint.id} value={sprint.id}>{sprint.name}</option>
                    ))}
                </select>
              </Field>
            </div>
            <Field label="Title">
              <input value={taskDraft.title} onChange={(e) => setTaskDraft((current) => ({ ...current, title: e.target.value }))} required />
            </Field>
            <Field label="Description">
              <textarea rows="4" value={taskDraft.description} onChange={(e) => setTaskDraft((current) => ({ ...current, description: e.target.value }))} />
            </Field>
            <div className="grid two-col">
              <Field label="Assignee">
                <select value={taskDraft.assignee_id} onChange={(e) => setTaskDraft((current) => ({ ...current, assignee_id: e.target.value }))}>
                  <option value={HUMAN_ID}>{HUMAN_NAME}</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Reporter">
                <select value={taskDraft.reporter_id} onChange={(e) => setTaskDraft((current) => ({ ...current, reporter_id: e.target.value }))}>
                  <option value={HUMAN_ID}>{HUMAN_NAME}</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.id}>{agent.name}</option>
                  ))}
                </select>
              </Field>
            </div>
            <div className="grid three-col">
              <Field label="Priority">
                <select value={taskDraft.priority} onChange={(e) => setTaskDraft((current) => ({ ...current, priority: e.target.value }))}>
                  {['P0', 'P1', 'P2', 'P3'].map((priority) => <option key={priority} value={priority}>{priority}</option>)}
                </select>
              </Field>
              <Field label="Status">
                <select value={taskDraft.status} onChange={(e) => setTaskDraft((current) => ({ ...current, status: e.target.value }))}>
                  {COLUMNS.map((status) => <option key={status} value={status}>{status}</option>)}
                </select>
              </Field>
              <Field label="Due date">
                <input type="date" value={taskDraft.due_date} onChange={(e) => setTaskDraft((current) => ({ ...current, due_date: e.target.value }))} />
              </Field>
            </div>
            <Field label="Tags">
              <input value={taskDraft.tags} onChange={(e) => setTaskDraft((current) => ({ ...current, tags: e.target.value }))} placeholder="relay, backend" />
            </Field>
            {!selectedTask ? (
              <Field label="Initial comment">
                <textarea rows="3" value={taskDraft.comment} onChange={(e) => setTaskDraft((current) => ({ ...current, comment: e.target.value }))} />
              </Field>
            ) : null}
            {selectedTask ? (
              <div className="comments">
                <div className="panel-title">Comments</div>
                <div className="stack">
                  {selectedTask.comments?.map((comment) => (
                    <div className="comment" key={comment.id}>
                      <strong>{comment.author_id}</strong>
                      <div className="muted">{prettyDate(comment.created_at?.slice?.(0, 10) || comment.created_at)}</div>
                      <div>{comment.content}</div>
                    </div>
                  ))}
                </div>
                <Field label="Add comment">
                  <textarea rows="3" value={commentText} onChange={(e) => setCommentText(e.target.value)} />
                </Field>
              </div>
            ) : null}
          </form>
        </Modal>
      ) : null}

      {sprintModalOpen ? (
        <Modal
          title="New sprint"
          onClose={() => setSprintModalOpen(false)}
          footer={
            <>
              <button className="secondary-button" onClick={() => setSprintModalOpen(false)} type="button">Cancel</button>
              <button className="primary-button" onClick={saveSprint} type="button">Create</button>
            </>
          }
        >
          <form className="modal-form" onSubmit={saveSprint}>
            <Field label="Project">
              <select value={sprintDraft.project_id} onChange={(e) => setSprintDraft((current) => ({ ...current, project_id: e.target.value }))} required>
                <option value="">Pick a project</option>
                {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
              </select>
            </Field>
            <Field label="Name">
              <input value={sprintDraft.name} onChange={(e) => setSprintDraft((current) => ({ ...current, name: e.target.value }))} required />
            </Field>
            <div className="grid two-col">
              <Field label="Start date">
                <input type="date" value={sprintDraft.start_date} onChange={(e) => setSprintDraft((current) => ({ ...current, start_date: e.target.value }))} />
              </Field>
              <Field label="End date">
                <input type="date" value={sprintDraft.end_date} onChange={(e) => setSprintDraft((current) => ({ ...current, end_date: e.target.value }))} />
              </Field>
            </div>
          </form>
        </Modal>
      ) : null}
    </div>
  )
}
