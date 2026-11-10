import { Link } from 'react-router-dom'
import { formatEventDateRange } from '../utils/eventDate.js'
import EventImage from './EventImage.jsx'
import LoadingScreen from './LoadingScreen.jsx'

function BackLink() {
  return <Link className="back-link" to="/#evenimente">← Înapoi la evenimente</Link>
}

// Presentational detail view; `status` is one of loading | error | not-found | success.
export default function EventDetail({ status, event, error, onRetry }) {
  if (status === 'loading') return <LoadingScreen />
  if (status === 'not-found') return (
    <div className="empty-state" role="alert">
      <p className="eyebrow mb-3">Eroare 404</p>
      <h1 className="font-display text-3xl">Evenimentul nu a fost găsit.</h1>
      <p className="mt-3 text-[var(--muted)]">Este posibil ca evenimentul să fi fost șters sau linkul să fie greșit.</p>
      <Link className="primary-button mt-6" to="/#evenimente">Vezi toate evenimentele</Link>
    </div>
  )
  if (status === 'error') return (
    <div className="empty-state" role="alert">
      <p className="eyebrow mb-3">Conexiune întreruptă</p>
      <h1 className="font-display text-3xl">Nu am putut încărca evenimentul.</h1>
      <p className="mt-3 text-[var(--muted)]">{error}</p>
      <div className="detail-actions">
        <button type="button" className="primary-button" onClick={onRetry}>Încearcă din nou</button>
        <BackLink />
      </div>
    </div>
  )

  const dateLabel = formatEventDateRange(event.startAt, event.endAt)
  return (
    <article className="event-detail">
      <BackLink />
      <EventImage url={event.imageUrl} className="event-detail-media" eager />
      <p className="eyebrow mt-8 mb-3">{event.sourceName || 'Cluj-Napoca'}</p>
      <h1 className="font-display text-3xl leading-tight sm:text-5xl">{event.title}</h1>
      <dl className="event-details detail-facts">
        <div><dt>Data</dt><dd>{dateLabel ? <time dateTime={event.startAt}>{dateLabel}</time> : 'Data va fi anunțată'}</dd></div>
        <div>
          <dt>Locație</dt>
          <dd>{event.venueName}{event.venueAddress && <span className="detail-address">{event.venueAddress}</span>}</dd>
        </div>
        <div><dt>Preț</dt><dd>{event.price}</dd></div>
        {event.sourceName && <div><dt>Sursă</dt><dd>{event.sourceName}</dd></div>}
      </dl>
      {/* The source link stays above the description so it is visible without scrolling. */}
      <div className="detail-actions">
        {event.sourceUrl ? (
          <a className="primary-button" href={event.sourceUrl} target="_blank" rel="noopener noreferrer"
            aria-label={`Bilete / Vezi sursa${event.sourceName ? ` pe ${event.sourceName}` : ''} (filă nouă)`}>
            Bilete / Vezi sursa <span aria-hidden="true">↗</span>
          </a>
        ) : <p className="source-unavailable">Sursa originală nu este disponibilă.</p>}
      </div>
      {event.description && <p className="event-description">{event.description}</p>}
    </article>
  )
}
