import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './Terminal.css'

const LINES = [
  { delay: 300,  text: '$ connecting to manojshendre.dev...',  type: 'cmd'  },
  { delay: 950,  text: '  ✓ connection established',           type: 'ok'   },
  { delay: 1400, text: '',                                      type: 'gap'  },
  { delay: 1600, text: '$ loading systems...',                 type: 'cmd'  },
  { delay: 2200, text: '  ✓ drawing processing pipeline       [online]',   type: 'ok'   },
  { delay: 2750, text: '  ✓ computer vision engine            [online]',   type: 'ok'   },
  { delay: 3300, text: '  ✓ satellite change detection        [standby]',  type: 'warn' },
  { delay: 3900, text: '',                                      type: 'gap'  },
  { delay: 4100, text: '$ fetching engineer profile...',       type: 'cmd'  },
  { delay: 4700, text: '  ✓ 2 yrs · 10 production projects',  type: 'ok'   },
  { delay: 5200, text: '  ✓ railways · ships · automotive',   type: 'ok'   },
  { delay: 5700, text: '',                                      type: 'gap'  },
  { delay: 5900, text: '$ ready.',                             type: 'cmd'  },
]

export default function Terminal({ onDone }) {
  const [lines,      setLines]      = useState([])
  const [showCursor, setShowCursor] = useState(true)
  const [exiting,    setExiting]    = useState(false)

  useEffect(() => {
    const timers = LINES.map((line, i) =>
      setTimeout(() => setLines(prev => [...prev, { ...line, id: i }]), line.delay)
    )
    const cursorTimer = setInterval(() => setShowCursor(p => !p), 530)
    const exitTimer   = setTimeout(() => {
      setExiting(true)
      setTimeout(onDone, 900)
    }, LINES[LINES.length - 1].delay + 1300)

    return () => {
      timers.forEach(clearTimeout)
      clearInterval(cursorTimer)
      clearTimeout(exitTimer)
    }
  }, [onDone])

  return (
    <AnimatePresence>
      {!exiting && (
        <motion.div
          className="term-overlay"
          exit={{ opacity: 0, scale: 0.97, filter: 'blur(8px)' }}
          transition={{ duration: 0.8, ease: [0.76, 0, 0.24, 1] }}
        >
          <motion.div
            className="term-window"
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, ease: [0.25, 0.1, 0.25, 1] }}
          >
            <div className="term-bar">
              <div className="term-dots">
                <span className="td red" /><span className="td yellow" /><span className="td green" />
              </div>
              <span className="term-title">manojshendre.dev — zsh</span>
              <div style={{ width: 52 }} />
            </div>
            <div className="term-body">
              {lines.map(line => (
                <motion.div
                  key={line.id}
                  className={`tl tl-${line.type}`}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  {line.text}
                </motion.div>
              ))}
              <span className={`tcursor ${showCursor ? 'on' : ''}`}>▋</span>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
