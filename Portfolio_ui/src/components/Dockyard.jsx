import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import './Dockyard.css'

const STEPS = [
  { num: '01', title: 'pipeline_config.py',  desc: 'Define queues, pipeline stages, and entry point. New domain in one file.' },
  { num: '02', title: 'workflow_stages.json', desc: 'Stage names and metadata. Must match pipeline keys exactly.' },
  { num: '03', title: 'Worker files',         desc: 'Each worker: run(task, update_queue) → TaskResult. That\'s the entire contract.' },
  { num: '04', title: 'Upload view',          desc: 'Django view sends TCP signal with stage name. Engine receives, dispatches.' },
  { num: '05', title: 'Review APIs',          desc: 'submit_validation and data endpoints for human-review gate stages.' },
  { num: '06', title: '__init__.py',          desc: 'Present in every new Python package. Easy to forget, always the last bug.' },
]

const PRINCIPLES = [
  {
    principle: 'Open / Closed Principle',
    source:    'Robert C. Martin — Clean Architecture',
    quote:     'Open for extension, closed for modification.',
    how:       'Engine files are never touched per domain. New behaviour is added only by writing new workers and configs.',
  },
  {
    principle: 'Single Responsibility',
    source:    'Robert C. Martin — Clean Code',
    quote:     'A module should have one, and only one, reason to change.',
    how:       'Each worker does exactly one stage. The dispatcher orchestrates. The pool executes. Zero overlap.',
  },
  {
    principle: 'Dependency Inversion',
    source:    'Robert C. Martin — Clean Architecture',
    quote:     'High-level modules should not depend on low-level modules. Both should depend on abstractions.',
    how:       'Engine depends only on BaseTask and TaskResult abstractions — never on concrete domain workers.',
  },
  {
    principle: 'Plugin Architecture',
    source:    'Martin Fowler — Patterns of Enterprise Application Architecture',
    quote:     'Define a fixed core and a flexible shell.',
    how:       'The engine is the fixed core. Every client domain is a plugin — dropped in without touching the core.',
  },
]

export default function Dockyard() {
  const ref = useRef(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start end', 'end start'] })
  const lineH = useTransform(scrollYProgress, [0.1, 0.8], ['0%', '100%'])

  return (
    <section className="dock-section" id="dockyard" ref={ref}>
      <div className="dock-inner">

        {/* header */}
        <motion.div
          className="dock-header"
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
        >
          <p className="section-label">Personal Project</p>
          <h2 className="section-title">Dockyard<br /><em>Workflow Engine</em></h2>
          <p className="dock-tagline">
            A domain-agnostic drawing processing engine —<br />
            built from first principles, designed to never be touched.
          </p>
        </motion.div>

        {/* story + stats */}
        <div className="dock-body">
          <motion.div
            className="dock-story"
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <p>
              Built over 6–9 months after multiple failed attempts.
              A <strong>domain-agnostic drawing processing engine</strong> — plugin architecture,
              custom Python worker pool with configurable concurrency, multi-stage pipelines
              with human-review gates, real-time WebSocket log streaming, crash recovery,
              and TCP signal-based job dispatch.
            </p>
            <p>
              The engine files are <strong>never touched</strong> when adding a new client domain.
              Drop in a config file, write workers, done. New domain onboarded in under 30 minutes.
            </p>
            <p>
              Powers several client projects across railways, shipbuilding,
              and automotive domains — the same core engine, entirely different domain logic.
            </p>

            <div className="dock-stats">
              {[
                { num: '30m', label: 'New domain\nonboard time' },
                { num: '0',   label: 'Engine files touched\nper new domain' },
                { num: '6',   label: 'Step onboarding\nchecklist' },
              ].map((s, i) => (
                <div key={i} className="dock-stat">
                  <span className="dock-stat-num">{s.num}</span>
                  <span className="dock-stat-label">{s.label}</span>
                </div>
              ))}
            </div>
          </motion.div>

          {/* 6-step onboarding */}
          <div className="dock-steps-wrap">
            <p className="dock-steps-title">6-Step Onboarding Checklist</p>

            {/* animated vertical line */}
            <div className="dock-line-track">
              <motion.div className="dock-line-fill" style={{ height: lineH }} />
            </div>

            <div className="dock-steps">
              {STEPS.map((s, i) => (
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

        {/* design principles — full width row */}
        <motion.div
          className="dock-principles"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <p className="dock-principles-title">Built on</p>
          <div className="dock-principles-grid">
            {PRINCIPLES.map((p, i) => (
              <motion.div
                key={i}
                className="dock-principle"
                initial={{ opacity: 0, y: 16 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-20px' }}
                transition={{ duration: 0.5, delay: i * 0.07 }}
              >
                <div className="dp-header">
                  <span className="dp-name">{p.principle}</span>
                  <span className="dp-source">{p.source}</span>
                </div>
                <p className="dp-quote">"{p.quote}"</p>
                <p className="dp-how">{p.how}</p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* open source note */}
        <motion.div
          className="dock-oss"
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <span className="dock-oss-label">Open Source</span>
          <p>GitHub release coming soon — clean extraction in progress.</p>
        </motion.div>

      </div>
    </section>
  )
}
