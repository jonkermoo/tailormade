import { useEffect, useState } from 'react'

const TABS = {
  jobs: {
    label: 'Jobs',
    body: 'Job feed goes here: new postings from the crawler, filtered by your saved searches and sorted by match score.',
  },
  tracker: {
    label: 'Tracker',
    body: 'Application board goes here: Saved, Applied, Interview, Offer. Each card links to the resume version you sent.',
  },
  resume: {
    label: 'Resume',
    body: 'Resume builder goes here: fill in your profile once, then tailor it to any job with one click.',
  },
}

function App() {
  const [tab, setTab] = useState('jobs')
  const [apiStatus, setApiStatus] = useState('checking...')

  useEffect(() => {
    fetch('/api/health')
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => setApiStatus(data.status))
      .catch(() => setApiStatus('offline'))
  }, [])

  return (
    <div className="app">
      <header className="header">
        <h1>TailorMade</h1>
        <span className="status">API: {apiStatus}</span>
      </header>

      <nav className="tabs">
        {Object.entries(TABS).map(([key, { label }]) => (
          <button
            key={key}
            className={tab === key ? 'active' : ''}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </nav>

      <section className="panel">
        <p>{TABS[tab].body}</p>
      </section>
    </div>
  )
}

export default App
