import { useState } from 'react'

// 16:9 event picture. Falls back to a branded placeholder when there is no URL or the image fails to load.
export default function EventImage({ url, className = '', eager = false }) {
  const [failed, setFailed] = useState(false)
  if (!url || failed) {
    return (
      <div className={`event-media event-media-placeholder ${className}`} data-placeholder="true">
        <img src="/images/gocluj-white.svg" alt="" width="165" height="44" aria-hidden="true" />
      </div>
    )
  }
  return (
    <div className={`event-media ${className}`}>
      <img
        src={url}
        alt=""
        width="800"
        height="450"
        loading={eager ? 'eager' : 'lazy'}
        decoding="async"
        referrerPolicy="no-referrer"
        onError={() => setFailed(true)}
      />
    </div>
  )
}
