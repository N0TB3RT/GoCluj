import EventCard from './EventCard.jsx'
import LoadingScreen from './LoadingScreen.jsx'

export default function EventsList({ status, events, error, onRetry, hasMore = false, loadingMore = false, loadMoreError = null, onLoadMore }) {
  if (status === 'loading') return <LoadingScreen />
  if (status === 'error') return (
    <div className="empty-state" role="alert">
      <p className="eyebrow mb-3">Conexiune întreruptă</p>
      <h3 className="font-display text-2xl">Nu am putut încărca evenimentele.</h3>
      <p className="mt-3 text-[var(--muted)]">{error}</p>
      <button type="button" className="primary-button mt-6" onClick={onRetry}>Încearcă din nou</button>
    </div>
  )
  if (events.length === 0) return (
    <div className="empty-state" role="status">
      <p className="eyebrow mb-3">Agenda se pregătește</p>
      <h3 className="font-display text-2xl">Nu sunt evenimente disponibile momentan.</h3>
      <p className="mt-3 text-[var(--muted)]">Revino în curând sau actualizează lista.</p>
      <button type="button" className="primary-button mt-6" onClick={onRetry}>Actualizează lista</button>
    </div>
  )
  return (
    <>
      <div className="event-grid grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
        {events.map((event) => <EventCard key={event.key} event={event} />)}
      </div>
      {(hasMore || loadMoreError) && (
        <div className="load-more">
          {loadMoreError && <p className="load-more-error" role="alert">{loadMoreError}</p>}
          {hasMore && (
            <button type="button" className="secondary-button" onClick={onLoadMore} disabled={loadingMore} aria-busy={loadingMore}>
              {loadingMore ? 'Se încarcă…' : loadMoreError ? 'Încearcă din nou' : 'Încarcă mai multe'}
            </button>
          )}
        </div>
      )}
    </>
  )
}
