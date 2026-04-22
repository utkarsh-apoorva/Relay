import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import TaskDetailPage from '../pages/TaskDetailPage'

const mockTask = {
  id: 1,
  project_id: 1,
  sprint_id: 1,
  title: 'Test Task',
  description: 'Task description',
  assignee_id: 'agent1',
  assignee_name: 'Agent One',
  reporter_id: 'human',
  reporter_name: 'Human',
  priority: 'P2',
  status: 'To Do',
  tags: 'test,backend',
  due_date: '2026-01-15',
  eval_brief: 'Complete this task',
  result_description: '',
  judgement: '',
  trace: '',
  depends_on: '',
  comments: [],
  created_at: '2026-01-01T00:00:00',
  updated_at: '2026-01-01T00:00:00',
  project_name: 'Test Project',
  sprint_name: 'Sprint 1',
}

const mockProjects = [
  { id: 1, name: 'Test Project', description: 'A test project', status: 'Active' },
]

describe('TaskDetailPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockReset()
  })

  it('renders loading state initially', () => {
    global.fetch.mockImplementation(() => new Promise(() => {}))

    render(
      <BrowserRouter>
        <TaskDetailPage />
      </BrowserRouter>
    )

    expect(screen.getByText(/Loading task/i)).toBeInTheDocument()
  })

  it('shows task not found when task does not exist', async () => {
    global.fetch.mockImplementation(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve(null),
        headers: { get: () => 'application/json' },
      })
    )

    render(
      <BrowserRouter>
        <TaskDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Task not found/i)).toBeInTheDocument()
    })
  })

  it('displays task title and metadata', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/tasks/')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTask), headers: { get: () => 'application/json' } })
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <TaskDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Test Task')).toBeInTheDocument()
    })
  })

  it('displays task description', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/tasks/')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTask), headers: { get: () => 'application/json' } })
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <TaskDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Task description/i)).toBeInTheDocument()
    })
  })

  it('shows error on API failure', async () => {
    global.fetch.mockRejectedValue(new Error('Failed to load'))

    render(
      <BrowserRouter>
        <TaskDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Failed to load/i)).toBeInTheDocument()
    })
  })

  it('displays priority and status badges', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/tasks/')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTask), headers: { get: () => 'application/json' } })
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <TaskDetailPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('P2')).toBeInTheDocument()
      expect(screen.getByText('To Do')).toBeInTheDocument()
    })
  })
})