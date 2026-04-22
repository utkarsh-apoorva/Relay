import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import React from 'react'
import { BrowserRouter } from 'react-router-dom'
import ProjectCreationPage from '../pages/ProjectCreationPage'

describe('ProjectCreationPage Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch.mockReset()
  })

  it('renders the project creation form', async () => {
    global.fetch.mockImplementation((url) => {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectCreationPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      expect(screen.getByText(/Brief to Orchestrator/i)).toBeInTheDocument()
    })
  })

  it('shows validation error when name is empty', async () => {
    global.fetch.mockImplementation((url) => {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectCreationPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const submitButton = screen.getByRole('button', { name: /Submit Brief/i })
      userEvent.click(submitButton)
    })

    await waitFor(() => {
      expect(screen.getByText(/Project name is required/i)).toBeInTheDocument()
    })
  })

  it('shows validation error when brief is empty', async () => {
    global.fetch.mockImplementation((url) => {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectCreationPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const nameInput = screen.getByPlaceholderText(/Give this project a clear name/i)
      userEvent.type(nameInput, 'My Project')

      const submitButton = screen.getByRole('button', { name: /Submit Brief/i })
      userEvent.click(submitButton)
    })

    await waitFor(() => {
      expect(screen.getByText(/brief is needed/i)).toBeInTheDocument()
    })
  })

  it('displays word count for brief textarea', async () => {
    global.fetch.mockImplementation((url) => {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectCreationPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/What's the goal/i)
      userEvent.type(textarea, 'This is a test brief')
    })

    await waitFor(() => {
      expect(screen.getByText(/5 \/ 500 words/i)).toBeInTheDocument()
    })
  })

  it('navigates back on cancel', async () => {
    global.fetch.mockImplementation((url) => {
      return Promise.resolve({ ok: true, json: () => Promise.resolve({}), headers: { get: () => 'application/json' } })
    })

    render(
      <BrowserRouter>
        <ProjectCreationPage />
      </BrowserRouter>
    )

    await waitFor(() => {
      const cancelButton = screen.getByRole('button', { name: /Cancel/i })
      userEvent.click(cancelButton)
    })
  })
})