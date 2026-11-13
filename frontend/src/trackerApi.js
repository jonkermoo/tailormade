// Talks to the application tracker endpoints from docs/api.md:
//   GET   /api/applications
//   POST  /api/applications        { job_id }
//   PATCH /api/applications/{id}   { status?, notes? }
//
// The real endpoints aren't built yet, so USE_MOCK keeps the board working
// with data saved in the browser. Flip it to false once the API has them;
// the shapes are the same, so nothing else needs to change.
const USE_MOCK = true

export const STATUSES = ['saved', 'applied', 'interview', 'offer', 'rejected']

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json' },
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    const error = new Error(data.error || `Request failed (${res.status})`)
    error.status = res.status
    throw error
  }
  return data
}

// ---------- Mock: same responses as the API, stored in localStorage ----------

const STORAGE_KEY = 'tailormade.applications'

function loadMock() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || []
  } catch {
    return []
  }
}

function saveMock(applications) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(applications))
  } catch {
    // Storage blocked (e.g. private window): changes last until refresh
  }
}

const mock = {
  async list() {
    return { applications: loadMock() }
  },

  async create(job) {
    const applications = loadMock()
    if (applications.some((app) => app.job.id === job.id)) {
      const error = new Error('This job is already on your board')
      error.status = 409
      throw error
    }
    const now = new Date().toISOString()
    const application = {
      id: Math.max(0, ...applications.map((app) => app.id)) + 1,
      status: 'saved',
      notes: null,
      applied_at: null,
      updated_at: now,
      resume_version_id: null,
      job: { id: job.id, company: job.company, title: job.title },
    }
    saveMock([...applications, application])
    return application
  },

  async update(id, changes) {
    const applications = loadMock()
    const current = applications.find((app) => app.id === id)
    if (!current) {
      const error = new Error(`Application ${id} not found`)
      error.status = 404
      throw error
    }
    const now = new Date().toISOString()
    const updated = { ...current, ...changes, updated_at: now }
    // Same rule as the API: moving to "applied" fills in applied_at
    if (changes.status === 'applied' && !current.applied_at) {
      updated.applied_at = now
    }
    saveMock(applications.map((app) => (app.id === id ? updated : app)))
    return updated
  },
}

// ---------- What the components use ----------

export function getApplications() {
  return USE_MOCK ? mock.list() : request('/api/applications')
}

export function addApplication(job) {
  return USE_MOCK
    ? mock.create(job)
    : request('/api/applications', {
        method: 'POST',
        body: JSON.stringify({ job_id: job.id }),
      })
}

export function updateApplication(id, changes) {
  return USE_MOCK
    ? mock.update(id, changes)
    : request(`/api/applications/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(changes),
      })
}
