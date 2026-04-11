export const getApiKey = () => localStorage.getItem('agentos_api_key') || 'utkarsh-key'

export const setApiKey = (value) => {
  localStorage.setItem('agentos_api_key', value)
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
