function SiteFooter() {
  return (
    <footer id="despre" className="site-footer" aria-labelledby="about-heading">
      <div className="about-content mx-auto w-full max-w-[1240px] px-5 sm:px-8">
        <div>
          <p className="eyebrow mb-3">Despre GoCluj</p>
          <h2 id="about-heading" className="font-display text-3xl sm:text-4xl">Mai aproape de oraș.<br />Mai aproape de oameni.</h2>
        </div>
        <p className="text-[var(--muted)] leading-7">GoCluj aduce într-un singur loc idei pentru timpul tău liber. Descoperă evenimentele publicate, vezi când și unde au loc și consultă sursa originală pentru programul actualizat și condițiile de acces.</p>
      </div>
      <div className="mx-auto flex w-full max-w-[1240px] flex-col gap-4 px-5 py-7 text-sm sm:flex-row sm:items-center sm:justify-between sm:px-8">
        <p className="text-[var(--muted)]">GoCluj · Descoperă orașul, eveniment cu eveniment.</p>
        <a className="footer-link" href="#top">Înapoi sus ↑</a>
      </div>
    </footer>
  )
}

export default SiteFooter
