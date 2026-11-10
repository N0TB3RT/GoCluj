import { useEffect, useRef, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

function SiteHeader({ onRefresh, loading = false }) {
  const isHome = useLocation().pathname === '/'
  // Off the home page the section links navigate home first; the home page scrolls to the hash.
  const NavLink = isHome ? 'a' : Link
  const target = (hash) => (isHome ? { href: hash } : { to: `/${hash}` })
  const [menuOpen, setMenuOpen] = useState(false)
  const [activeSection, setActiveSection] = useState('top')
  const headerRef = useRef(null)
  const menuButtonRef = useRef(null)

  useEffect(() => {
    let frame
    function updateSection() {
      const about = document.getElementById('despre')
      const events = document.getElementById('evenimente')
      const atBottom = window.scrollY + window.innerHeight >= document.documentElement.scrollHeight - 8
      setActiveSection(about && (about.getBoundingClientRect().top <= 140 || atBottom)
        ? 'despre'
        : events?.getBoundingClientRect().top <= 140 ? 'evenimente' : 'top')
    }
    function onScroll() {
      cancelAnimationFrame(frame)
      frame = requestAnimationFrame(updateSection)
    }
    updateSection()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
    }
  }, [])

  useEffect(() => {
    if (!menuOpen) return
    function onKeyDown(event) {
      if (event.key === 'Escape') {
        setMenuOpen(false)
        menuButtonRef.current?.focus()
      }
    }
    function onPointerDown(event) {
      if (!headerRef.current?.contains(event.target)) setMenuOpen(false)
    }
    const desktop = window.matchMedia('(min-width: 768px)')
    const closeOnDesktop = () => { if (desktop.matches) setMenuOpen(false) }
    desktop.addEventListener('change', closeOnDesktop)
    document.addEventListener('keydown', onKeyDown)
    document.addEventListener('pointerdown', onPointerDown)
    return () => {
      desktop.removeEventListener('change', closeOnDesktop)
      document.removeEventListener('keydown', onKeyDown)
      document.removeEventListener('pointerdown', onPointerDown)
    }
  }, [menuOpen])

  return (
    <header ref={headerRef} className="site-header">
      <div className="header-inner mx-auto flex w-full max-w-[1240px] items-center justify-between px-5 py-4 sm:px-8">
        <NavLink className="brand-link" {...target('#top')} aria-label="GoCluj — pagina principală" onClick={() => setMenuOpen(false)}>
          <img className="brand-image" src="/images/gocluj-white.svg" alt="GoCluj" width="165" height="44" />
        </NavLink>
        <button ref={menuButtonRef} type="button" className="menu-toggle" aria-expanded={menuOpen} aria-controls="main-navigation" onClick={() => setMenuOpen(!menuOpen)}>
          <span>{menuOpen ? 'Închide' : 'Meniu'}</span>
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d={menuOpen ? 'm6 6 12 12M18 6 6 18' : 'M4 7h16M4 12h16M4 17h16'} stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" />
          </svg>
        </button>
        <nav id="main-navigation" aria-label="Navigare principală" className={`main-navigation ${menuOpen ? 'is-open' : ''}`}>
          <NavLink className="nav-link" {...target('#evenimente')} aria-current={isHome && activeSection === 'evenimente' ? 'location' : undefined} onClick={() => setMenuOpen(false)}>Evenimente</NavLink>
          <NavLink className="nav-link" {...target('#despre')} aria-current={isHome && activeSection === 'despre' ? 'location' : undefined} onClick={() => setMenuOpen(false)}>Despre GoCluj</NavLink>
          {onRefresh && (
            <button className="nav-refresh" type="button" disabled={loading} onClick={() => { onRefresh(); setMenuOpen(false) }}>
              {loading ? 'Se încarcă…' : 'Actualizează lista'} <span aria-hidden="true">↻</span>
            </button>
          )}
        </nav>
      </div>
    </header>
  )
}

export default SiteHeader
