import goClujLogo from '../../../logo.jpeg'

function SiteHeader() {
  return (
    <header className="site-header">
      <div className="mx-auto flex w-full max-w-[1240px] items-center justify-between px-5 py-4 sm:px-8">
        <a className="brand-link" href="#top" aria-label="GoCluj — pagina principală">
          <img className="brand-image" src={goClujLogo} alt="GoCluj" />
        </a>
        <nav aria-label="Navigare principală" className="flex items-center gap-6 sm:gap-9">
          <a className="nav-link" href="#evenimente" aria-current="page">Evenimente</a>
          <a className="nav-link" href="#despre">Despre</a>
        </nav>
      </div>
    </header>
  )
}

export default SiteHeader
