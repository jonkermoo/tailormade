import { useEffect, useState } from 'react'
import { addApplication, getApplications } from './trackerApi.js'

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

function JobFeed() {
  const [jobs, setJobs] = useState([])
  const [status, setStatus] = useState('loading') // 'loading' | 'ready' | 'error'
  const [savedJobIds, setSavedJobIds] = useState(new Set())
  const [saveError, setSaveError] = useState(null)

  useEffect(() => {
    // Know which jobs are already on the board so their button says "Saved"
    getApplications()
      .then((data) => setSavedJobIds(new Set(data.applications.map((app) => app.job.id))))
      .catch(() => {})
  }, [])

  async function saveJob(job) {
    setSaveError(null)
    try {
      await addApplication(job)
      setSavedJobIds((ids) => new Set(ids).add(job.id))
    } catch (err) {
      if (err.status === 409) setSavedJobIds((ids) => new Set(ids).add(job.id))
      else setSaveError(err.message)
    }
  }

  useEffect(() => {
    fetch('/api/jobs')
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => {
        setJobs(data.jobs)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [])

  if (status === 'loading') return <p>Loading jobs…</p>
  if (status === 'error') return <p>Couldn't load jobs. Is the API running?</p>
  if (jobs.length === 0) return <p>No jobs yet.</p>

  return (
    <>
      {saveError && <p className="error">{saveError}</p>}
      <ul className="job-list">
        {jobs.map((job) => (
          <li key={job.id} className="job-card">
            <h3>{job.title}</h3>
            <p className="job-meta">
              {job.company} · {job.location}
              {job.is_remote && <span className="tag">Remote</span>}
            </p>
            <div className="job-footer">
              <span className="job-meta">Posted {formatDate(job.posted_at)}</span>
              <div className="job-actions">
                <a href={job.url} target="_blank" rel="noreferrer">
                  View job
                </a>
                <button
                  onClick={() => saveJob(job)}
                  disabled={savedJobIds.has(job.id)}
                >
                  {savedJobIds.has(job.id) ? 'Saved' : 'Save'}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </>
  )
}

export default JobFeed
