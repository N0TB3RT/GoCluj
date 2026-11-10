import { Link } from 'react-router-dom'
import { formatEventDateRange } from '../utils/eventDate.js'
import EventImage from './EventImage.jsx'

export default function EventCard({ event }) {
  const dateLabel = formatEventDateRange(event.startAt, event.endAt)
  return (
    <article className="event-card">
      <EventImage url={event.imageUrl} />
      <div className="event-card-body">
        <p className="eyebrow mb-4">{event.sourceName || 'Cluj-Napoca'}</p>
        <h3 className="font-display text-2xl leading-tight">
          {event.id == null ? event.title : <Link className="event-title-link" to={`/evenimente/${encodeURIComponent(event.id)}`}>{event.title}</Link>}
        </h3>
        <dl className="event-details">
          <div><dt>Data</dt><dd>{dateLabel ? <time dateTime={event.startAt}>{dateLabel}</time> : 'Data va fi anunțată'}</dd></div>
          <div><dt>Locație</dt><dd>{event.venueName}</dd></div>
          <div><dt>Preț</dt><dd>{event.price}</dd></div>
        </dl>
        {event.sourceUrl ? (
          <a className="event-source" href={event.sourceUrl} target="_blank" rel="noopener noreferrer" aria-label={`Vezi sursa originală: ${event.title} (filă nouă)`}>
            Vezi sursa originală <span aria-hidden="true">↗</span>
          </a>
        ) : <p className="source-unavailable">Sursa originală nu este disponibilă.</p>}
      </div>
    </article>
  )
}
