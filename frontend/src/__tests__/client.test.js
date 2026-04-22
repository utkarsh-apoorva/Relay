import { describe, it, expect } from 'vitest'
import { api, getApiKey, setApiKey, ApiError, getFieldError } from '../api/client'

describe('API Client', () => {
  describe('getApiKey', () => {
    it('returns empty string when no key stored', () => {
      sessionStorage.getItem.mockReturnValueOnce(null)
      const key = getApiKey()
      expect(key).toBe('')
    })

    it('returns stored key', () => {
      sessionStorage.getItem.mockReturnValueOnce('test-key')
      const key = getApiKey()
      expect(key).toBe('test-key')
    })
  })

  describe('setApiKey', () => {
    it('stores key when value provided', () => {
      setApiKey('new-key')
      expect(sessionStorage.setItem).toHaveBeenCalledWith('relay_api_key', 'new-key')
    })

    it('removes key when empty value provided', () => {
      setApiKey('')
      expect(sessionStorage.removeItem).toHaveBeenCalledWith('relay_api_key')
    })
  })

  describe('ApiError', () => {
    it('creates error with code and message', () => {
      const error = new ApiError('TEST_ERROR', 'Test message')
      expect(error.code).toBe('TEST_ERROR')
      expect(error.message).toBe('Test message')
      expect(error.field).toBeNull()
      expect(error.meta).toBeNull()
    })

    it('creates error with field', () => {
      const error = new ApiError('VALIDATION_ERROR', 'Invalid field', 'name')
      expect(error.field).toBe('name')
    })
  })

  describe('getFieldError', () => {
    it('returns null for null errors', () => {
      expect(getFieldError(null, 'name')).toBeNull()
    })

    it('returns null for undefined errors', () => {
      expect(getFieldError(undefined, 'name')).toBeNull()
    })

    it('extracts field error from flat object', () => {
      const errors = { name: 'Name is required' }
      expect(getFieldError(errors, 'name')).toBe('Name is required')
    })

    it('returns null for missing field', () => {
      const errors = { name: 'Name is required' }
      expect(getFieldError(errors, 'email')).toBeNull()
    })

    it('extracts field error from nested errors array', () => {
      const errors = { errors: [{ field: 'name', message: 'Name required' }] }
      expect(getFieldError(errors, 'name')).toBe('Name required')
    })
  })
})