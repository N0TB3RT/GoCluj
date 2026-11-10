import assert from 'node:assert/strict'
import test from 'node:test'
import { fetchEvents, normalizeEvents, safeSourceUrl } from '../src/api/events.js'
import { formatEventDate } from '../src/utils/eventDate.js'

const backendEvent = {
  id: 7, title: 'Concert din API', event_date: '2026-11-12T18:00:00Z',
  location_name: 'BT Arena', price_info: '50 RON', is_free: false,
  source_url: 'https://example.org/concert',
}
const response = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
})

test('requests configured GET /api/events and maps the current backend contract', async () => {
  const events = await fetchEvents({
    baseUrl: 'https://api.example.org/',
    fetchImpl: async (url, options) => {
      assert.equal(url, 'https://api.example.org/api/events')
      assert.equal(options.method, 'GET')
      assert.equal(options.headers.Accept, 'application/json')
      assert.equal(options.cache, 'no-store')
      return response([backendEvent])
    },
  })
  assert.deepEqual(events[0], {
    key: '7-0', title: 'Concert din API', date: backendEvent.event_date,
    venue: 'BT Arena', price: '50 RON', sourceUrl: backendEvent.source_url,
  })
})

test('empty API base uses the same-origin proxy and empty results remain empty', async () => {
  assert.deepEqual(await fetchEvents({ baseUrl: '', fetchImpl: async (url) => {
    assert.equal(url, '/api/events')
    return response([])
  } }), [])
})

test('supports requested aliases, numeric prices and explicit free admission', () => {
  const events = normalizeEvents([
    { title: 'A', start_time: '2026-11-12T18:00:00+02:00', venue: 'Sala A', price: 35 },
    { price: 0 }, { is_free: true, price_info: 'Informație veche' },
  ])
  assert.equal(events[0].date, '2026-11-12T18:00:00+02:00')
  assert.equal(events[0].venue, 'Sala A')
  assert.equal(events[0].price, '35 lei')
  assert.equal(events[1].price, 'Gratuit')
  assert.equal(events[2].price, 'Gratuit')
})

test('missing optional fields have honest fallbacks, not invented data', () => {
  const [event] = normalizeEvents([{ title: 'Eveniment', is_free: false }])
  assert.equal(event.price, 'Preț neprecizat')
  assert.equal(event.venue, 'Locație neprecizată')
  assert.equal(event.sourceUrl, null)
  assert.equal(formatEventDate(event.date), null)
})

test('source links allow only absolute HTTP(S) addresses', () => {
  for (const url of ['javascript:alert(1)', 'data:text/html,test', '/relative', '', null]) {
    assert.equal(safeSourceUrl(url), null)
  }
  assert.equal(safeSourceUrl('https://example.org/event'), 'https://example.org/event')
})

test('formats offsets in Bucharest and preserves date-only and naive source times', () => {
  assert.match(formatEventDate('2026-11-12T18:00:00Z'), /20:00/)
  assert.match(formatEventDate('2026-11-12T18:00:00'), /18:00/)
  assert.equal(formatEventDate('2026-11-12'), '12 noiembrie 2026')
  assert.equal(formatEventDate('not a date'), null)
})

test('rejects malformed payloads instead of pretending there are no events', async () => {
  for (const payload of [{ detail: 'error' }, null, [null], ['event']]) {
    await assert.rejects(fetchEvents({ fetchImpl: async () => response(payload) }), { code: 'invalid-response' })
  }
  await assert.rejects(fetchEvents({ fetchImpl: async () => new Response('<html>fallback</html>') }), { code: 'invalid-response' })
})

test('reports missing GET endpoint and server failure as HTTP errors', async () => {
  for (const status of [404, 405, 500, 503]) {
    await assert.rejects(fetchEvents({ fetchImpl: async () => response({}, status) }),
      (error) => error.code === 'http' && error.message.includes(String(status)))
  }
})

test('reports network failure and permits a subsequent retry', async () => {
  let calls = 0
  const fetchImpl = async () => {
    if (++calls === 1) throw new TypeError('Failed to fetch')
    return response([backendEvent])
  }
  await assert.rejects(fetchEvents({ fetchImpl }), { code: 'network' })
  assert.equal((await fetchEvents({ fetchImpl }))[0].title, backendEvent.title)
})

const pendingFetch = (_url, { signal }) => new Promise((_resolve, reject) => {
  const abort = () => reject(new DOMException('Aborted', 'AbortError'))
  if (signal.aborted) abort()
  else signal.addEventListener('abort', abort, { once: true })
})

test('a slow backend reaches an actionable timeout instead of loading forever', async () => {
  await assert.rejects(fetchEvents({ fetchImpl: pendingFetch, timeoutMs: 10 }), { code: 'timeout' })
})

test('supports cancelling in-flight requests without turning cancellation into a network error', async () => {
  const controller = new AbortController()
  const promise = fetchEvents({ fetchImpl: pendingFetch, signal: controller.signal })
  controller.abort()
  await assert.rejects(promise, { name: 'AbortError' })
})
