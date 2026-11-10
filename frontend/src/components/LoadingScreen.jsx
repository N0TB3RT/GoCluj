export default function LoadingScreen() {
  return (
    <div className="loading-screen" role="status" aria-live="polite">
      <div className="loading-brand" aria-hidden="true">
        <span className="loading-orbit" />
        <img src="/images/gocluj-white.svg" width="220" height="59" alt="" />
      </div>
      <p>Se încarcă evenimentele…</p>
      <span className="loading-track" aria-hidden="true"><span /></span>
    </div>
  )
}
