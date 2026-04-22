import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import AgentRegistryPage from '../pages/AgentRegistryPage'

const mockAgents = [
  {
    id: 'human',
    name: 'Human',
    avatar: '👤',
    role: 'Owner',
    model: '',
    provider: '',
    status: 'Online',
    last_active: '2026-01-01T00:00:00',
    current_tasks: 2,
    total_tasks: 10,
    capabilities: [],
  },
  {
    id: 'agent1',
    name: 'Agent One',
    avatar: '🤖',
    role: 'Worker',
    model: 'openai/gpt-4o',
    provider: 'openai',
    status: 'Idle',
    last_active: '2026-01-01T00:00:00',
    current_tasks: 1,
    total_tasks: 5,
    capabilities: ['coding', 'testing'],
  },
  {
    id: 'agent2',
    name: 'Agent Two',
    avatar: '🤖',
    role: 'Reviewer',
    model: 'anthropic/claude-sonnet-4-6',
    provider: 'anthropic',
    status: 'Busy',
    last_active: '2026-01-01T00:00:00',
    current_tasks: 3,
    total_tasks: 8,
    capabilities: ['review', 'qa'],
  },
]

describe('AgentRegistryPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockReset()
  })

  it('renders loading state initially', () => {
    global.fetch.mockImplementation(() => new Promise(() => {}))

    render(
      <BrowserRouter>
        <AgentRegistryPage />
      </BrowserRouter>
    )

    expect(screen.getByText(/Loading agents/i)).toBeInTheDocument()
  })

  it('displays agent list when loaded', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <AgentRegistryPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Agent Registry')).toBeInTheDocument()
    })
  })

  it('shows error on API failure', async () => {
    global.fetch.mockRejectedValue(new Error('Failed to load agents'))

    render(
      <BrowserRouter>
        <AgentRegistryPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Failed to load agents/i)).toBeInTheDocument()
    })
  })

  it('displays agent capabilities', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <AgentRegistryPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/coding, testing/i)).toBeInTheDocument()
    })
  })

  it('shows agent status indicators', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <AgentRegistryPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText('Online')).toBeInTheDocument()
      expect(screen.getByText('Idle')).toBeInTheDocument()
      expect(screen.getByText('Busy')).toBeInTheDocument()
    })
  })

  it('displays task counts per agent', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/agents')) return Promise.resolve({ ok: true, json: () => Promise.resolve(mockAgents), headers: { get: () => 'application/json' } })
      return Promise.resolve({ ok: true, json: () => Promise.resolve([]), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <AgentRegistryPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/2.*current/i)).toBeInTheDocument()
    })
  })
})