import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import EventsList from './components/EventsList.jsx'
import SiteFooter from './components/SiteFooter.jsx'
import SiteHeader from './components/SiteHeader.jsx'
import useEvents from './hooks/useEvents.js'
import './site.css'

function GoClujApp() {
  const { status, events, total, error, reload, hasMore, loadMore, loadingMore, loadMoreError } = useEvents()
  const loading = status === 'loading'
  const { hash } = useLocation()

  // Arriving from another route (e.g. the detail page) does not scroll to the hash by itself.
  useEffect(() => {
    if (hash) document.getElementById(hash.slice(1))?.scrollIntoView()
  }, [hash])

  function refreshEvents() {
    reload()
    window.location.hash = 'evenimente'
    document.getElementById('evenimente')?.scrollIntoView()
  }

  return (
    <div id="top" className="min-h-screen bg-[var(--page-bg)] text-[var(--ink)]">
      <a href="#evenimente" className="skip-link">Sari la evenimente</a>
      <SiteHeader onRefresh={refreshEvents} loading={loading} />
      <main>
        <section className="intro-shell" aria-labelledby="intro-heading">
          <img className="hero-image" src="/images/cluj-sunset.jpg" alt="" fetchPriority="high" width="1920" height="1275" />
          <div className="hero-content mx-auto w-full max-w-[1240px] px-5 sm:px-8">
            <p className="eyebrow mb-6"><span className="live-dot" /> Cluj-Napoca · O agendă locală, în ritmul tău</p>
            <h1 id="intro-heading" className="intro-title font-display">
              Descoperă ce se<br className="hidden sm:block" /> întâmplă <em>în Cluj.</em>
            </h1>
            <p className="hero-description mt-6 max-w-[510px] text-base leading-7 sm:text-lg">
              Idei pentru serile libere și weekendurile petrecute prin oraș, de la concerte la întâlniri de cartier.
            </p>
            <div className="hero-actions">
              <a href="#evenimente" className="primary-button">Explorează evenimentele <span aria-hidden="true">↗</span></a>
              <a href="#despre" className="secondary-button">Despre GoCluj <span aria-hidden="true">→</span></a>
            </div>
            <div className="hero-caption"><span className="caption-line" /> Orașul tău. Următoarea poveste.</div>
          </div>
        </section>

        <section id="evenimente" tabIndex={-1} aria-labelledby="events-heading" className="events-section mx-auto w-full max-w-[1240px] px-5 pb-20 sm:px-8 md:pb-24">
          <div className="section-heading flex flex-col gap-3 py-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="eyebrow mb-2">Agenda orașului</p>
              <h2 id="events-heading" className="font-display text-3xl leading-tight sm:text-[2.4rem]">Evenimente în Cluj</h2>
            </div>
            <p className="text-sm text-[var(--muted)]" aria-live="polite">
              {status === 'success' ? `${total} ${total === 1 ? 'eveniment' : 'evenimente'} în listă` : ''}
            </p>
          </div>
          <EventsList status={status} events={events} error={error} onRetry={reload}
            hasMore={hasMore} loadingMore={loadingMore} loadMoreError={loadMoreError} onLoadMore={loadMore} />
        </section>
      </main>
      <SiteFooter />
    </div>
  )
}

export default GoClujApp
