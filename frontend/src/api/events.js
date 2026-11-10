export class EventsApiError extends Error {
  constructor(message, code) {
    super(message)
    this.name = 'EventsApiError'
    this.code = code
  }
}

export const DEFAULT_PAGE_SIZE = 20

function text(value) {
  return typeof value === 'string' ? value.trim() : ''
}

function isObject(value) {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value)
}

function safeHttpUrl(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

export const safeSourceUrl = safeHttpUrl
export const safeImageUrl = safeHttpUrl

function invalidResponse(message = 'Lista de evenimente primită nu are formatul așteptat.') {
  return new EventsApiError(message, 'invalid-response')
}

export function normalizeEvent(raw) {
  if (!isObject(raw)) throw invalidResponse('Evenimentul primit nu are formatul așteptat.')
  const venue = isObject(raw.venue) ? raw.venue : {}
  const id = raw.id ?? null
  return {
    id,
    key: `event-${id ?? raw.source_url ?? text(raw.title)}`,
    title: text(raw.title) || 'Eveniment fără titlu',
    description: text(raw.description) || null,
    startAt: text(raw.start_at),
    endAt: text(raw.end_at) || null,
    venueName: text(venue.name) || 'Locație neprecizată',
    venueAddress: text(venue.address) || null,
    // Free admission is never assumed: only an explicit is_free === true counts.
    price: raw.is_free === true ? 'Gratuit' : text(raw.price_text) || 'Preț neprecizat',
    sourceName: text(raw.source_name) || null,
    sourceUrl: safeSourceUrl(raw.source_url),
    imageUrl: safeImageUrl(raw.image_url),
  }
}

export function normalizeEventPage(payload) {
  if (!isObject(payload) || !Array.isArray(payload.items)
    || typeof payload.total !== 'number' || !Number.isFinite(payload.total)) {
    throw invalidResponse()
  }
  return {
    events: payload.items.map(normalizeEvent),
    total: payload.total,
    limit: Number.isFinite(payload.limit) ? payload.limit : null,
    offset: Number.isFinite(payload.offset) ? payload.offset : null,
  }
}

async function request(path, {
  baseUrl = import.meta.env?.VITE_API_URL ?? '',
  signal,
  timeoutMs = 15000,
  fetchImpl = globalThis.fetch,
  notFoundCode,
} = {}) {
  const base = baseUrl.trim().replace(/\/+$/, '')
  if (base && !/^https?:\/\//i.test(base) && !/^\/(?!\/)/.test(base)) {
    throw new EventsApiError('Adresa serviciului de evenimente nu este configurată corect.', 'configuration')
  }
  const controller = new AbortController()
  const abort = () => controller.abort()
  if (signal?.aborted) controller.abort()
  signal?.addEventListener('abort', abort, { once: true })
  let timedOut = false
  const timeout = setTimeout(() => { timedOut = true; controller.abort() }, timeoutMs)

  try {
    const response = await fetchImpl(`${base}${path}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
      cache: 'no-store',
    })
    if (notFoundCode && response.status === 404) {
      throw new EventsApiError('Evenimentul nu a fost găsit.', notFoundCode)
    }
    if (!response.ok) {
      throw new EventsApiError(`Serviciul de evenimente a răspuns cu o eroare (HTTP ${response.status}).`, 'http')
    }
    try {
      return await response.json()
    } catch (error) {
      if (controller.signal.aborted) throw error
      throw invalidResponse('Serviciul de evenimente a trimis un răspuns care nu poate fi citit.')
    }
  } catch (error) {
    if (signal?.aborted) throw error
    if (timedOut) throw new EventsApiError('Serviciul de evenimente răspunde prea greu. Încearcă din nou.', 'timeout')
    if (error instanceof EventsApiError) throw error
    throw new EventsApiError('Nu putem contacta serviciul de evenimente. Verifică conexiunea și încearcă din nou.', 'network')
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', abort)
  }
}

export async function fetchEvents({ limit = DEFAULT_PAGE_SIZE, offset = 0, ...options } = {}) {
  const query = new URLSearchParams({ limit: String(limit), offset: String(offset) })
  const page = normalizeEventPage(await request(`/api/events?${query}`, options))
  return { ...page, limit: page.limit ?? limit, offset: page.offset ?? offset }
}

export async function fetchEvent(id, options = {}) {
  const payload = await request(`/api/events/${encodeURIComponent(id)}`, { ...options, notFoundCode: 'not-found' })
  return normalizeEvent(payload)
}
