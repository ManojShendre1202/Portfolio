import { useEffect, useRef, useState } from 'react'
import './SidePanel.css'

const SECTIONS = ['Intro', 'About', 'Experience', 'Skills', 'Contact']

export default function SidePanel() {
  const [progress,       setProgress]       = useState(0)
  const [activeSection,  setActiveSection]  = useState('Intro')
  const raf = useRef(null)

  useEffect(() => {
    const onScroll = () => {
      const scrollTop  = window.scrollY
      const docHeight  = document.documentElement.scrollHeight - window.innerHeight
      setProgress(docHeight > 0 ? scrollTop / docHeight : 0)

      // detect active section
      const ids = ['about', 'experience', 'skills', 'contact']
      let current = 'Intro'
      for (const id of ids) {
        const el = document.getElementById(id)
        if (el && el.getBoundingClientRect().top < window.innerHeight * 0.4) {
          current = id.charAt(0).toUpperCase() + id.slice(1)
        }
      }
      setActiveSection(current)
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <>
      {/* left panel */}
      <div className="side-left">
        <span className="side-left-text">
          MANOJ SHENDRE · CV ENGINEER · BANGALORE
        </span>
      </div>

      {/* right panel */}
      <div className="side-right">
        <div className="side-progress-track">
          <div
            className="side-progress-fill"
            style={{ transform: `scaleY(${progress})` }}
          />
        </div>
        <span className="side-section-name">{activeSection}</span>
      </div>
    </>
  )
}
