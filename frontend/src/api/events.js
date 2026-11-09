export class EventsApiError extends Error {
  constructor(message, code) {
    super(message)
    this.name = 'EventsApiError'
    this.code = code
  }
}

function text(value) {
  return typeof value === 'string' ? value.trim() : ''
}

export function safeSourceUrl(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) ? url.href : null
  } catch {
    return null
  }
}

export function normalizeEvents(payload) {
  if (!Array.isArray(payload) || payload.some((event) => !event || typeof event !== 'object' || Array.isArray(event))) {
    throw new EventsApiError('Lista de evenimente primită nu are formatul așteptat.', 'invalid-response')
  }
  return payload.map((event, index) => ({
    key: `${event.id ?? event.source_url ?? 'event'}-${index}`,
    title: text(event.title) || 'Eveniment fără titlu',
    date: text(event.start_time) || text(event.event_date),
    venue: text(event.venue) || text(event.location_name) || 'Locație neprecizată',
    price: event.is_free === true || event.price === 0
      ? 'Gratuit'
      : text(event.price_info) || text(event.price) || (typeof event.price === 'number' && Number.isFinite(event.price)
        ? `${event.price} lei` : 'Preț neprecizat'),
    sourceUrl: safeSourceUrl(event.source_url),
  }))
}

export async function fetchEvents({
  baseUrl = import.meta.env?.VITE_API_URL ?? '',
  signal,
  timeoutMs = 15000,
  fetchImpl = globalThis.fetch,
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
    const response = await fetchImpl(`${base}/api/events`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
      cache: 'no-store',
    })
    if (!response.ok) {
      throw new EventsApiError(`Serviciul de evenimente a răspuns cu o eroare (HTTP ${response.status}).`, 'http')
    }
    let payload
    try {
      payload = await response.json()
    } catch (error) {
      if (controller.signal.aborted) throw error
      throw new EventsApiError('Serviciul de evenimente a trimis un răspuns care nu poate fi citit.', 'invalid-response')
    }
    return normalizeEvents(payload)
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
