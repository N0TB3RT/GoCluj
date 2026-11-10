import { useState } from 'react'

// 16:9 event picture. The whole image is shown (object-fit: contain) over a blurred, decorative copy of
// itself that fills the letterbox, so portrait posters are not cropped. Both use the same src, so the
// browser downloads it once. If `url` fails to load, `fallbackUrl` is tried next; when there is no URL left,
// a branded placeholder is shown.
export default function EventImage({ url, fallbackUrl = null, className = '', eager = false }) {
  const [failures, setFailures] = useState(0)
  const candidates = [...new Set([url, fallbackUrl].filter(Boolean))]
  const src = candidates[failures]
  if (!src) {
    return (
      <div className={`event-media event-media-placeholder ${className}`} data-placeholder="true">
        <img src="/images/gocluj-white.svg" alt="" width="165" height="44" aria-hidden="true" />
      </div>
    )
  }
  const loading = eager ? 'eager' : 'lazy'
  return (
    <div className={`event-media ${className}`}>
      <img
        className="event-media-backdrop"
        src={src}
        alt=""
        aria-hidden="true"
        loading={loading}
        decoding="async"
        referrerPolicy="no-referrer"
      />
      <img
        src={src}
        alt=""
        loading={loading}
        decoding="async"
        referrerPolicy="no-referrer"
        onError={() => setFailures((n) => n + 1)}
      />
    </div>
  )
}
