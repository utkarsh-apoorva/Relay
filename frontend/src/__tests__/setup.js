import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import '@testing-library/jest-dom'

global.fetch = vi.fn()

afterEach(() => {
  cleanup()
  global.fetch.mockReset()
})

const mockApiKey = 'test-api-key-12345'
const mockSessionStorage = {
  getItem: vi.fn((key) => key === 'relay_api_key' ? mockApiKey : null),
  setItem: vi.fn(),
  removeItem: vi.fn(),
}
global.sessionStorage = mockSessionStorage

const mockNavigate = vi.fn()
const mockUseNavigate = () => mockNavigate

export { mockNavigate, mockUseNavigate }