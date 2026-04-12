export const getApiKey = () => localStorage.getItem('relay_api_key') || import.meta.env.VITE_RELAY_API_KEY || ''

export const setApiKey = (value) => {
  localStorage.setItem('relay_api_key', value)
}

export const api = async (path, opts = {}) => {
  const key = getApiKey()
  const response = await fetch(path, {
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
