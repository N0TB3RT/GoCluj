import { useMemo, useState } from 'react'
import { events } from './data/events.js'
import EventCard from './components/EventCard.jsx'
import EventDialog from './components/EventDialog.jsx'
import SiteFooter from './components/SiteFooter.jsx'
import SiteHeader from './components/SiteHeader.jsx'
import './site.css'

const categories = ['Muzică', 'Artă', 'Teatru', 'Tehnologie', 'Sport', 'Comunitate']

function matchesDate(eventDate, dateFilter) {
  if (dateFilter === 'week') return eventDate >= '2026-11-09' && eventDate <= '2026-11-15'
  if (dateFilter === 'weekend') return eventDate >= '2026-11-14' && eventDate <= '2026-11-15'
  if (dateFilter === 'month') return eventDate.startsWith('2026-11')
  return true
}

function GoClujApp() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('')
  const [dateFilter, setDateFilter] = useState('')
  const [freeOnly, setFreeOnly] = useState(false)
  const [selectedEvent, setSelectedEvent] = useState(null)

  const filteredEvents = useMemo(() => {
    const query = search.trim().toLocaleLowerCase('ro-RO')

    return events
      .filter((event) => {
        const searchableText = `${event.title} ${event.venue} ${event.neighborhood} ${event.category}`
          .toLocaleLowerCase('ro-RO')

        return (
          (!query || searchableText.includes(query)) &&
          (!category || event.category === category) &&
          matchesDate(event.date, dateFilter) &&
          (!freeOnly || event.isFree)
        )
      })
      .sort((first, second) => first.date.localeCompare(second.date))
  }, [search, category, dateFilter, freeOnly])

  const hasFilters = Boolean(search || category || dateFilter || freeOnly)

  function resetFilters() {
    setSearch('')
    setCategory('')
    setDateFilter('')
    setFreeOnly(false)
  }

  return (
    <div id="top" className="min-h-screen bg-[var(--page-bg)] text-[var(--ink)]">
      <SiteHeader />
      <main>
        <section className="intro-shell mx-auto grid w-full max-w-[1240px] grid-cols-1 items-end gap-8 px-5 pb-12 pt-14 sm:px-8 md:grid-cols-[minmax(0,1.35fr)_minmax(230px,0.65fr)] md:gap-12 md:pb-16 md:pt-20">
          <div>
            <p className="eyebrow mb-5">O agendă locală, în ritmul tău</p>
            <h1 className="intro-title max-w-[760px] font-display text-[2.65rem] leading-[1.05] sm:text-5xl md:text-[3.55rem]">
              Descoperă ce se întâmplă în Cluj
            </h1>
            <p className="mt-5 max-w-[560px] text-base leading-7 text-[var(--muted)] sm:text-lg">
              Idei pentru serile libere și weekendurile petrecute prin oraș, de la concerte la întâlniri de cartier.
            </p>
          </div>
          <aside className="demo-note md:mb-1" aria-label="Notă despre programul demonstrativ">
            <span className="demo-note-mark" aria-hidden="true">i</span>
            <p>Program demonstrativ. Evenimentele și detaliile de mai jos sunt fictive, create pentru această pagină.</p>
          </aside>
        </section>

        <section id="evenimente" className="mx-auto w-full max-w-[1240px] scroll-mt-8 px-5 pb-20 sm:px-8 md:pb-24">
          <div className="section-heading flex flex-col gap-3 border-t border-[var(--line)] py-6 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <p className="eyebrow mb-2">Calendar demonstrativ</p>
              <h2 className="font-display text-3xl leading-tight sm:text-[2rem]">Următoarele ieșiri</h2>
            </div>
            <p className="text-sm text-[var(--muted)]" aria-live="polite">
              {filteredEvents.length} {filteredEvents.length === 1 ? 'eveniment' : 'evenimente'} în listă
            </p>
          </div>

          <div className="filters mb-8 grid gap-3 rounded-sm border border-[var(--line)] bg-white p-4 md:grid-cols-[minmax(220px,1.5fr)_repeat(2,minmax(160px,0.8fr))_auto_auto] md:items-center md:gap-3 md:p-4">
            <label className="search-field">
              <span className="sr-only">Caută după eveniment sau loc</span>
              <svg aria-hidden="true" viewBox="0 0 24 24" className="search-icon" fill="none">
                <circle cx="10.8" cy="10.8" r="6.8" stroke="currentColor" strokeWidth="1.7" />
                <path d="m16 16 4.2 4.2" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
              </svg>
              <input
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Caută un eveniment sau un loc"
              />
            </label>

            <label className="filter-select">
              <span className="sr-only">Filtrează după categorie</span>
              <select value={category} onChange={(event) => setCategory(event.target.value)}>
                <option value="">Toate categoriile</option>
                {categories.map((item) => <option key={item} value={item}>{item}</option>)}
              </select>
            </label>

            <label className="filter-select">
              <span className="sr-only">Filtrează după dată</span>
              <select value={dateFilter} onChange={(event) => setDateFilter(event.target.value)}>
                <option value="">Oricând</option>
                <option value="week">9–15 noiembrie</option>
                <option value="weekend">Weekendul acesta</option>
                <option value="month">Noiembrie 2026</option>
              </select>
            </label>

            <label className="free-filter">
              <input type="checkbox" checked={freeOnly} onChange={(event) => setFreeOnly(event.target.checked)} />
              <span className="free-toggle" aria-hidden="true"><span /></span>
              <span>Doar gratuite</span>
            </label>

            <button type="button" className="reset-button" onClick={resetFilters} disabled={!hasFilters}>
              Resetează
            </button>
          </div>

          {filteredEvents.length > 0 ? (
            <div className="event-grid grid grid-cols-1 gap-x-5 gap-y-9 sm:grid-cols-2 lg:grid-cols-3 lg:gap-x-6 lg:gap-y-11">
              {filteredEvents.map((event) => (
                <EventCard key={event.id} event={event} onOpen={() => setSelectedEvent(event)} />
              ))}
            </div>
          ) : (
            <div className="empty-state" role="status">
              <p className="eyebrow mb-3">Niciun rezultat</p>
              <h3 className="font-display text-2xl">Nu am găsit ceva pe măsura căutării.</h3>
              <p className="mt-2 text-[var(--muted)]">Încearcă alt termen sau elimină unul dintre filtre.</p>
              <button type="button" className="primary-button mt-6" onClick={resetFilters}>Resetează filtrele</button>
            </div>
          )}
        </section>
      </main>
      <SiteFooter />
      {selectedEvent && <EventDialog event={selectedEvent} onClose={() => setSelectedEvent(null)} />}
    </div>
  )
}

export default GoClujApp
