import { useEffect, useState } from 'react'
import { STATUSES, getApplications, updateApplication } from './trackerApi.js'

const COLUMN_LABELS = {
  saved: 'Saved',
  applied: 'Applied',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
}

function formatDate(isoString) {
  return new Date(isoString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
  })
}

function Tracker() {
  const [applications, setApplications] = useState([])
  const [status, setStatus] = useState('loading') // 'loading' | 'ready' | 'error'
  const [error, setError] = useState(null)
  const [dropTarget, setDropTarget] = useState(null)

  useEffect(() => {
    getApplications()
      .then((data) => {
        setApplications(data.applications)
        setStatus('ready')
      })
      .catch(() => setStatus('error'))
  }, [])

  async function save(id, changes) {
    setError(null)
    try {
      const updated = await updateApplication(id, changes)
      setApplications((apps) => apps.map((app) => (app.id === id ? updated : app)))
    } catch (err) {
      setError(err.message)
    }
  }

  function moveTo(id, newStatus) {
    const app = applications.find((a) => a.id === id)
    if (app && app.status !== newStatus) save(id, { status: newStatus })
  }

  if (status === 'loading') return <p>Loading your board…</p>
  if (status === 'error') return <p>Couldn't load your applications. Is the API running?</p>

  return (
    <div>
      {error && <p className="error">{error}</p>}
      {applications.length === 0 && (
        <p className="job-meta">
          Your board is empty. Click <strong>Save</strong> on a job in the Jobs tab to start tracking it.
        </p>
      )}

      <div className="board">
        {STATUSES.map((column) => {
          const cards = applications.filter((app) => app.status === column)
          return (
            <section
              key={column}
              className={`column ${dropTarget === column ? 'drop-target' : ''}`}
              onDragOver={(e) => {
                e.preventDefault()
                setDropTarget(column)
              }}
              onDragLeave={() => setDropTarget(null)}
              onDrop={(e) => {
                e.preventDefault()
                setDropTarget(null)
                moveTo(Number(e.dataTransfer.getData('text/plain')), column)
              }}
            >
              <h2 className="column-title">
                {COLUMN_LABELS[column]} <span className="count">{cards.length}</span>
              </h2>
              {cards.map((app) => (
                <ApplicationCard key={app.id} app={app} onMove={moveTo} onSave={save} />
              ))}
            </section>
          )
        })}
      </div>
    </div>
  )
}

function ApplicationCard({ app, onMove, onSave }) {
  const [editing, setEditing] = useState(false)
  const [notes, setNotes] = useState(app.notes || '')

  function saveNotes() {
    onSave(app.id, { notes: notes.trim() || null })
    setEditing(false)
  }

  return (
    <article
      className="app-card"
      draggable={!editing}
      onDragStart={(e) => e.dataTransfer.setData('text/plain', String(app.id))}
    >
      <h3>{app.job.title}</h3>
      <p className="job-meta">{app.job.company}</p>
      {app.applied_at && <p className="job-meta">Applied {formatDate(app.applied_at)}</p>}

      {editing ? (
        <div className="notes-edit">
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            maxLength={2000}
            rows={3}
            autoFocus
          />
          <div className="notes-actions">
            <button onClick={saveNotes}>Save</button>
            <button
              className="secondary"
              onClick={() => {
                setNotes(app.notes || '')
                setEditing(false)
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <button className="notes" onClick={() => setEditing(true)}>
          {app.notes || 'Add notes'}
        </button>
      )}

      <select
        value={app.status}
        onChange={(e) => onMove(app.id, e.target.value)}
        aria-label={`Status for ${app.job.title}`}
      >
        {STATUSES.map((s) => (
          <option key={s} value={s}>
            {COLUMN_LABELS[s]}
          </option>
        ))}
      </select>
    </article>
  )
}

export default Tracker
