import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence, useScroll, useTransform, useMotionValue, useSpring } from 'framer-motion'
import lottie from 'lottie-web'
import robotData from '../../assets/robot.json'
import './Portfolio.css'

/* ══════════════════════════════
   TILT CARD — cursor-reactive 3D tilt wrapper
══════════════════════════════ */
function TiltCard({ children, className, style, max = 6, ...motionProps }) {
  const ref = useRef(null)
  const mx  = useMotionValue(0)
  const my  = useMotionValue(0)
  const rotateX = useSpring(useTransform(my, [-0.5, 0.5], [max, -max]), { stiffness: 300, damping: 30 })
  const rotateY = useSpring(useTransform(mx, [-0.5, 0.5], [-max, max]), { stiffness: 300, damping: 30 })
  const glowX   = useSpring(useTransform(mx, [-0.5, 0.5], ['0%', '100%']), { stiffness: 300, damping: 30 })
  const glowY   = useSpring(useTransform(my, [-0.5, 0.5], ['0%', '100%']), { stiffness: 300, damping: 30 })

  const onMove = (e) => {
    const r = ref.current.getBoundingClientRect()
    mx.set((e.clientX - r.left) / r.width - 0.5)
    my.set((e.clientY - r.top) / r.height - 0.5)
  }
  const onLeave = () => { mx.set(0); my.set(0) }

  return (
    <motion.div
      ref={ref}
      className={`tilt-card ${className || ''}`}
      style={{ ...style, rotateX, rotateY, '--gx': glowX, '--gy': glowY }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      {...motionProps}
    >
      <div className="tilt-glow" aria-hidden />
      {children}
    </motion.div>
  )
}

/* ══════════════════════════════
   NAVBAR
══════════════════════════════ */
const NAV_LINKS = [
  { label: 'About',      href: '#about'      },
  { label: 'Experience', href: '#experience' },
  { label: 'Readar',     href: '#readar'     },
  { label: 'Skills',     href: '#skills'     },
  { label: 'Contact',    href: '#contact'    },
]

function Navbar() {
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 60)
    window.addEventListener('scroll', fn, { passive: true })
    return () => window.removeEventListener('scroll', fn)
  }, [])

  return (
    <motion.nav
      className={`navbar ${scrolled ? 'scrolled' : ''}`}
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0,   opacity: 1 }}
      transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <a href="#" className="nav-logo">M<em>S</em></a>

      <div className="nav-links">
        {NAV_LINKS.map(l => (
          <a key={l.href} href={l.href} className="nav-link">{l.label}</a>
        ))}
      </div>

      <div className="nav-right">
        <a href="https://github.com/ManojShendre1202" target="_blank" rel="noopener noreferrer" className="nav-social" title="GitHub">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
          </svg>
        </a>
        <a href="https://www.linkedin.com/in/manoj-shendre-a40b932b0/" target="_blank" rel="noopener noreferrer" className="nav-social" title="LinkedIn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/>
          </svg>
        </a>
        <a href="mailto:manojshendre.1202@gmail.com" className="nav-hire">
          Hire Me <span className="nav-dot" />
        </a>
      </div>
    </motion.nav>
  )
}

/* ══════════════════════════════
   SIDE PANEL
══════════════════════════════ */
function SidePanel() {
  const [progress,      setProgress]      = useState(0)
  const [activeSection, setActiveSection] = useState('Intro')

  useEffect(() => {
    const onScroll = () => {
      const scrollTop = window.scrollY
      const docHeight = document.documentElement.scrollHeight - window.innerHeight
      setProgress(docHeight > 0 ? scrollTop / docHeight : 0)

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
      <div className="side-left">
        <span className="side-left-text">
          MANOJ SHENDRE · CV ENGINEER · BANGALORE
        </span>
      </div>

      <div className="side-right">
        <div className="side-progress-track">
          <div className="side-progress-fill" style={{ transform: `scaleY(${progress})` }} />
        </div>
        <span className="side-section-name">{activeSection}</span>
      </div>
    </>
  )
}

/* ══════════════════════════════
   INTRO
══════════════════════════════ */
const SCRAMBLE_CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%'

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
            return SCRAMBLE_CHARS[Math.floor(Math.random() * SCRAMBLE_CHARS.length)]
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
          const ease = t === 1 ? 1 : t < 0.5
            ? 4 * t * t * t
            : 1 - Math.pow(-2 * t + 2, 3) / 2
          setVal(Math.round(ease * target))
          if (t < 1) requestAnimationFrame(tick)
          else {
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

function MagButton({ children, href, className }) {
  return (
    <a href={href} className={className}>
      {children}
    </a>
  )
}

function Intro() {
  const name  = useScramble('MANOJ SHENDRE', 200)
  const title = useScramble('Machine Learning Engineer', 600)

  return (
    <section className="intro-section">
      <span className="reg-mark tl" aria-hidden /><span className="reg-mark tr" aria-hidden />

      <div className="intro-lines" aria-hidden>
        {[...Array(6)].map((_, i) => <span key={i} className="iline" style={{ '--i': i }} />)}
      </div>

      <div className="intro-inner">
        <motion.div
          className="intro-top"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <span className="callout-label">· Cover</span>
          <span className="intro-location">Bangalore, India</span>
        </motion.div>

        <div className="intro-grid">
          <div className="intro-main">
            <motion.div
              className="intro-name-wrap"
              initial={{ opacity: 0, y: 40, filter: 'blur(8px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ delay: 0.2, duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
            >
              <div className="intro-name">{name}</div>
            </motion.div>

            <motion.div
              className="intro-mid"
              initial={{ opacity: 0, y: 30, filter: 'blur(4px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
              transition={{ delay: 0.4, duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
            >
              <p className="intro-role">{title}</p>
              <p className="intro-tagline">
                Making machines read engineering drawings<br />
                <em>the way human engineers do.</em>
              </p>
            </motion.div>

            <motion.div
              className="intro-cta"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.75, duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
            >
              <MagButton href="#experience" className="btn-primary">View Work</MagButton>
              <MagButton href="mailto:manojshendre.1202@gmail.com" className="btn-ghost">Get in Touch</MagButton>
            </motion.div>
          </div>

          <motion.div
            className="intro-ledger"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className="ledger-row">
              <span className="istat-tag">01</span>
              <span className="istat-num"><CountUp target={95} suffix="%" /></span>
              <span className="istat-label">Time reduction<br/>Railways BOM</span>
            </div>
            <div className="ledger-row">
              <span className="istat-tag">02</span>
              <span className="istat-num"><CountUp target={10} /></span>
              <span className="istat-label">Client<br/>projects</span>
            </div>
            <div className="ledger-row">
              <span className="istat-tag">03</span>
              <span className="istat-num"><CountUp target={6} /></span>
              <span className="istat-label">Industries<br/>served</span>
            </div>
          </motion.div>
        </div>
      </div>

      <motion.div
        className="scroll-hint"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1.1, duration: 0.6 }}
      >
        <span className="scroll-line" />
        <span className="scroll-text">scroll</span>
      </motion.div>

      <div className="sheet-title-block">
        <div className="stb-num">MS-01</div>
        <div>CV Engineer</div>
        <div className="stb-rev">Rev. 2026</div>
      </div>
    </section>
  )
}

/* ══════════════════════════════
   MARQUEE
══════════════════════════════ */
const MARQUEE_ITEMS = [
  'Railways', 'Shipbuilding', 'Automotive',
  'Aerospace', 'Defense', 'Industrial Manufacturing',
  'Computer Vision', 'Graph Algorithms',
]

function Marquee({ dark = false }) {
  const repeated = [...MARQUEE_ITEMS, ...MARQUEE_ITEMS, ...MARQUEE_ITEMS]

  return (
    <div className={`marquee-wrap ${dark ? 'marquee-dark' : ''}`}>
      <div className="marquee-track">
        {repeated.map((item, i) => (
          <span key={i} className="marquee-item">
            {item} <span className="marquee-dot">·</span>
          </span>
        ))}
      </div>
    </div>
  )
}

/* mask-wipe reveal — curtain-style clip-path reveal for headlines.
   onMount=true animates immediately instead of on scroll — whileInView's
   IntersectionObserver is unreliable inside a position:sticky ancestor
   (e.g. .exp-header-wrap), so sticky-parented headlines would stay stuck
   at their fully-clipped initial state and never reveal. */
function MaskReveal({ children, as: Tag = 'h2', className, delay = 0, onMount = false }) {
  const hiddenClip  = 'inset(-20% 100% -20% 0%)'
  const visibleClip = 'inset(-20% 0% -20% 0%)'
  const revealProps = onMount
    ? { initial: { clipPath: hiddenClip }, animate: { clipPath: visibleClip } }
    : { initial: { clipPath: hiddenClip }, whileInView: { clipPath: visibleClip }, viewport: { once: true, margin: '-80px' } }

  return (
    <div className="mask-reveal-wrap">
      <motion.div
        {...revealProps}
        transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
      >
        <Tag className={className}>{children}</Tag>
      </motion.div>
    </div>
  )
}

/* ══════════════════════════════
   ABOUT
══════════════════════════════ */
const aboutReveal = (delay = 0) => ({
  initial:    { opacity: 0, y: 48, filter: 'blur(6px)' },
  whileInView:{ opacity: 1, y: 0,  filter: 'blur(0px)' },
  viewport:   { once: true, margin: '-60px' },
  transition: { duration: 0.85, delay, ease: [0.16, 1, 0.3, 1] },
})

const CREDENTIALS = [
  {
    label: 'Education',
    title: 'B.Tech — Aeronautical Engineering',
    sub:   'Bharath University, Chennai · 2023',
  },
  {
    label: 'Internship',
    title: 'Hindustan Aeronautics Limited',
    sub:   'End-to-end documentation of Chetak helicopter manufacturing',
  },
  {
    label: 'Research',
    title: '3 Publications',
    sub: (
      <>
        <a href="https://doi.org/10.15282/ijame.21.2.2024.3.0866" target="_blank" rel="noopener noreferrer" className="cred-link">
          Static Aeroelastic Analysis &amp; Flutter Characterization
        </a>
        {' · '}
        <a href="https://doi.org/10.4273/ijvss.16.1.04" target="_blank" rel="noopener noreferrer" className="cred-link">
          Static Aeroelastic Characterization
        </a>
        {' · '}
        <a href="https://doi.org/10.21203/rs.3.rs-7726344/v1" target="_blank" rel="noopener noreferrer" className="cred-link">
          Color Vision Prediction from Cone Ratios (preprint)
        </a>
      </>
    ),
  },
]

function About() {
  const sectionRef = useRef(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], [40, -40])

  return (
    <section className="about-section" id="about" ref={sectionRef}>
      <span className="reg-mark tl" aria-hidden /><span className="reg-mark br" aria-hidden />
      <motion.div className="about-inner" style={{ y }}>

        <motion.p className="section-label" {...aboutReveal(0)}>About</motion.p>

        <MaskReveal className="about-headline" delay={0.1}>
          Aeronautical engineer<br />
          <em>who builds CV systems</em>
        </MaskReveal>

        <motion.div className="about-body" {...aboutReveal(0.2)}>
          <p>
            I graduated in Aeronautical Engineering — then pivoted into Computer Vision
            because the aerospace background is a superpower when your job is making
            machines read engineering drawings.
          </p>
          <p>
            In 2 years at Kynea Solutions, I've handled core development or led 7 of 10 client
            projects across the railways, shipbuilding, aerospace, automotive, defense,
            and industrial manufacturing domains.
          </p>
          <p>
            As a personal project, I also built and deployed <strong>Readar</strong> — a
            graph-based RAG chat engine with custom retrieval, graph traversal, cross-encoder
            reranking, and session memory, cutting LLM token usage by ~75–85% with no accuracy
            loss.
          </p>
        </motion.div>

        <motion.div className="about-credentials" {...aboutReveal(0.3)}>
          {CREDENTIALS.map((c, i) => (
            <div className="cred-row" key={i}>
              <span className="cred-num">{String(i + 1).padStart(2, '0')}</span>
              <span className="cred-label">{c.label}</span>
              <div className="cred-body">
                <p className="cred-title">{c.title}</p>
                <p className="cred-sub">{c.sub}</p>
              </div>
            </div>
          ))}
        </motion.div>

      </motion.div>

      <div className="sheet-title-block">
        <div className="stb-num">MS-02</div>
        <div>Profile</div>
      </div>
    </section>
  )
}

/* ══════════════════════════════
   PROJECT MODAL
══════════════════════════════ */
function ProjectModal({ project, onClose }) {
  useEffect(() => {
    const onKey = (e) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose])

  if (!project) return null

  return (
    <AnimatePresence>
      <motion.div
        className="modal-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.3 }}
        onClick={onClose}
      >
        <motion.div
          className="modal-panel"
          initial={{ opacity: 0, y: 60, scale: 0.97 }}
          animate={{ opacity: 1, y: 0,  scale: 1    }}
          exit={{    opacity: 0, y: 40, scale: 0.97 }}
          transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          onClick={(e) => e.stopPropagation()}
        >
          <button className="modal-close" onClick={onClose}>
            <span>✕</span> <span className="modal-close-label">ESC</span>
          </button>

          <div className="modal-header">
            <div className="modal-meta">
              <span className="modal-num">{project.num}</span>
              <span className="modal-client">{project.client}</span>
              {project.solo && (
                <span className="modal-solo">
                  {project.lead ? 'Project Lead' : 'Core Development'}
                </span>
              )}
            </div>
            <h2 className="modal-title">{project.title}</h2>
            <div className="modal-status-row">
              <span className="modal-status" style={{ color: project.statusColor }}>
                ● {project.status}
              </span>
              <span className="modal-impact">{project.impact}</span>
            </div>
          </div>

          <div className="modal-divider" />

          <div className="modal-body">
            <div className="modal-section">
              <p className="modal-section-label">What it does</p>
              <p className="modal-text">{project.fullDesc}</p>
            </div>

            {project.techDetails && (
              <div className="modal-section">
                <p className="modal-section-label">Technical Approach</p>
                <ul className="modal-tech-list">
                  {project.techDetails.map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            )}

            {project.beforeAfter && (
              <div className="modal-section">
                <p className="modal-section-label">Before vs After</p>
                <div className="modal-ba">
                  <div className="modal-ba-item before">
                    <span className="ba-label">Before</span>
                    <p>{project.beforeAfter.before}</p>
                  </div>
                  <div className="modal-arrow">→</div>
                  <div className="modal-ba-item after">
                    <span className="ba-label">After</span>
                    <p>{project.beforeAfter.after}</p>
                  </div>
                </div>
              </div>
            )}

            <div className="modal-section">
              <p className="modal-section-label">Stack</p>
              <div className="modal-tags">
                {project.tags.map(t => (
                  <span key={t} className="modal-tag">{t}</span>
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}

/* ══════════════════════════════
   EXPERIENCE
══════════════════════════════ */
const STATUS_COLOR = {
  'Production': '#16a34a',
  'Delivered':  '#16a34a',
  'UAT':        '#2563eb',
  'Near-Prod':  '#d97706',
  'In Dev':     '#78716c',
}

const PROJECTS = [
  {
    num: '01', client: 'Railways', title: 'Automated BOM Generation',
    status: 'Production', impact: '95% reduction — 1 month → 2 hours',
    tags: ['Python', 'OpenCV', 'OCR', 'Azure'],
    desc: 'Reads railway engineering drawings with image sizes near a lakh pixels and generates complete Bills of Materials.',
    fullDesc: 'Reads PDFs and images of railway engineering drawings — some with image sizes near a lakh pixels. Encodes complex domain flowchart logic in Python to identify components, interpret symbols, and generate complete Bills of Materials automatically. Handles scale variations, noisy scans, and domain-specific notation.',
    techDetails: [
      'Multi-scale PDF processing with adaptive resolution based on drawing density',
      'Custom OCR pipeline fine-tuned for railway engineering notation and symbols',
      'Flowchart logic encoder that replicates domain expert decision trees in Python',
      'Azure cloud integration for parallel processing of large drawing sets',
    ],
    beforeAfter: { before: '10–20 engineers, ~1 month per drawing set', after: '2–3 people, ~2 hours including human verification' },
  },
  {
    num: '02', client: 'Shipbuilding — Cable Systems', title: 'Cable Routing System',
    status: 'UAT', impact: 'Lakhs of cables · Lakhs of km routed', solo: true,
    tags: ['Python', 'ezdxf', 'Shapely', 'Dijkstra', 'Graph Algorithms'],
    desc: 'Flood Fill + Dijkstra hybrid routes cables across ship decks via a universal graph from DXF drawings.',
    fullDesc: 'Parses complex DXF ship drawings to identify multiple decks and cable trays — a significant challenge given the varied curves, angles, and representations across different ship departments. Builds a universal topological graph of the ship, then routes cables using a custom Flood Fill + Dijkstra hybrid algorithm that accounts for tray capacity, routing constraints, and cable specifications.',
    techDetails: [
      'DXF parsing with ezdxf to extract cable tray geometry across multiple ship decks',
      'Shapely-based geometric analysis to classify tray types from varied curve representations',
      'Universal graph construction representing all possible routing paths',
      'Flood Fill + Dijkstra hybrid for optimal cable routing with constraint satisfaction',
      'BOM output: cable lengths, tray assignments, routing paths',
    ],
    beforeAfter: { before: 'Manual routing by engineers — weeks per ship, lakhs of cables', after: 'Automated routing in hours — same accuracy, full BOM output' },
  },
  {
    num: '03', client: 'Shipbuilding — Hull Engineering', title: 'Hull Weld Seam BOM',
    status: 'UAT', impact: 'Thousands of weld spots per drawing', solo: true, lead: true,
    tags: ['Python', 'ezdxf', 'Shapely', 'OpenCV'],
    desc: 'On-spot geometric computation of weld seam lengths — no graph, no ML. Pure shape analysis.',
    fullDesc: 'Second project within the shipbuilding domain — a different department, demonstrating repeat client engagement. Detects thousands of welding spots and blocks across hull drawings, then computes weld seam lengths via on-spot geometric calculation. Deliberately contrasts with the cable routing approach — no graph-based algorithm, no ML models. Pure shape analysis because the problem structure demands it.',
    techDetails: [
      'Hull drawing parsing with ezdxf — different schema from cable routing drawings',
      'Weld spot and block detection using Shapely geometric analysis',
      'On-spot seam length computation via direct geometric measurement',
      'No ML, no graph — pure engineering solution matching the problem structure',
      'BOM output: weld seam lengths, weld types, location references',
    ],
    beforeAfter: { before: 'Manual measurement by engineers — error-prone on complex hull geometries', after: 'Automated geometric computation — thousands of spots in minutes' },
  },
  {
    num: '04', client: 'Automotive (multiple clients)', title: 'Automotive Wiring Harness BOM',
    status: 'Near-Prod', impact: '~95% reduction — 2–3 days → 1 hour',
    tags: ['FasterRCNN', 'AWS', 'Azure', 'OpenCV', 'OCR'],
    desc: 'FasterRCNN detection + graph association generates full BOM from automotive wiring drawings.',
    fullDesc: 'Processes complex automotive wiring harness drawings across multiple clients — among the most intricate engineering drawings in any domain. Element detection using a locally-trained FasterRCNN model identifies connectors, terminals, splices, and wiring components. Custom graph association logic (core contribution) links detected elements to tables and BOM entries, calculates wiring lengths and bundle configurations, and generates complete manufacturing BOMs.',
    techDetails: [
      'FasterRCNN trained locally on automotive wiring harness components',
      'Custom graph/association logic linking detected elements to BOM tables',
      'Wiring length calculation from geometric analysis of harness paths',
      'Bundle calculation combining individual wire specifications',
      'AWS + Azure cloud processing for large drawing batches',
    ],
    beforeAfter: { before: '3–4 engineers, ~2–3 days per harness drawing set', after: '~1 hour including manual verification step' },
  },
  {
    num: '05', client: 'Defense Shipbuilding', title: 'Cable Routing POC',
    status: 'Delivered', impact: 'Sent Alone · On-site · No internet · 120m ships', solo: true,
    tags: ['Python', 'ezdxf', 'Shapely', 'OpenCV'],
    desc: 'On-site live delivery, sent alone, with zero internet access on 120m+ ships.',
    fullDesc: 'Sent alone by the company to deliver a live proof-of-concept on-site at a defense shipyard, with no internet access. Ships 120+ meters in length with DXF and SVG format drawings (a different format from the earlier shipbuilding engagement). Adapted the cable routing engine on-site for the new format, ran live demonstrations, and delivered a technically successful POC.',
    techDetails: [
      "Adapted cable routing engine for the client's DXF + SVG drawing formats",
      'On-site adaptation with zero internet — all dependencies pre-packaged',
      '120m+ ship drawings with significantly different deck layout conventions',
      "Live demonstration to the client's engineering team",
    ],
  },
  {
    num: '06', client: 'Aerospace', title: 'Aircraft BOM Generation',
    status: 'In Dev', impact: 'Airbus + Boeing aircraft database', solo: true,
    tags: ['Python', 'YOLO', 'OpenCV', 'AWS OCR'],
    desc: 'YOLO content classification + deterministic OpenCV table detection, tuned for maximum extraction accuracy.',
    fullDesc: 'Processes complex scanned engineering drawings for Airbus and Boeing aircraft databases. Trained a YOLO classification model to identify content types across each drawing and route regions to the right extraction path. Table detection itself stays deterministic — fax-format unstructured tables have enough consistent geometric structure that a pure OpenCV approach, backed by custom CV detection and processing, is more accurate and maintainable than a neural network for that specific step.',
    techDetails: [
      'YOLO classification model trained to identify content types across scanned drawings',
      'Fax-format unstructured table detection — deterministic OpenCV, no ML by design',
      "AWS's document-extraction OCR for text extraction, tuned for maximum accuracy",
      'Cross-document reference resolution across large Airbus/Boeing drawing sets',
    ],
  },
  {
    num: '07', client: 'Electrical Components Manufacturing', title: 'SAP Deduction Validation',
    status: 'Production', impact: '1+ year owned · 6 months in production', solo: true,
    tags: ['Python', 'Azure ADF', 'ADLS', 'SQL'],
    desc: 'Sole maintainer of an existing ML model validating SAP deductions — took it to production, own the full support lifecycle.',
    fullDesc: 'An existing ML classification model that validates the genuineness of deductions across SAP enterprise documents, inherited rather than built from scratch. The only non-drawing project in the portfolio — demonstrates stack versatility beyond computer vision, enterprise data pipeline experience, and SAP domain knowledge. Sole maintainer for 1+ year: took the system to production, stabilized its accuracy-drift-triggered retraining pipeline, and own the full support lifecycle — monitoring, dashboarding, and all client change requests.',
    techDetails: [
      'Existing ML classification model for SAP deduction validation, maintained not built',
      'Stabilized and productionized an accuracy-drift-triggered retraining pipeline',
      'Azure Data Factory (ADF) pipelines for automated data ingestion',
      'Azure Data Lake Storage (ADLS) for document and result storage',
      'SQL-based reporting and dashboard for business users',
    ],
    beforeAfter: { before: 'Manual review of deductions by finance team — slow, inconsistent', after: 'Automated ML validation — sole maintainer for 1+ year, in production for the last 6 months' },
  },
]

function ProjectRow({ p, onOpen }) {
  const sc  = STATUS_COLOR[p.status] || '#78716c'
  const ref = useRef(null)
  const mx  = useMotionValue(0)
  const my  = useMotionValue(0)
  const rotateX = useSpring(useTransform(my, [-0.5, 0.5], [3, -3]), { stiffness: 300, damping: 30 })
  const rotateY = useSpring(useTransform(mx, [-0.5, 0.5], [-3, 3]), { stiffness: 300, damping: 30 })
  const glowX   = useSpring(useTransform(mx, [-0.5, 0.5], ['0%', '100%']), { stiffness: 300, damping: 30 })
  const glowY   = useSpring(useTransform(my, [-0.5, 0.5], ['0%', '100%']), { stiffness: 300, damping: 30 })

  const onMove  = (e) => {
    const r = ref.current.getBoundingClientRect()
    mx.set((e.clientX - r.left) / r.width - 0.5)
    my.set((e.clientY - r.top) / r.height - 0.5)
  }
  const onLeave = () => { mx.set(0); my.set(0) }

  return (
    <motion.div
      ref={ref}
      className="log-row"
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay: 0.03, ease: [0.25, 0.1, 0.25, 1] }}
      style={{ rotateX, rotateY, '--gx': glowX, '--gy': glowY }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      onClick={() => onOpen({ ...p, statusColor: sc })}
    >
      <div className="log-glow" aria-hidden />
      <span className="log-num">{p.num}</span>

      <div className="log-main">
        <div className="log-top-line">
          <p className="log-client">{p.client}</p>
          <span className="log-status" style={{ color: sc }}>● {p.status}</span>
          {p.solo && <span className="log-solo">{p.lead ? 'Lead' : 'Core Dev'}</span>}
        </div>
        <h3 className="log-title">{p.title}</h3>
        <p className="log-desc">{p.desc}</p>
        <div className="log-tags">
          {p.tags.map(t => <span key={t} className="log-tag">{t}</span>)}
        </div>
      </div>

      <div className="log-side">
        <p className="log-impact">{p.impact}</p>
        <span className="log-open">View details →</span>
      </div>
    </motion.div>
  )
}

function Experience() {
  const [modal, setModal] = useState(null)
  const sectionRef = useRef(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], [50, -50])

  return (
    <>
      <section className="exp-section" id="experience" ref={sectionRef}>
        <span className="reg-mark tr" aria-hidden /><span className="reg-mark bl" aria-hidden />
        <div className="exp-header-wrap">
          <motion.div className="exp-header" style={{ y }}>
            <p className="section-label">Professional Experience</p>
            <MaskReveal className="section-title" onMount>
              Kynea Solutions LLP<br />
              <em>May 2024 — Present</em>
            </MaskReveal>
            <p className="exp-sub">
              ML Engineer · Bangalore<br />
              7 of 10 projects — core development or lead
            </p>
            <p className="exp-hint">Click any card for full details</p>
          </motion.div>
        </div>

        <div className="case-log">
          {PROJECTS.map((p, i) => (
            <ProjectRow key={i} p={p} onOpen={setModal} />
          ))}
        </div>

        <div className="sheet-title-block">
          <div className="stb-num">MS-03</div>
          <div>Case Log</div>
        </div>
      </section>

      {modal && <ProjectModal project={modal} onClose={() => setModal(null)} />}
    </>
  )
}

/* ══════════════════════════════
   READAR
══════════════════════════════ */
const DOCK_STEPS = [
  { num: '01', title: 'Parse',   desc: 'DOM-aware HTML parsing — heading-path stitching, no font-size heuristics. Cross-page paragraph stitching for PDFs.' },
  { num: '02', title: 'Embed',   desc: 'nomic-embed-text-v1.5 locally, 8192-token context. Overflow nodes chunked + mean-pooled, never truncated.' },
  { num: '03', title: 'Graph',   desc: 'Cosine-similarity edges above threshold connect nodes — coreferences resolve naturally, no entity extraction pass.' },
  { num: '04', title: 'Retrieve', desc: 'BFS hop traversal over the graph pulls a candidate subgraph — a cheap, wide recall net.' },
  { num: '05', title: 'Rerank',  desc: 'Cross-encoder re-scores candidates against the real query text — cuts tokens sent to Gemini by ~75-85%.' },
  { num: '06', title: 'Stream',  desc: 'WebSocket token streaming with live citation highlighting — click a citation, it scrolls to and flashes the real source paragraph.' },
]

const DOCK_PRINCIPLES = [
  {
    name:   'Memory that doesn\'t grow with the conversation',
    metric: 'Flat cost — turn 2 or turn 30',
    detail: 'Each turn\'s hidden summary gets embedded into its own small per-session graph. A new question retrieves only the few relevant past turns, never the full transcript.',
  },
  {
    name:   'Rerank before it reaches Gemini',
    metric: '~75-85% fewer tokens per answer',
    detail: 'Graph-hop retrieval casts a wide net; a cross-encoder re-scores every candidate against the actual question before anything gets sent to the model.',
  },
  {
    name:   'A similarity graph, not an entity graph',
    metric: 'Zero entity-extraction passes',
    detail: 'Nodes are paragraphs, edges are cosine similarity. Coreferences like "it" or "the system" resolve for free by clustering with what they mean.',
  },
  {
    name:   'Built to survive real concurrent load',
    metric: 'Load-tested with real simultaneous chats',
    detail: 'Blocking embed/rerank/Gemini calls run off the shared event loop in dedicated executors; a rate guard returns a friendly message instead of a raw exception.',
  },
]

function Readar() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const lineH = useTransform(scrollYProgress, [0.1, 0.8], ['0%', '100%'])

  return (
    <section className="dock-section" id="readar" ref={ref}>
      <span className="reg-mark on-dark tl" aria-hidden /><span className="reg-mark on-dark tr" aria-hidden />
      <div className="dock-inner">

        <motion.div
          className="dock-header"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
        >
          <p className="section-label">Personal Project</p>
          <MaskReveal className="section-title">Readar<br /><em>Graph RAG Chat Engine</em></MaskReveal>
          <p className="dock-tagline">
            A retrieval-augmented chatbot built from scratch —<br />
            semantic similarity graph, live citations, real conversation memory.
          </p>
        </motion.div>

        <div className="dock-body">
          <motion.div
            className="dock-story"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <p>
              A <strong>graph-based RAG pipeline</strong> written from first principles — no
              vector DB, no LangChain. Paragraphs become nodes, cosine-similarity edges connect
              related ideas, and a BFS hop-traversal retrieves a subgraph per question. A
              cross-encoder reranks the candidates before anything reaches Gemini.
            </p>
            <p>
              The live demo ingests real documentation end-to-end — parsed straight from the
              DOM, stitched into 1,049 nodes and 549,676 similarity edges — and answers with
              streamed responses, clickable citations that scroll to and highlight the exact
              source paragraph, and a live trace panel exposing retrieval scores, token counts,
              and latency per stage.
            </p>
            <p>
              Multi-turn memory is <strong>retrieval-augmented, not history replay</strong> —
              each turn's hidden summary is embedded into its own small per-session graph, so
              cost stays flat over a long conversation instead of growing with every turn.
            </p>
            <p>
              Self-hosted end-to-end on an <strong>Oracle Cloud (OCI) ARM VM</strong> — Dockerized
              Django + WebSocket services behind Nginx, load-tested with real concurrent chat
              sessions (embedding, reranking, and Gemini streaming all running under actual
              simultaneous load, not just single-request benchmarks).
            </p>

            <div className="dock-stats">
              {[
                { num: '1,049',  label: 'Nodes ingested\n(live demo graph)' },
                { num: '~80%',   label: 'Token cut from\ntwo-stage rerank' },
              ].map((s, i) => (
                <div key={i} className="dock-stat">
                  <span className="dock-stat-num">{s.num}</span>
                  <span className="dock-stat-label">{s.label}</span>
                </div>
              ))}
            </div>
          </motion.div>

          <div className="dock-steps-wrap">
            <p className="dock-steps-title">Pipeline — question to answer</p>

            <div className="dock-line-track">
              <motion.div className="dock-line-fill" style={{ height: lineH }} />
            </div>

            <div className="dock-steps">
              {DOCK_STEPS.map((s, i) => (
                <motion.div
                  key={i}
                  className="dock-step"
                  initial={{ opacity: 0, x: 20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true, margin: '-40px' }}
                  transition={{ duration: 0.5, delay: i * 0.08 }}
                >
                  <span className="ds-num">{s.num}</span>
                  <div className="ds-content">
                    <p className="ds-title">{s.title}</p>
                    <p className="ds-desc">{s.desc}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </div>

        <motion.div
          className="dock-principles"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <p className="dock-principles-title">Engineering decisions</p>
          <div className="dock-principles-grid">
            {DOCK_PRINCIPLES.map((p, i) => (
              <TiltCard
                key={i}
                className="dock-principle"
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-20px' }}
                transition={{ duration: 0.5, delay: i * 0.07 }}
              >
                <p className="dp-name">{p.name}</p>
                <p className="dp-metric">{p.metric}</p>
                <p className="dp-how">{p.detail}</p>
              </TiltCard>
            ))}
          </div>
        </motion.div>

        <motion.div
          className="dock-oss"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <span className="dock-oss-label">Live Demo</span>
          <p>
            Try it yourself — pick a curated doc and ask it anything at{' '}
            <a href="https://manojshendre.com/readar/" target="_blank" rel="noopener noreferrer" className="dock-oss-link">
              manojshendre.com/readar
            </a>
          </p>
        </motion.div>

      </div>

      <div className="sheet-title-block on-dark">
        <div className="stb-num">MS-04</div>
        <div>Field Notes</div>
      </div>
    </section>
  )
}

/* ══════════════════════════════
   SKILLS
══════════════════════════════ */
const SKILLS = [
  { cat: 'AI, ML & LLM Engineering', items: ['Machine Learning', 'Deep Learning', 'Generative AI', 'Large Language Models (LLMs)', 'Retrieval-Augmented Generation (RAG)', 'Google Gemini API', 'Prompt Engineering', 'Vector Embeddings', 'Semantic Search', 'Natural Language Processing (NLP)'] },
  { cat: 'Computer Vision & ML',    items: ['OpenCV (advanced)', 'FasterRCNN', 'OCR', 'Azure Computer Vision', 'ChangeFormer', 'PyTorch'] },
  { cat: 'Drawing & Geometry',      items: ['ezdxf', 'Shapely', 'DXF processing', 'SVG processing', 'PDF processing'] },
  { cat: 'Cloud & Infrastructure',  items: ['Azure ADF', 'Azure ADLS', 'AWS', 'Oracle Cloud Infrastructure (OCI)', 'Docker', 'Nginx'] },
  { cat: 'Backend & Systems',       items: ['Python', 'Django', 'FastAPI', 'WebSockets', 'Custom Worker Pools', 'SQL'] },
  { cat: 'Databases',               items: ['MSSQL', 'MySQL', 'ArangoDB', 'Azure Data Lake', 'Firebase', 'PostgreSQL'] },
]

function Skills() {
  const sectionRef = useRef(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], [30, -30])

  return (
    <section className="skills-section" id="skills" ref={sectionRef}>
      <span className="reg-mark tl" aria-hidden /><span className="reg-mark br" aria-hidden />
      <motion.div className="skills-inner" style={{ y }}>
        <motion.div
          className="skills-header"
          initial={{ opacity: 0, y: 40, filter: 'blur(6px)' }}
          whileInView={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
          viewport={{ once: true, margin: '-60px' }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <p className="section-label">Technical Skills</p>
          <MaskReveal className="section-title">What I work with</MaskReveal>
        </motion.div>

        <div className="bom-table">
          <div className="bom-row bom-head">
            <span>Item</span>
            <span>Category</span>
            <span>Components</span>
          </div>
          {SKILLS.map((g, i) => (
            <motion.div
              key={i}
              className="bom-row"
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: i * 0.05, ease: [0.16, 1, 0.3, 1] }}
            >
              <span className="bom-no">{String(i + 1).padStart(2, '0')}</span>
              <span className="bom-cat">{g.cat}</span>
              <span className="bom-items">
                {g.items.map(item => (
                  <span key={item} className="bom-item">{item}</span>
                ))}
              </span>
            </motion.div>
          ))}
        </div>
      </motion.div>

      <div className="sheet-title-block">
        <div className="stb-num">MS-05</div>
        <div>Parts Index</div>
      </div>
    </section>
  )
}

/* ══════════════════════════════
   CONTACT
══════════════════════════════ */
function Contact() {
  const sectionRef = useRef(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], [30, -30])

  return (
    <section className="contact-section" id="contact" ref={sectionRef}>
      <span className="reg-mark on-dark tl" aria-hidden /><span className="reg-mark on-dark br" aria-hidden />
      <motion.div className="contact-inner" style={{ y }}>

        <motion.div
          className="contact-left"
          initial={{ opacity: 0, x: -32 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
        >
          <p className="section-label">Contact</p>
          <MaskReveal className="contact-headline">
            Let's build<br />
            <em>something real.</em>
          </MaskReveal>
          <p className="contact-sub">
            Open to senior CV / ML / Backend engineering roles.<br />
            Bangalore or remote.
          </p>
          <p className="contact-footnote">
            Built with React + Vite, designed and shipped with AI-assisted development.
          </p>
        </motion.div>

        <motion.div
          className="contact-right"
          initial={{ opacity: 0, x: 32 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, delay: 0.1 }}
        >
          <a href="mailto:manojshendre.1202@gmail.com" className="contact-link">
            <span className="cl-label">Email</span>
            <span className="cl-value">manojshendre.1202@gmail.com →</span>
          </a>
          <a href="tel:+918884812422" className="contact-link">
            <span className="cl-label">Phone</span>
            <span className="cl-value">+91 88848 12422 →</span>
          </a>
          <div className="contact-link no-hover">
            <span className="cl-label">Location</span>
            <span className="cl-value">Bangalore, India</span>
          </div>
          <div className="contact-link no-hover">
            <span className="cl-label">Status</span>
            <span className="cl-value cl-available">
              <span className="cl-dot" /> Available for hire
            </span>
          </div>
        </motion.div>

      </motion.div>

      <div className="sheet-title-block on-dark">
        <div className="stb-num">MS-06</div>
        <div>Correspondence</div>
      </div>
    </section>
  )
}

/* ══════════════════════════════
   FOOTER
══════════════════════════════ */
function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="footer">
      <span className="footer-approved">Approved</span>
      <div className="footer-inner">
        <div className="footer-left">
          <span className="footer-logo">M<em>S</em></span>
          <p className="footer-copy">
            © {year} Manoj Shendre · Rev. {year}.01
          </p>
        </div>

        <p className="footer-note">
          Built with React · Designed with AI-assisted tools · Backend skills are all mine
        </p>

        <div className="footer-right">
          <a href="mailto:manojshendre.1202@gmail.com" className="footer-link">Email</a>
          <span className="footer-sep">·</span>
          <a href="tel:+918884812422" className="footer-link">Phone</a>
          <span className="footer-sep">·</span>
          <a href="https://github.com/ManojShendre1202" target="_blank" rel="noopener noreferrer" className="footer-link footer-link-dim">GitHub ↗</a>
          <span className="footer-sep">·</span>
          <a href="https://www.linkedin.com/in/manoj-shendre-a40b932b0/" target="_blank" rel="noopener noreferrer" className="footer-link footer-link-dim">LinkedIn ↗</a>
        </div>
      </div>
    </footer>
  )
}

/* ══════════════════════════════
   ROBOT WIDGET
══════════════════════════════ */
function RobotWidget() {
  const [mounted, setMounted] = useState(false)
  const [hovered, setHovered] = useState(false)
  const containerRef = useRef(null)
  const animRef      = useRef(null)

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 1000)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!mounted || !containerRef.current) return
    animRef.current = lottie.loadAnimation({
      container:     containerRef.current,
      animationData: robotData,
      renderer:      'svg',
      loop:          true,
      autoplay:      true,
    })
    return () => animRef.current?.destroy()
  }, [mounted])

  return (
    <div className="robot-widget">
      <a
        href="/readar/"
        target="_blank"
        rel="noopener noreferrer"
        className="robot-widget-link"
        title="Try Readar"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {mounted
          ? <div ref={containerRef} className={`robot-lottie-wrap ${hovered ? 'hovered' : ''}`} />
          : <div className="robot-widget-skeleton" />
        }
        <div className="robot-widget-label">
          <span className="robot-widget-dot" />
          Try Readar
        </div>
      </a>
    </div>
  )
}

/* ══════════════════════════════
   PORTFOLIO — page root
══════════════════════════════ */
export default function Portfolio() {
  return (
    <div className="portfolio-dark">
      <RobotWidget />
      <Navbar />
      <SidePanel />
      <main>
        <Intro />
        <Marquee />
        <About />
        <Marquee />
        <Experience />
        <Marquee />
        <Readar />
        <Marquee dark />
        <Skills />
        <Contact />
      </main>
      <Footer />
    </div>
  )
}
