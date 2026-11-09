import assert from 'node:assert/strict'
import { after, before, test } from 'node:test'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { createServer } from 'vite'
import { normalizeEvents } from '../src/api/events.js'

let server
let EventsList
before(async () => {
  server = await createServer({ server: { middlewareMode: true, watch: null, hmr: false }, appType: 'custom' })
  EventsList = (await server.ssrLoadModule('/src/components/EventsList.jsx')).default
})
after(async () => { await server?.close() })
const render = (props) => renderToStaticMarkup(createElement(EventsList, { events: [], onRetry() {}, ...props }))

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

test('API events render all five required fields and a safe source link', () => {
  const html = render({ status: 'success', events: normalizeEvents([{
    title: 'Titlu primit din backend', event_date: '2026-11-12T18:00:00Z',
    location_name: 'Locație din API', is_free: true, source_url: 'https://example.org/event',
  }]) })
  for (const expected of ['Titlu primit din backend', '12 noiembrie 2026', '20:00', 'Locație din API', 'Gratuit', 'href="https://example.org/event"', 'rel="noopener noreferrer"']) {
    assert.ok(html.includes(expected), expected)
  }
})

test('incomplete records render gracefully and untrusted titles stay text', () => {
  const html = render({ status: 'success', events: normalizeEvents([{ title: '<script>alert(1)</script>', source_url: 'javascript:alert(1)' }]) })
  assert.match(html, /Data va fi anunțată/)
  assert.match(html, /Locație neprecizată/)
  assert.match(html, /Preț neprecizat/)
  assert.match(html, /Sursa originală nu este disponibilă/)
  assert.doesNotMatch(html, /<script>|href="javascript:/)
})
