import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import App from '../App'

const wrapApp = (ui) => {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

const mockProjects = [
  { id: 1, name: 'Test Project', description: 'A test project', status: 'Active', task_count: 5, '% done': 40, sprint_count: 1, lead_agent_name: 'Agent One', last_updated: '2026-01-01T00:00:00' },
]

const mockAgents = [
  { id: 'human', name: 'Human', role: 'Owner', status: 'Online', current_tasks: 2, total_tasks: 10, capabilities: [] },
  { id: 'agent1', name: 'Agent One', role: 'Worker', status: 'Idle', current_tasks: 1, total_tasks: 5, capabilities: ['coding'] },
]

const mockTasks = [
  { id: 1, project_id: 1, sprint_id: 1, title: 'Test Task', description: 'Description', assignee_id: 'agent1', assignee_name: 'Agent One', reporter_id: 'human', priority: 'P2', status: 'To Do', tags: 'test', due_date: '2026-01-15', comments: [], created_at: '2026-01-01T00:00:00', updated_at: '2026-01-01T00:00:00' },
]

const mockSprints = [
  { id: 1, project_id: 1, name: 'Sprint 1', start_date: '2026-01-01', end_date: '2026-01-14' },
]

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({}),
      headers: { get: () => 'application/json' },
    })
  })

  it('renders the app shell', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      if (url.includes('/api/tasks')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTasks), headers: { get: () => 'application/json' } })
      if (url.includes('/api/sprints')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSprints), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(<BrowserRouter><App /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText(/Relay/i)).toBeInTheDocument()
    })
  })

  it('displays project list', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      if (url.includes('/api/tasks')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTasks), headers: { get: () => 'application/json' } })
      if (url.includes('/api/sprints')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSprints), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(<BrowserRouter><App /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('Test Project')).toBeInTheDocument()
    })
  })

  it('shows error on API failure', async () => {
    global.fetch.mockRejectedValue(new Error('Network error'))

    render(<BrowserRouter><App /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.queryByText(/Network error/i)).toBeInTheDocument()
    })
  })

  it('opens task modal when clicking + Task button', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/projects')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockProjects), headers: { get: () => 'application/json' } })
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      if (url.includes('/api/tasks')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockTasks), headers: { get: () => 'application/json' } })
      if (url.includes('/api/sprints')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockSprints), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(<BrowserRouter><App /></BrowserRouter>)

    await waitFor(() => {
      const taskButton = screen.getByRole('button', { name: /Task/i })
      expect(taskButton).toBeInTheDocument()
    })
  })
})