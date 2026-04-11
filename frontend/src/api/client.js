const KEY = localStorage.getItem('agentos_api_key') || 'gandalf-key'
export const api = async (path, opts={}) => {
  const res = await fetch(path, { ...opts, headers: { 'Content-Type': 'application/json', 'X-API-Key': KEY, ...(opts.headers||{}) } })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}
