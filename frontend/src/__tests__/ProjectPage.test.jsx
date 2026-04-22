import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import ProjectPage from '../pages/ProjectPage'

const mockProjects = [
  { id: 1, name: 'Test Project', description: 'A test project', status: 'Active', task_count: 5, '% done': 40, sprint_count: 1, lead_agent_name: 'Agent One', last_updated: '2026-01-01T00:00:00' },
]

const mockTasks = [
  { id: 1, project_id: 1, sprint_id: 1, title: 'Test Task', description: 'Description', assignee_id: 'agent1', assignee_name: 'Agent One', reporter_id: 'human', priority: 'P2', status: 'To Do', tags: 'test', due_date: '2026-01-15', comments: [], created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
]

describe('ProjectPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockReset()
  })

  it('renders loading state initially', () => {
    global.fetch.mockImplementation(() => new Promise(() => {}))

    render(
      <BrowserRouter>
        <ProjectPage />
      </BrowserRouter>
    )

    expect(screen.getByText(/Loading project/i)).toBeInTheDocument()
  })

  it('renders project not found when project does not exist', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
      if (url.includes('/api/tasks')) return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Project not found/i)).toBeInTheDocument()
    })
  })

  it('displays kanban board with columns', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      if (url.includes('/api/tasks')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTasks), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Backlog')).toBeInTheDocument()
      expect(screen.getByText('To Do')).toBeInTheDocument()
      expect(screen.getByText('In Progress')).toBeInTheDocument()
    })
  })

  it('shows error message on API failure', async () => {
    global.fetch.mockRejectedValue(new Error('API Error'))

    render(
      <BrowserRouter>
        <ProjectPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/API Error/i)).toBeInTheDocument()
    })
  })

  it('displays project header with stats', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      if (url.includes('/api/tasks')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTasks), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })
  })
})