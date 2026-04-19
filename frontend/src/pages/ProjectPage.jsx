import React, { useEffect, useMemo, useState } from 'react'
import { DragDropContext, Draggable, Droppable } from '@hello-pangea/dnd'
import { useNavigate, useParams } from 'react-router-dom'
import MarkdownRenderer from '../components/MarkdownRenderer'
import { api } from '../api/client'

const COLUMNS = ['Backlog', 'To Do', 'In Progress', 'In Review', 'Done']
const TABS = [
  ['kanban', 'Kanban'],
  ['wiki', 'Wiki'],
  ['brief', 'Brief'],
  ['activity', 'Activity'],
]

const STATUS_META = {
  Orchestrating: { dot: 'status-dot orchestrating', label: 'Orchestrating' },
  Active: { dot: 'status-dot active', label: 'Active' },
  Paused: { dot: 'status-dot paused', label: 'Paused' },
  'Re-orchestrating': { dot: 'status-dot reorchestrating', label: 'Re-orchestrating' },
  Completed: { dot: 'status-dot completed', label: 'Completed' },
  Failed: { dot: 'status-dot failed', label: 'Failed' },
}

function DraggableTaskCard({ task, index, navigate }) {
  return (
    <Draggable draggableId={String(task.id)} index={index}>
      {(provided, snapshot) => (
        <button
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          className={`project-task-card${snapshot.isDragging ? ' project-task-card--dragging' : ''}`}
          onClick={() => navigate(`/projects/${task.project_id}/tasks/${task.id}`)}
          type="button"
        >
          <div className="row-between">
            <strong>#{task.id}</strong>
            <span className={`priority ${String(task.priority || 'P2').toLowerCase()}`}>{task.priority}</span>
          </div>
          <div className="project-task-title">{task.title}</div>
          <div className="muted">{task.assignee_name || task.assignee_id || 'Unassigned'}</div>
        </button>
      )}
    </Draggable>
  )
}

export default function ProjectPage() {
  const { projectId } = useParams()
  const navigate = useNavigate()
  const [projects, setProjects] = useState([])
  const [tasks, setTasks] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [tab, setTab] = useState('kanban')
  const [wikiError, setWikiError] = useState('')

  const load = async (showSpinner = false) => {
    if (showSpinner) setLoading(true)
    try {
      setError('')
      const [projectRows, taskRows] = await Promise.all([
        api('/api/projects'),
        api('/api/tasks'),
      ])
      setProjects(projectRows)
      setTasks(taskRows)
      setLoading(false)
    } catch (err) {
      setError(err.message || String(err))
      setLoading(false)
    }
  }

  useEffect(() => {
    load(true)
  }, [projectId])

  const project = useMemo(
    () => projects.find((item) => String(item.id) === String(projectId)) || null,
    [projects, projectId],
  )

  const projectTasks = useMemo(
    () => tasks.filter((task) => String(task.project_id) === String(projectId)),
    [tasks, projectId],
  )

  const handleDragEnd = async (result) => {
    if (!result.destination) return
    if (result.destination.droppableId === result.source.droppableId) return
    await api(`/api/tasks/${Number(result.draggableId)}`, {
      method: 'PATCH',
      body: JSON.stringify({ status: result.destination.droppableId }),
    })
    await load(false)
  }

  useEffect(() => {
    if (!project) return undefined
    if (!['Orchestrating', 'Re-orchestrating'].includes(project.status)) return undefined

    const timer = setInterval(() => load(false), 3000)
    return () => clearInterval(timer)
  }, [project?.status, projectId])

  const stats = useMemo(() => {
    const counts = Object.fromEntries(COLUMNS.map((column) => [column, 0]))
    projectTasks.forEach((task) => {
      if (counts[task.status] !== undefined) counts[task.status] += 1
    })
    return counts
  }, [projectTasks])

  const activity = useMemo(() => {
    if (!project) return []
    const items = [
      {
        ts: project.last_updated || project.created_at || '',
        text: `Project is currently ${project.status}`,
      },
      {
        ts: project.last_updated || project.created_at || '',
        text: `Project created with lead agent ${project.lead_agent_name || project.lead_agent_id || 'Unassigned'}`,
      },
      ...projectTasks.flatMap((task) => {
        const rows = [
          {
            ts: task.created_at,
            text: `Task #${task.id} created: ${task.title}`,
          },
        ]
        if (task.updated_at && task.updated_at !== task.created_at) {
          rows.push({
            ts: task.updated_at,
            text: `Task #${task.id} updated to ${task.status}`,
          })
        }
        return rows
      }),
    ]
    return items
      .filter((item) => item.ts)
      .sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())
  }, [project, projectTasks])

  useEffect(() => {
    if (tab !== 'wiki') return
    if (!project) return
    api(`/api/projects/${project.id}/wiki`)
      .then(() => setWikiError(''))
      .catch((err) => setWikiError(err.message || 'No wiki yet.'))
  }, [tab, project?.id])

  if (loading) return <div className="project-page-shell"><div className="project-page-card">Loading project...</div></div>
  if (error) return <div className="project-page-shell"><div className="project-page-card">{error}</div></div>
  if (!project) return <div className="project-page-shell"><div className="project-page-card">Project not found.</div></div>

  const statusMeta = STATUS_META[project.status] || { dot: 'status-dot', label: project.status }
  const taskCount = projectTasks.length
  const donePct = project['% done'] || 0
  const bannerMode = project.status === 'Failed'
    ? 'failed'
    : ['Orchestrating', 'Re-orchestrating'].includes(project.status)
      ? 'working'
      : 'ready'

  return (
    <div className="project-page-shell">
      <div className="project-page-wrap">
        <button className="project-back-link" onClick={() => navigate('/')} type="button">← Back to projects</button>

        <div className="project-header-card">
          <div className="row-between project-header-top">
            <div>
              <h1 className="project-page-title">{project.name}</h1>
              <div className="project-summary-line">
                Orchestrator: {project.lead_agent_name || project.lead_agent_id || 'Unassigned'} · {taskCount} tasks · {donePct}% done
              </div>
            </div>
            <div className="project-status-chip">
              <span className={statusMeta.dot} />
              <span>{statusMeta.label}</span>
            </div>
          </div>

          <div className="project-stat-grid">
            {COLUMNS.map((column) => (
              <div className="project-stat-pill" key={column}>
                <strong>{stats[column] || 0}</strong>
                <span>{column}</span>
              </div>
            ))}
          </div>

          <div className={`orchestrator-banner ${bannerMode}`}>
            {bannerMode === 'working' ? (
              <>
                <div>
                  <div className="orchestrator-banner-title">🔄 {project.lead_agent_name || project.lead_agent_id || 'Orchestrator'} is decomposing your brief into tasks...</div>
                  <div className="muted">This usually takes 30–90 seconds. New tasks will appear below as they are created.</div>
                </div>
                <button className="ghost-button" onClick={() => navigate('/')} type="button">Back</button>
              </>
            ) : null}

            {bannerMode === 'ready' ? (
              <>
                <div>
                  <div className="orchestrator-banner-title">✅ Project is ready</div>
                  <div className="muted">The orchestration kickoff task has been created. Review the brief and task plan below.</div>
                </div>
                <button className="ghost-button" onClick={() => setTab('brief')} type="button">View Brief</button>
              </>
            ) : null}

            {bannerMode === 'failed' ? (
              <>
                <div>
                  <div className="orchestrator-banner-title">⚠️ Orchestration failed</div>
                  <div className="muted">The project was created but the orchestration kickoff did not complete cleanly.</div>
                </div>
                <button className="ghost-button" onClick={() => navigate('/projects/new')} type="button">Try Again</button>
              </>
            ) : null}
          </div>
        </div>

        <div className="project-tabs">
          {TABS.map(([id, label]) => (
            <button
              key={id}
              className={tab === id ? 'project-tab active' : 'project-tab'}
              onClick={() => setTab(id)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>

        {tab === 'kanban' ? (
          <DragDropContext onDragEnd={handleDragEnd}>
            <div className="project-board-grid">
              {COLUMNS.map((column) => {
                const columnTasks = projectTasks.filter((task) => task.status === column)
                return (
                  <div className="project-board-column" key={column}>
                    <div className="project-board-column-head">
                      <strong>{column}</strong>
                      <span>{columnTasks.length}</span>
                    </div>
                    <Droppable droppableId={column}>
                      {(provided) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.droppableProps}
                          className="stack"
                        >
                          {columnTasks.length ? columnTasks.map((task, index) => (
                            <DraggableTaskCard key={task.id} task={task} index={index} navigate={navigate} />
                          )) : <div className="project-empty-state">No tasks yet.</div>}
                          {provided.placeholder}
                        </div>
                      )}
                    </Droppable>
                  </div>
                )
              })}
            </div>
          </DragDropContext>
        ) : null}

        {tab === 'brief' ? (
          <div className="project-page-card">
            <div className="panel-title">Original Brief</div>
            <div className="project-brief-meta">
              Submitted {new Date(project.last_updated || Date.now()).toLocaleString()} · Orchestrator: {project.lead_agent_name || project.lead_agent_id || 'Unassigned'}
            </div>
            <MarkdownRenderer content={project.description || '_No brief provided._'} />
          </div>
        ) : null}

        {tab === 'wiki' ? (
          <div className="project-page-card">
            <div className="panel-title">Wiki</div>
            <div className="project-empty-state">{wikiError || 'Wiki view is wired, but no wiki content exists yet.'}</div>
          </div>
        ) : null}

        {tab === 'activity' ? (
          <div className="project-page-card">
            <div className="panel-title">Activity</div>
            <div className="stack">
              {activity.length ? activity.map((item, index) => (
                <div className="project-activity-row" key={`${item.ts}-${index}`}>
                  <div className="project-activity-dot" />
                  <div>
                    <div className="muted">{new Date(item.ts).toLocaleString()}</div>
                    <div>{item.text}</div>
                  </div>
                </div>
              )) : <div className="project-empty-state">No activity yet.</div>}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
