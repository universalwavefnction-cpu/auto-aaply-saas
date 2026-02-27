const BASE = '/api'

function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken()
  const defaultHeaders: Record<string, string> = {}
  if (token) defaultHeaders['Authorization'] = `Bearer ${token}`
  if (!(options.headers as Record<string, string>)?.['Content-Type']) {
    defaultHeaders['Content-Type'] = 'application/json'
  }
  const headers: Record<string, string> = {
    ...defaultHeaders,
    ...((options.headers as Record<string, string>) || {}),
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  return res.json()
}

export const api = {
  // Auth
  login: async (email: string, password: string) => {
    const res = await fetch(`${BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
    })
    return res.json()
  },
  register: (email: string, password: string) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify({ email, password }) }),
  me: () => request('/auth/me'),

  // Profile
  getProfile: () => request('/profile'),
  updateProfile: (data: any) => request('/profile', { method: 'PUT', body: JSON.stringify(data) }),
  addCredential: (data: any) =>
    request('/profile/credentials', { method: 'POST', body: JSON.stringify(data) }),
  deleteCredential: (id: number) => request(`/profile/credentials/${id}`, { method: 'DELETE' }),

  // CVs
  listCVs: () => request('/profile/cvs'),
  uploadCV: async (file: File, label: string) => {
    const token = getToken()
    const form = new FormData()
    form.append('file', file)
    form.append('label', label)
    const res = await fetch(`${BASE}/profile/cv?label=${encodeURIComponent(label)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    })
    return res.json()
  },
  deleteCV: (id: number) => request(`/profile/cv/${id}`, { method: 'DELETE' }),

  // Jobs
  getJobs: (params: Record<string, any> = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/jobs?${qs}`)
  },
  getJob: (id: number) => request(`/jobs/${id}`),
  getFilters: () => request('/jobs/filters/current'),
  updateFilters: (data: any) =>
    request('/jobs/filters', { method: 'PUT', body: JSON.stringify(data) }),

  // Applications
  getApplications: (params: Record<string, any> = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/applications?${qs}`)
  },
  updateResponse: (id: number, data: any) =>
    request(`/applications/${id}/response`, { method: 'POST', body: JSON.stringify(data) }),
  manualApply: (data: any) =>
    request('/applications/manual', { method: 'POST', body: JSON.stringify(data) }),

  // Dashboard
  getStats: () => request('/dashboard/stats'),

  // Bot Control
  startBot: (mode: string = 'scrape_and_apply') =>
    request(`/bot/start?mode=${mode}`, { method: 'POST' }),
  stopBot: () => request('/bot/stop', { method: 'POST' }),
  getBotStatus: () => request('/bot/status'),
  getBotSessions: () => request('/bot/logs/sessions'),
  getBotLogs: (sessionId?: string) =>
    request(`/bot/logs${sessionId ? `?session_id=${sessionId}` : ''}`),
  getBotAnalytics: () => request('/bot/logs/analytics'),
  getUnmatchedFields: () => request('/bot/logs/unmatched-fields'),
}
