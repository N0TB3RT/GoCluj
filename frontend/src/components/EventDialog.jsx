import { useEffect, useRef } from 'react'

function formatDate(date) {
  return new Intl.DateTimeFormat('ro-RO', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date(`${date}T12:00:00`))
}

function EventDialog({ event, onClose }) {
  const dialogRef = useRef(null)
  const closeButtonRef = useRef(null)

  useEffect(() => {
    const previousActiveElement = document.activeElement
    const focusFrame = window.requestAnimationFrame(() => closeButtonRef.current?.focus())
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    function handleKeyDown(keyboardEvent) {
      if (keyboardEvent.key === 'Escape') {
        onClose()
        return
      }

      if (keyboardEvent.key !== 'Tab' || !dialogRef.current) return

      const focusableElements = dialogRef.current.querySelectorAll(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      if (keyboardEvent.shiftKey && document.activeElement === firstElement) {
        keyboardEvent.preventDefault()
        lastElement?.focus()
      } else if (!keyboardEvent.shiftKey && document.activeElement === lastElement) {
        keyboardEvent.preventDefault()
        firstElement?.focus()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      window.cancelAnimationFrame(focusFrame)
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = previousOverflow
      previousActiveElement?.focus()
    }
  }, [onClose])

  function handleBackdropMouseDown(mouseEvent) {
    if (mouseEvent.target === mouseEvent.currentTarget) onClose()
  }

  return (
    <div className="dialog-backdrop" onMouseDown={handleBackdropMouseDown}>
      <section
        ref={dialogRef}
        className="event-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="event-dialog-title"
        aria-describedby="event-dialog-description"
        tabIndex={-1}
      >
        <button ref={closeButtonRef} type="button" className="dialog-close" onClick={onClose} aria-label="Închide detaliile">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="m6 6 12 12M18 6 6 18" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
        </button>
        <img className="dialog-image" src={event.image} alt={event.imageAlt} />
        <div className="dialog-body">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="event-category">{event.category}</span>
            <span className="event-price">{event.price}</span>
          </div>
          <h2 id="event-dialog-title" className="mt-4 font-display text-3xl leading-tight sm:text-4xl">{event.title}</h2>
          <p id="event-dialog-description" className="mt-4 max-w-[62ch] text-[0.94rem] leading-7 text-[var(--muted)]">
            {event.description}
          </p>

          <dl className="mt-7 grid grid-cols-1 gap-x-8 gap-y-5 sm:grid-cols-2">
            <div className="dialog-detail">
              <dt>Data și ora</dt>
              <dd>{formatDate(event.date)} · {event.time}</dd>
            </div>
            <div className="dialog-detail">
              <dt>Locație</dt>
              <dd>{event.venue}, {event.neighborhood}</dd>
            </div>
            <div className="dialog-detail">
              <dt>Adresă</dt>
              <dd>{event.address}</dd>
            </div>
            <div className="dialog-detail">
              <dt>Acces</dt>
              <dd>{event.ticketInfo}</dd>
            </div>
          </dl>
          <p className="mt-7 border-t border-[var(--line)] pt-4 text-xs leading-5 text-[var(--muted)]">
            Acesta este un eveniment fictiv dintr-un program demonstrativ. Informațiile nu reprezintă o ofertă reală.
          </p>
        </div>
      </section>
    </div>
  )
}

export default EventDialog
