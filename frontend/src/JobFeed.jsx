import { useEffect, useState } from 'react'

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

function JobFeed() {
  const [jobs, setJobs] = useState([])
  const [status, setStatus] = useState('loading') // 'loading' | 'ready' | 'error'

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
            <a href={job.url} target="_blank" rel="noreferrer">
              View job
            </a>
          </div>
        </li>
      ))}
    </ul>
  )
}

export default JobFeed
