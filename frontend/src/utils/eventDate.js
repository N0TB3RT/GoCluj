export function formatEventDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}(?:$|T)/.test(value)) return null
  const hasTime = value.includes('T')
  const hasZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  // A timestamp without an offset is kept as the source's wall-clock time.
  const date = new Date(hasTime && !hasZone ? `${value}Z` : value)
  if (Number.isNaN(date.getTime())) return null
  return new Intl.DateTimeFormat('ro-RO', {
    timeZone: hasZone ? 'Europe/Bucharest' : 'UTC',
    day: 'numeric', month: 'long', year: 'numeric',
    ...(hasTime ? { hour: '2-digit', minute: '2-digit' } : {}),
  }).format(date)
}
