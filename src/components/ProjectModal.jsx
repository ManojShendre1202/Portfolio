import { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import './ProjectModal.css'

export default function ProjectModal({ project, onClose }) {
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
          {/* close */}
          <button className="modal-close" onClick={onClose}>
            <span>✕</span> <span className="modal-close-label">ESC</span>
          </button>

          {/* header */}
          <div className="modal-header">
            <div className="modal-meta">
              <span className="modal-num">{project.num}</span>
              <span className="modal-client">{project.client}</span>
              {project.solo && (
                <span className="modal-solo">
                  {project.lead ? 'Project Lead' : 'Solo Delivery'}
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

          {/* body */}
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
