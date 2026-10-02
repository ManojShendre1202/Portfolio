import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom'
import Portfolio from './pages/portfolio/Portfolio'
import Readar    from './pages/readar/Readar'
import { trackPageView, applyOptOutFromUrl } from './tracking'
import './App.css'

// Fires once per route change (not per query-string change) — pathname only,
// so nothing user-specific ever ends up in the tracked path.
function RouteTracker() {
  const { pathname, search } = useLocation()

  useEffect(() => {
    let cancelled = false
    applyOptOutFromUrl(search).then(optedOut => {
      if (!cancelled && !optedOut && !new URLSearchParams(search).has('notrack')) {
        trackPageView(pathname)
      }
    })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname])

  return null
}

export default function App() {
  return (
    <BrowserRouter>
      <RouteTracker />
      <Routes>
        <Route path="/"         element={<Portfolio />} />
        <Route path="/readar"          element={<Readar />} />
        <Route path="/readar/:docId"   element={<Readar />} />
      </Routes>
    </BrowserRouter>
  )
}
