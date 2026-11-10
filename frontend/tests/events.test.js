import assert from 'node:assert/strict'
import test from 'node:test'
import {
  fetchEvent, fetchEvents, normalizeEvent, normalizeEventPage, safeImageUrl, safeSourceUrl,
} from '../src/api/events.js'
import { formatEventDate, formatEventDateRange } from '../src/utils/eventDate.js'

const backendEvent = {
  id: 12, source_name: 'LiveTickets', source_url: 'https://www.livetickets.ro/bilete/balul-1',
  title: 'Balul Dinților de Lapte', description: 'Line one\n\nLine two',
  start_at: '2026-11-12T21:00:00+02:00', end_at: '2026-11-13T05:00:00+02:00',
  venue: { name: 'MATTER', address: 'Str. Universității 3', city: 'Cluj-Napoca', lat: 46.768, lng: 23.59 },
  price_text: '30 - 35 RON', is_free: false, categories: [], source_category: 'divertisment',
  image_url: 'https://cdn.example/x/Background_MEDIUM.jpg',
}
const page = (items = [backendEvent], extra = {}) => ({ items, total: items.length, limit: 20, offset: 0, ...extra })
const response = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
})

test('requests GET /api/events with limit and offset and maps the page', async () => {
  const result = await fetchEvents({
    baseUrl: 'https://api.example.org/',
    limit: 10,
    offset: 30,
    fetchImpl: async (url, options) => {
      const parsed = new URL(url)
      assert.equal(parsed.origin + parsed.pathname, 'https://api.example.org/api/events')
      assert.equal(parsed.searchParams.get('limit'), '10')
      assert.equal(parsed.searchParams.get('offset'), '30')
      assert.equal(options.method, 'GET')
      assert.equal(options.headers.Accept, 'application/json')
      assert.equal(options.cache, 'no-store')
      return response(page([backendEvent], { total: 41, limit: 10, offset: 30 }))
    },
  })
  assert.equal(result.total, 41)
  assert.equal(result.limit, 10)
  assert.equal(result.offset, 30)
  assert.deepEqual(result.events[0], {
    id: 12, key: 'event-12', title: 'Balul Dinților de Lapte', description: 'Line one\n\nLine two',
    startAt: '2026-11-12T21:00:00+02:00', endAt: '2026-11-13T05:00:00+02:00',
    venueName: 'MATTER', venueAddress: 'Str. Universității 3', price: '30 - 35 RON',
    sourceName: 'LiveTickets', sourceUrl: backendEvent.source_url, imageUrl: backendEvent.image_url,
  })
})

test('default request asks for the first page and an empty list stays empty', async () => {
  const result = await fetchEvents({ baseUrl: '', fetchImpl: async (url) => {
    assert.equal(url, '/api/events?limit=20&offset=0')
    return response({ items: [], total: 0, limit: 20, offset: 0 })
  } })
  assert.deepEqual(result, { events: [], total: 0, limit: 20, offset: 0 })
})

test('null optional fields get honest fallbacks, not invented data', () => {
  const event = normalizeEvent({
    id: 3, title: 'Minimal', description: null, start_at: '2026-11-12T21:00:00+02:00', end_at: null,
    venue: { name: null, address: null, city: null, lat: null, lng: null },
    price_text: null, is_free: null, source_category: null, image_url: null, source_url: null, source_name: null,
  })
  assert.equal(event.description, null)
  assert.equal(event.endAt, null)
  assert.equal(event.venueName, 'Locație neprecizată')
  assert.equal(event.venueAddress, null)
  assert.equal(event.price, 'Preț neprecizat')
  assert.equal(event.imageUrl, null)
  assert.equal(event.sourceUrl, null)
  assert.equal(event.sourceName, null)
  assert.equal(normalizeEvent({ id: 4, title: 'No venue', venue: null }).venueName, 'Locație neprecizată')
})

test('price: only an explicit is_free true means Gratuit', () => {
  assert.equal(normalizeEvent({ id: 1, is_free: true, price_text: 'old' }).price, 'Gratuit')
  assert.equal(normalizeEvent({ id: 1, is_free: false, price_text: '50 RON' }).price, '50 RON')
  assert.equal(normalizeEvent({ id: 1, is_free: null, price_text: '50 RON' }).price, '50 RON')
  assert.equal(normalizeEvent({ id: 1, is_free: null, price_text: null }).price, 'Preț neprecizat')
  assert.equal(normalizeEvent({ id: 1, is_free: false }).price, 'Preț neprecizat')
})

test('source and image links allow only absolute HTTP(S) addresses', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,test', 'data:image/png;base64,AAAA', '/relative', '', null]) {
    assert.equal(safeSourceUrl(url), null)
    assert.equal(safeImageUrl(url), null)
  }
  assert.equal(safeSourceUrl('https://example.org/event'), 'https://example.org/event')
  assert.equal(safeImageUrl('http://cdn.example/a.jpg'), 'http://cdn.example/a.jpg')
  assert.equal(normalizeEvent({ id: 1, image_url: 'javascript:alert(1)' }).imageUrl, null)
})

test('formats offsets in Bucharest and preserves date-only and naive source times', () => {
  assert.match(formatEventDate('2026-11-12T18:00:00Z'), /20:00/)
  assert.match(formatEventDate('2026-11-12T18:00:00'), /18:00/)
  assert.equal(formatEventDate('2026-11-12'), '12 noiembrie 2026')
  assert.equal(formatEventDate('not a date'), null)
})

test('formats date ranges on one day and across days', () => {
  assert.equal(formatEventDateRange('2026-11-12T21:00:00+02:00', '2026-11-12T23:00:00+02:00'), '12 noiembrie 2026, 21:00 – 23:00')
  assert.equal(
    formatEventDateRange('2026-11-12T21:00:00+02:00', '2026-11-13T05:00:00+02:00'),
    '12 noiembrie 2026 la 21:00 – 13 noiembrie 2026 la 05:00',
  )
  assert.equal(formatEventDateRange('2026-11-12T19:00:00Z', '2026-11-12T21:00:00Z'), '12 noiembrie 2026, 21:00 – 23:00')
  assert.equal(formatEventDateRange('2026-11-12T21:00:00+02:00', null), formatEventDate('2026-11-12T21:00:00+02:00'))
  assert.equal(formatEventDateRange('2026-11-12T21:00:00+02:00', '2026-11-12T20:00:00+02:00'), formatEventDate('2026-11-12T21:00:00+02:00'))
  assert.equal(formatEventDateRange('', '2026-11-12T20:00:00+02:00'), null)
})

test('rejects malformed pages instead of pretending there are no events', async () => {
  for (const payload of [[], { detail: 'error' }, null, { items: 'x', total: 1 }, { items: [] }, { items: [null], total: 1 }, { items: ['event'], total: 1 }]) {
    await assert.rejects(fetchEvents({ fetchImpl: async () => response(payload) }), { code: 'invalid-response' })
  }
  assert.throws(() => normalizeEventPage({ items: [], total: '3' }), { code: 'invalid-response' })
  await assert.rejects(fetchEvents({ fetchImpl: async () => new Response('<html>fallback</html>') }), { code: 'invalid-response' })
})

test('reports server failure as an HTTP error, including 404 on the list', async () => {
  for (const status of [404, 405, 500, 503]) {
    await assert.rejects(fetchEvents({ fetchImpl: async () => response({}, status) }),
      (error) => error.code === 'http' && error.message.includes(String(status)))
  }
})

test('fetchEvent requests /api/events/{id} and normalizes one event', async () => {
  const event = await fetchEvent(12, { baseUrl: 'https://api.example.org', fetchImpl: async (url) => {
    assert.equal(url, 'https://api.example.org/api/events/12')
    return response(backendEvent)
  } })
  assert.equal(event.id, 12)
  assert.equal(event.title, 'Balul Dinților de Lapte')
})

test('fetchEvent reports 404 with a distinct code and other failures as http', async () => {
  await assert.rejects(fetchEvent(99, { fetchImpl: async () => response({ detail: 'Event not found' }, 404) }),
    { code: 'not-found', message: 'Evenimentul nu a fost găsit.' })
  await assert.rejects(fetchEvent(99, { fetchImpl: async () => response({}, 500) }), { code: 'http' })
  await assert.rejects(fetchEvent(99, { fetchImpl: async () => response([1]) }), { code: 'invalid-response' })
})

test('fetchEvent escapes the id in the path', async () => {
  await fetchEvent('a/b', { fetchImpl: async (url) => {
    assert.equal(url, '/api/events/a%2Fb')
    return response(backendEvent)
  } })
})

test('reports network failure and permits a subsequent retry', async () => {
  let calls = 0
  const fetchImpl = async () => {
    if (++calls === 1) throw new TypeError('Failed to fetch')
    return response(page())
  }
  await assert.rejects(fetchEvents({ fetchImpl }), { code: 'network' })
  assert.equal((await fetchEvents({ fetchImpl })).events[0].title, backendEvent.title)
})

const pendingFetch = (_url, { signal }) => new Promise((_resolve, reject) => {
  const abort = () => reject(new DOMException('Aborted', 'AbortError'))
  if (signal.aborted) abort()
  else signal.addEventListener('abort', abort, { once: true })
})

test('a slow backend reaches an actionable timeout instead of loading forever', async () => {
  await assert.rejects(fetchEvents({ fetchImpl: pendingFetch, timeoutMs: 10 }), { code: 'timeout' })
  await assert.rejects(fetchEvent(1, { fetchImpl: pendingFetch, timeoutMs: 10 }), { code: 'timeout' })
})

test('supports cancelling in-flight requests without turning cancellation into a network error', async () => {
  const controller = new AbortController()
  const promise = fetchEvents({ fetchImpl: pendingFetch, signal: controller.signal })
  controller.abort()
  await assert.rejects(promise, { name: 'AbortError' })
})
