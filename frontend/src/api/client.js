const STORAGE_KEY = 'relay_api_key'

// In production, VITE_API_URL is set to the Railway backend URL.
// In local dev, it's empty and the vite proxy handles /api/* → localhost:8000.
const API_BASE = (typeof __API_BASE__ !== 'undefined' ? __API_BASE__ : '').replace(/\/$/, '')

export const getApiKey = () => sessionStorage.getItem(STORAGE_KEY) || ''

export const setApiKey = (value) => {
  if (value) {
    sessionStorage.setItem(STORAGE_KEY, value)
    return
  }
  sessionStorage.removeItem(STORAGE_KEY)
}

export class ApiError extends Error {
  constructor(code, message, field = null, meta = null) {
    super(message)
    this.code = code
    this.field = field
    this.meta = meta
  }
}

/**
 * Extract the error message for a specific field from an API validation
 * errors object. Handles both flat `{ field: "message" }` and nested
 * `{ errors: [{ field, message }] }` shapes.
 */
export const getFieldError = (errors, fieldName) => {
  if (!errors) return null
  if (typeof errors === 'object' && !Array.isArray(errors)) {
    if (fieldName in errors) return errors[fieldName]
    // Handle nested validation shapes
    if ('errors' in errors && Array.isArray(errors.errors)) {
      const match = errors.errors.find((e) => e.field === fieldName)
      return match ? match.message : null
    }
  }
  return null
}

export const api = async (path, opts = {}) => {
  const key = getApiKey()
  const url = `${API_BASE}${path}`
  const response = await fetch(url, {
    ...opts,
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': key,
      ...(opts.headers || {}),
    },
  })

  const ct = response.headers.get('content-type') || ''
  const isJson = ct.includes('application/json')

  if (!response.ok) {
    if (isJson) {
      try {
        const body = await response.json()
        throw new ApiError(
          body.error || 'SERVER_ERROR',
          body.message || response.statusText,
          body.field || null,
          body.meta || null,
        )
      } catch (e) {
        if (e instanceof ApiError) throw e
        // JSON parse failed — treat as generic server error
        throw new ApiError('SERVER_ERROR', response.statusText)
      }
    }
    // Non-JSON error body (e.g. HTML error page from nginx/railway)
    const text = await response.text()
    throw new ApiError('SERVER_ERROR', text || response.statusText)
  }

  if (!isJson) {
    const text = await response.text()
    return text || {}
  }

  const body = await response.text()
  if (!body) return {}
  try {
    return JSON.parse(body)
  } catch {
    return body
  }
}
