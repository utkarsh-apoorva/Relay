import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getApiKey, setApiKey as saveApiKey } from './api/client'

const COLUMNS = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Done']
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
  const [view] = useState('projects')
  const [projects, setProjects] = useState([])
  const [agents, setAgents] = useState([])
  const [tasks, setTasks] = useState([])
  const [sprints, setSprints] = useState([])
  const [error, setError] = useState('')
  const [apiKey, setApiKeyState] = useState(getApiKey())
  const [apiKeyCollapsed, setApiKeyCollapsed] = useState(false)
  const [projectId, setProjectId] = useState('')
  const [sprintId, setSprintId] = useState('')
  const [selectedTask, setSelectedTask] = useState(null)
  const [taskDraft, setTaskDraft] = useState(blankTask())
  const [sprintDraft, setSprintDraft] = useState(blankSprint())
  const [commentText, setCommentText] = useState('')
  const [taskModalOpen, setTaskModalOpen] = useState(false)
  const [sprintModalOpen, setSprintModalOpen] = useState(false)

  useEffect(() => {
    saveApiKey(apiKey)
  }, [apiKey])

  const load = async () => {
    try {
      setError('')
      const [projectRows, agentRows, taskRows, sprintRows] = await Promise.all([
        api('/api/projects'),
        api('/api/agents'),
        api('/api/tasks'),
        api('/api/sprints'),
      ])
      setProjects(projectRows)
      setAgents(agentRows)
      setTasks(taskRows)
      setSprints(sprintRows)
      if (!projectId && projectRows[0]) setProjectId(String(projectRows[0].id))
      if (projectId && !projectRows.some((project) => String(project.id) === String(projectId))) {
        setProjectId(projectRows[0] ? String(projectRows[0].id) : '')
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
                onClick={() => navigate(`/projects/${project.id}`)}
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
                  onClick={() => setSprintId(String(sprint.id))}
                  type="button"
                >
                  <strong>{sprint.name}</strong>
                  <div className="muted">{prettyDate(sprint.start_date)} → {prettyDate(sprint.end_date)}</div>
                </button>
              ))}
          </div>
        </div>
      </aside>

      <main className="content">
        <header className="topbar">
          <div>
            <div className="eyebrow">localhost:3000</div>
            <h1>Projects</h1>
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

        {error ? <div className="error-banner">{error}</div> : null}

        {view === 'projects' ? (
          <section className="grid cards-2">
            {projects.map((project) => (
              <article className="card" key={project.id} onClick={() => navigate(`/projects/${project.id}`)}>
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
