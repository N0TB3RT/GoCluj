function formatDate(date) {
  const formatted = new Intl.DateTimeFormat('ro-RO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  }).format(new Date(`${date}T12:00:00`))

  return formatted.charAt(0).toLocaleUpperCase('ro-RO') + formatted.slice(1)
}

function EventCard({ event, onOpen }) {
  return (
    <article className="event-card">
      <button type="button" className="event-image-button" onClick={onOpen} aria-label={`Vezi detalii: ${event.title}`}>
        <img className="event-image" src={event.image} alt={event.imageAlt} loading="lazy" />
      </button>
      <div className="flex items-start justify-between gap-3 pt-4">
        <span className="event-category">{event.category}</span>
        <span className="event-price">{event.price}</span>
      </div>
      <h3 className="mb-2 mt-3">
        <button type="button" className="event-title-button" onClick={onOpen}>{event.title}</button>
      </h3>
      <div className="event-meta">
        <time dateTime={`${event.date}T${event.time}`}>{formatDate(event.date)} · {event.time}</time>
        <span aria-hidden="true">·</span>
        <span>{event.venue}</span>
      </div>
    </article>
  )
}

export default EventCard
