import { useEffect } from 'react'
import { useParams } from 'react-router-dom'
import EventDetail from './components/EventDetail.jsx'
import SiteFooter from './components/SiteFooter.jsx'
import SiteHeader from './components/SiteHeader.jsx'
import useEvent from './hooks/useEvent.js'
import './site.css'

function EventDetailContent({ id }) {
  const { status, event, error, reload } = useEvent(id)
  const title = event?.title

  useEffect(() => {
    if (!title) return undefined
    const previous = document.title
    document.title = title
    return () => { document.title = previous }
  }, [title])

  return (
    <div id="top" className="min-h-screen bg-[var(--page-bg)] text-[var(--ink)]">
      <a href="#continut" className="skip-link">Sari la conținut</a>
      <SiteHeader />
      <main id="continut" tabIndex={-1} className="detail-shell mx-auto w-full max-w-[960px] px-5 pb-20 sm:px-8">
        <EventDetail status={status} event={event} error={error} onRetry={reload} />
      </main>
      <SiteFooter />
    </div>
  )
}

export default function EventDetailPage() {
  const { id } = useParams()
  return <EventDetailContent key={id} id={id} />
}
