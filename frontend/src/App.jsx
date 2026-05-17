import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api/events'

function getBadgeClass(type) {
  if (!type) return 'badge-other'
  const t = type.toLowerCase()
  if (t.includes('hack'))  return 'badge-hackathon'
  if (t.includes('cod'))   return 'badge-coding'
  if (t.includes('work'))  return 'badge-workshop'
  if (t.includes('fest'))  return 'badge-fest'
  return 'badge-other'
}

function getSourceDot(source) {
  if (!source) return 'dot-default'
  const s = source.toLowerCase()
  if (s.includes('unstop'))    return 'dot-unstop'
  if (s.includes('devfolio'))  return 'dot-devfolio'
  if (s.includes('knowafest')) return 'dot-knowafest'
  return 'dot-default'
}

// ---- Event Card ----
function EventCard({ event }) {
  return (
    <div className="event-card">
      <div className="card-header">
        <span className={`event-type-badge ${getBadgeClass(event.event_type)}`}>
          {event.event_type || 'Event'}
        </span>
        <span className={`source-dot ${getSourceDot(event.source)}`} title={event.source} />
      </div>

      <h2 className="event-title">{event.title}</h2>
      {event.organization && <p className="event-org">🏛 {event.organization}</p>}

      <div className="card-meta">
        {event.date && (
          <span className="meta-item"><span className="meta-icon">📅</span>{event.date}</span>
        )}
        {event.location && (
          <span className="meta-item"><span className="meta-icon">📍</span>{event.location}</span>
        )}
        {event.source && (
          <span className="meta-item"><span className="meta-icon">🔗</span>via {event.source}</span>
        )}
      </div>

      <div className="card-footer">
        <a href={event.link} target="_blank" rel="noopener noreferrer" className="apply-btn">
          Apply Now →
        </a>
      </div>
    </div>
  )
}

// ---- Toast ----
function Toast({ message, type, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000)
    return () => clearTimeout(t)
  }, [onClose])
  return <div className={`toast toast-${type}`}>{message}</div>
}

// ---- Main App ----
export default function App() {
  const [events, setEvents]   = useState([])
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(null)
  const [typeFilter, setTypeFilter]   = useState('All')
  const [toast, setToast] = useState(null)

  const showToast = (msg, type = 'info') => setToast({ message: msg, type })

  const fetchEvents = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/`)
      if (!res.ok) throw new Error('Fetch failed')
      setEvents(await res.json())
    } catch {
      showToast('Failed to load events. Is the backend running?', 'info')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { fetchEvents() }, [fetchEvents])

  const triggerScrape = async (source) => {
    setScraping(source)
    const endpoint = source === 'all' ? `${API_BASE}/scrape-all` : `${API_BASE}/scrape/${source}`
    try {
      const res = await fetch(endpoint, { method: 'POST' })
      if (!res.ok) throw new Error()
      showToast(`Scraping ${source} started! Checking for new events...`, 'success')
      let attempts = 0
      const prevCount = events.length
      const interval = setInterval(async () => {
        attempts++
        try {
          const r = await fetch(`${API_BASE}/`)
          const data = await r.json()
          setEvents(data)
          if (data.length > prevCount || attempts >= 20) {
            clearInterval(interval)
            setScraping(null)
            showToast(
              data.length > prevCount
                ? `✅ Found ${data.length - prevCount} new events!`
                : 'Scrape complete. No new events.',
              'success'
            )
          }
        } catch { /* silent */ }
      }, 3000)
    } catch {
      showToast('Scrape trigger failed.', 'info')
      setScraping(null)
    }
  }

  // --- Derived filter options ---
  const eventTypes  = ['All', ...new Set(events.map(e => e.event_type).filter(Boolean))]

  // --- Apply filters ---
  const filtered = events
    .filter(e => typeFilter  === 'All' || e.event_type === typeFilter)

  return (
    <>
      {/* Navbar */}
      <nav className="navbar">
        <div className="navbar-logo">
          <div className="logo-icon">🐝</div>
          EventHive
        </div>
        <div className="navbar-actions">
          <button className="btn btn-ghost" onClick={fetchEvents}>↻ Refresh</button>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-badge">✦ AI-Powered Hackathon & Coding Aggregator</div>
        <h1>
          Find the Best <span className="gradient-text">Hackathons & Coding Events</span><br />
          Across India
        </h1>
        <p>
          Hackathons, coding competitions & tech fests — aggregated from Unstop, Devfolio, and Knowafest using AI.
        </p>

        <div className="stats-bar">
          <div className="stat-item"><span className="stat-num">{events.length}</span> events tracked</div>
          <div className="stat-item"><span className="stat-num">3</span> sources scraped</div>
        </div>

        <div className="scrape-controls">
          {['unstop', 'devfolio', 'knowafest'].map(s => (
            <button key={s} className="btn btn-ghost" onClick={() => triggerScrape(s)} disabled={!!scraping}>
              {scraping === s ? '⏳ Scraping...' : `⚡ Scrape ${s.charAt(0).toUpperCase()+s.slice(1)}`}
            </button>
          ))}
          <button className="btn btn-primary" onClick={() => triggerScrape('all')} disabled={!!scraping}>
            {scraping === 'all' ? '⏳ Running...' : '🚀 Scrape All'}
          </button>
        </div>
      </section>

      {/* Main */}
      <main className="container">

        {/* Event Type Filter */}
        {events.length > 0 && (
          <div className="filter-bar">
            <span className="filter-label">Type:</span>
            {eventTypes.map(t => (
              <button key={t} className={`pill ${typeFilter===t?'active':''}`} onClick={() => setTypeFilter(t)}>
                {t}
              </button>
            ))}
          </div>
        )}



        {/* Count header */}
        {!loading && (
          <div className="section-header">
            <span className="section-title">
              {typeFilter === 'All'
                ? 'All Events'
                : [typeFilter !== 'All' && typeFilter].filter(Boolean).join(' · ')
              }
            </span>
            <span className="section-count">{filtered.length} event{filtered.length !== 1 ? 's' : ''}</span>
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="loading-wrapper">
            <div className="spinner" />
            <span>Loading events...</span>
          </div>
        )}

        {/* Empty */}
        {!loading && filtered.length === 0 && (
          <div className="empty-state">
            <span className="empty-icon">🐝</span>
            <h2>{events.length === 0 ? 'No events yet' : 'No matches'}</h2>
            <p>{events.length === 0
              ? 'Click a "Scrape" button above to start collecting events!'
              : 'Try changing your filters above.'
            }</p>
          </div>
        )}

        {/* Grid */}
        {!loading && filtered.length > 0 && (
          <div className="events-grid">
            {filtered.map(e => <EventCard key={e.id} event={e} />)}
          </div>
        )}
      </main>

      {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
    </>
  )
}
