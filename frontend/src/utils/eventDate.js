const TIME_ZONE = 'Europe/Bucharest'

function parseEventDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:$|T)/.test(value)) return null
  const hasTime = value.includes('T')
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  // A timestamp without an offset is kept as the source's wall-clock time.
  const date = new Date(hasTime && !hasZone ? `${value}Z` : value)
  if (Number.isNaN(date.getTime())) return null
  return { date, hasTime, timeZone: hasZone ? TIME_ZONE : 'UTC' }
}

const format = ({ date, timeZone }, options) => new Intl.DateTimeFormat('ro-RO', { timeZone, ...options }).format(date)
const formatDay = (parsed) => format(parsed, { day: 'numeric', month: 'long', year: 'numeric' })
const formatTime = (parsed) => format(parsed, { hour: '2-digit', minute: '2-digit' })

export function formatEventDate(value) {
  const parsed = parseEventDate(value)
  if (!parsed) return null
  return format(parsed, {
    day: 'numeric', month: 'long', year: 'numeric',
    ...(parsed.hasTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  })
}

export function formatEventDateRange(start, end) {
  const from = parseEventDate(start)
  if (!from) return null
  const to = parseEventDate(end)
  if (!to || to.date <= from.date) return formatEventDate(start)
  const fromDay = formatDay(from)
  const toDay = formatDay(to)
  if (!from.hasTime || !to.hasTime) return fromDay === toDay ? fromDay : `${fromDay} – ${toDay}`
  if (fromDay === toDay) return `${fromDay}, ${formatTime(from)} – ${formatTime(to)}`
  return `${fromDay} la ${formatTime(from)} – ${toDay} la ${formatTime(to)}`
}
