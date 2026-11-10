import { formatEventDate } from '../utils/eventDate.js'

export default function EventCard({ event }) {
  const dateLabel = formatEventDate(event.date)
  return (
    <article className="event-card">
      <p className="eyebrow mb-4">Cluj-Napoca</p>
      <h3 className="font-display text-2xl leading-tight">{event.title}</h3>
      <dl className="event-details">
        <div><dt>Data</dt><dd>{dateLabel ? <time dateTime={event.date}>{dateLabel}</time> : 'Data va fi anunțată'}</dd></div>
        <div><dt>Locație</dt><dd>{event.venue}</dd></div>
        <div><dt>Preț</dt><dd>{event.price}</dd></div>
      </dl>
      {event.sourceUrl ? (
        <a className="event-source" href={event.sourceUrl} target="_blank" rel="noopener noreferrer" aria-label={`Vezi sursa originală: ${event.title} (filă nouă)`}>
          Vezi sursa originală <span aria-hidden="true">↗</span>
        </a>
      ) : <p className="source-unavailable">Sursa originală nu este disponibilă.</p>}
    </article>
  )
}
