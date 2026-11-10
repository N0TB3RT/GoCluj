import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { MemoryRouter } from 'react-router-dom'
import { createServer } from 'vite'
import { normalizeEvent } from '../src/api/events.js'

let server
let EventsList
let EventDetail
before(async () => {
  server = await createServer({ server: { middlewareMode: true, watch: null, hmr: false }, appType: 'custom' })
  EventsList = (await server.ssrLoadModule('/src/components/EventsList.jsx')).default
  EventDetail = (await server.ssrLoadModule('/src/components/EventDetail.jsx')).default
})
after(async () => { await server?.close() })

const inRouter = (element) => renderToStaticMarkup(createElement(MemoryRouter, null, element))
const render = (props) => inRouter(createElement(EventsList, { events: [], onRetry() {}, ...props }))
const renderDetail = (props) => inRouter(createElement(EventDetail, { onRetry() {}, ...props }))
const rawEvent = {
  id: 12, source_name: 'LiveTickets', source_url: 'https://www.livetickets.ro/bilete/x', title: 'Balul',
  description: 'Line one\n\nLine two', start_at: '2026-11-12T21:00:00+02:00', end_at: '2026-11-13T05:00:00+02:00',
  venue: { name: 'MATTER', address: 'Str. Universității 3' }, price_text: '30 - 35 RON', is_free: false,
  image_url: 'https://cdn.example/x.jpg',
}
const events = (overrides = {}) => [normalizeEvent({ ...rawEvent, ...overrides })]

test('loading is visible while awaiting events', () => {
  const html = render({ status: 'loading' })
  assert.match(html, /role="status"/)
  assert.match(html, /Se încarcă evenimentele/)
  assert.doesNotMatch(html, /Nu sunt evenimente/)
})

test('error state explains the failure and exposes retry', () => {
  const html = render({ status: 'error', error: 'HTTP 405' })
  assert.match(html, /role="alert"/)
  assert.match(html, /HTTP 405/)
  assert.match(html, /Încearcă din nou/)
})

test('successful empty response gets a separate empty state', () => {
  assert.match(render({ status: 'success' }), /Nu sunt evenimente disponibile/)
})

test('card renders the required fields, source label, date range and detail link', () => {
  const html = render({ status: 'success', events: events() })
  for (const expected of [
    'Balul', '12 noiembrie 2026 la 21:00 – 13 noiembrie 2026 la 05:00', 'MATTER', '30 - 35 RON',
    'LiveTickets', 'href="/evenimente/12"', 'href="https://www.livetickets.ro/bilete/x"', 'rel="noopener noreferrer"',
  ]) {
    assert.ok(html.includes(expected), expected)
  }
})

test('card renders a lazy image when there is a url and a placeholder when there is not', () => {
  const withImage = render({ status: 'success', events: events() })
  assert.match(withImage, /<img src="https:\/\/cdn\.example\/x\.jpg"/)
  for (const attribute of ['loading="lazy"', 'decoding="async"', 'width="800"', 'height="450"', 'alt=""', 'referrerPolicy="no-referrer"']) {
    assert.ok(withImage.includes(attribute), attribute)
  }
  assert.doesNotMatch(withImage, /data-placeholder/)

  const without = render({ status: 'success', events: events({ image_url: null }) })
  assert.match(without, /data-placeholder="true"/)
  assert.match(without, /gocluj-white\.svg/)
  assert.doesNotMatch(without, /cdn\.example/)
})

test('card falls back to Cluj-Napoca without a source name and omits the link without an id', () => {
  const html = render({ status: 'success', events: events({ source_name: null, id: null }) })
  assert.match(html, /Cluj-Napoca/)
  assert.doesNotMatch(html, /href="\/evenimente/)
})

test('load more button appears only while more events exist and shows a loading state', () => {
  assert.doesNotMatch(render({ status: 'success', events: events(), hasMore: false }), /Încarcă mai multe/)
  assert.match(render({ status: 'success', events: events(), hasMore: true }), /Încarcă mai multe/)
  const loading = render({ status: 'success', events: events(), hasMore: true, loadingMore: true })
  assert.match(loading, /disabled/)
  assert.match(loading, /Se încarcă…/)
})

test('incomplete records render gracefully and untrusted titles stay text', () => {
  const html = render({ status: 'success', events: [normalizeEvent({ id: 1, title: '<script>alert(1)</script>', source_url: 'javascript:alert(1)' })] })
  assert.match(html, /Data va fi anunțată/)
  assert.match(html, /Locație neprecizată/)
  assert.match(html, /Preț neprecizat/)
  assert.match(html, /Sursa originală nu este disponibilă/)
  assert.doesNotMatch(html, /<script>|href="javascript:/)
})

test('detail page shows all fields, the ticket button and a back link', () => {
  const html = renderDetail({ status: 'success', event: events()[0] })
  for (const expected of [
    '← Înapoi la evenimente', 'Balul', '12 noiembrie 2026 la 21:00 – 13 noiembrie 2026 la 05:00', 'MATTER',
    'Str. Universității 3', '30 - 35 RON', 'LiveTickets', 'Bilete / Vezi sursa', 'target="_blank"',
    'rel="noopener noreferrer"', 'filă nouă', 'href="https://www.livetickets.ro/bilete/x"', 'Line one\n\nLine two',
  ]) {
    assert.ok(html.includes(expected), expected)
  }
})

test('detail description is escaped text, never HTML', () => {
  const html = renderDetail({ status: 'success', event: events({ description: 'Hi <script>alert(1)</script> <b>x</b>' })[0] })
  assert.doesNotMatch(html, /<script>|<b>/)
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/)
})

test('detail page has loading, error with retry and 404 states', () => {
  assert.match(renderDetail({ status: 'loading' }), /Se încarcă evenimentele/)
  const error = renderDetail({ status: 'error', error: 'HTTP 500' })
  assert.match(error, /role="alert"/)
  assert.match(error, /HTTP 500/)
  assert.match(error, /Încearcă din nou/)
  const missing = renderDetail({ status: 'not-found' })
  assert.match(missing, /Evenimentul nu a fost găsit\./)
  assert.match(missing, /href="\/#evenimente"/)
})
