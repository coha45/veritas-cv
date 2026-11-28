const apiOrigin = `${window.location.protocol === 'https:' ? 'https:' : 'http:'}//${window.location.hostname || '127.0.0.1'}:8000`
const TOKEN_KEY = 'veritas.sqlite-portal.token'

export const portalToken = {
  get() {
    try { return sessionStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
  },
  set(token) {
    try { sessionStorage.setItem(TOKEN_KEY, token) } catch {}
  },
  clear() {
    try { sessionStorage.removeItem(TOKEN_KEY) } catch {}
  },
}

export async function portalRequest(path, { method = 'GET', body } = {}) {
  const token = portalToken.get()
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (token) headers.Authorization = `Bearer ${token}`
  const response = await fetch(`${apiOrigin}/api/portal${path}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(result.detail || `Portal request failed (${response.status})`)
    error.status = response.status
    throw error
  }
  return result
}
