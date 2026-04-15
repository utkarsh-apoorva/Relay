const STORAGE_KEY = 'relay_api_key'

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
