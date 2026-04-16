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

  const text = await response.text()
  if (!response.ok) {
    throw new Error(text || response.statusText)
  }
  if (!text) return {}
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}
