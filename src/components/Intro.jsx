import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import './Intro.css'

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%'

function useScramble(text, startDelay = 0) {
  const [display, setDisplay] = useState(() => text.replace(/./g, ' '))
  const frame = useRef(0)
  const raf   = useRef(null)

  useEffect(() => {
    const start = setTimeout(() => {
      const totalFrames = 28
      const animate = () => {
        frame.current++
        const progress = frame.current / totalFrames
        setDisplay(
          text.split('').map((char, i) => {
            if (char === ' ') return ' '
            if (i / text.length < progress) return char
            return CHARS[Math.floor(Math.random() * CHARS.length)]
          }).join('')
        )
        if (frame.current < totalFrames) raf.current = requestAnimationFrame(animate)
        else setDisplay(text)
      }
      raf.current = requestAnimationFrame(animate)
    }, startDelay)

    return () => { clearTimeout(start); cancelAnimationFrame(raf.current) }
  }, [text, startDelay])

  return display
}

function CountUp({ target, suffix = '', duration = 1800 }) {
  const [val, setVal] = useState(0)
  const ref = useRef(null)
  const started = useRef(false)

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting && !started.current) {
        started.current = true
        const start = performance.now()
        const tick = (now) => {
          const t = Math.min((now - start) / duration, 1)
          // elastic overshoot easing
          const ease = t === 1 ? 1 : t < 0.5
            ? 4 * t * t * t
            : 1 - Math.pow(-2 * t + 2, 3) / 2
          setVal(Math.round(ease * target))
          if (t < 1) requestAnimationFrame(tick)
          else {
            // overshoot then snap
            setTimeout(() => setVal(target + (suffix === '%' ? 2 : 1)), 0)
            setTimeout(() => setVal(target), 120)
          }
        }
        requestAnimationFrame(tick)
      }
    }, { threshold: 0.5 })
    if (ref.current) obs.observe(ref.current)
    return () => obs.disconnect()
  }, [target, duration, suffix])

  return <span ref={ref}>{val}{suffix}</span>
}

// Magnetic button
function MagButton({ children, href, className }) {
  const ref  = useRef(null)
  const anim = useRef(null)
  const pos  = useRef({ x: 0, y: 0 })

  const onMove = (e) => {
    const r   = ref.current.getBoundingClientRect()
    const dx  = e.clientX - (r.left + r.width / 2)
    const dy  = e.clientY - (r.top  + r.height / 2)
    pos.current = { x: dx * 0.35, y: dy * 0.35 }
    ref.current.style.transform = `translate(${pos.current.x}px, ${pos.current.y}px)`
  }

  const onLeave = () => {
    ref.current.style.transition = 'transform 0.5s cubic-bezier(0.25,0.1,0.25,1)'
    ref.current.style.transform = 'translate(0,0)'
    setTimeout(() => { if (ref.current) ref.current.style.transition = '' }, 500)
  }

  return (
    <a
      ref={ref}
      href={href}
      className={className}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
    >
      {children}
    </a>
  )
}

export default function Intro() {
  const name   = useScramble('MANOJ SHENDRE', 200)
  const title  = useScramble('Computer Vision Engineer', 600)

  return (
    <section className="intro-section">
      {/* horizontal rule lines */}
      <div className="intro-lines" aria-hidden>
        {[...Array(6)].map((_, i) => <span key={i} className="iline" style={{ '--i': i }} />)}
      </div>

      <div className="intro-inner">
        {/* top row */}
        <motion.div
          className="intro-top"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3, duration: 0.6 }}
        >
          <span className="intro-index">01 / PORTFOLIO</span>
          <span className="intro-location">Bangalore, India · Open to relocation</span>
        </motion.div>

        {/* giant name */}
        <div className="intro-name-wrap">
          <div className="intro-name">{name}</div>
        </div>

        {/* title + tagline row */}
        <motion.div
          className="intro-mid"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.7 }}
        >
          <p className="intro-role">{title}</p>
          <p className="intro-tagline">
            Making machines read engineering drawings<br />
            <em>the way human engineers do.</em>
          </p>
        </motion.div>

        {/* stats */}
        <motion.div
          className="intro-stats"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.6 }}
        >
          <div className="istat">
            <span className="istat-num"><CountUp target={95} suffix="%" /></span>
            <span className="istat-label">Time reduction<br/>Railways BOM</span>
          </div>
          <div className="istat">
            <span className="istat-num"><CountUp target={10} /></span>
            <span className="istat-label">Production<br/>deployments</span>
          </div>
          <div className="istat">
            <span className="istat-num"><CountUp target={3} /></span>
            <span className="istat-label">Industries<br/>disrupted</span>
          </div>
        </motion.div>

        {/* cta */}
        <motion.div
          className="intro-cta"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 1, duration: 0.6 }}
        >
          <MagButton href="#experience" className="btn-primary">View Work</MagButton>
          <MagButton href="mailto:manojshendre.1202@gmail.com" className="btn-ghost">Get in Touch</MagButton>
        </motion.div>
      </div>

      {/* scroll hint */}
      <motion.div
        className="scroll-hint"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.4, duration: 0.6 }}
      >
        <span className="scroll-line" />
        <span className="scroll-text">scroll</span>
      </motion.div>
    </section>
  )
}
