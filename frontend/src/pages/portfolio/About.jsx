import { motion } from 'framer-motion'
import './About.css'

const reveal = (delay = 0) => ({
  initial:    { opacity: 0, y: 48, filter: 'blur(6px)' },
  whileInView:{ opacity: 1, y: 0,  filter: 'blur(0px)' },
  viewport:   { once: true, margin: '-60px' },
  transition: { duration: 0.85, delay, ease: [0.16, 1, 0.3, 1] },
})

export default function About() {
  return (
    <section className="about-section" id="about">
      <div className="about-inner">

        <motion.div className="about-label-col" {...reveal(0)}>
          <p className="section-label">About</p>
          <div className="about-accent-line" />
        </motion.div>

        <div className="about-content">
          <motion.h2 className="about-headline" {...reveal(0.1)}>
            Aeronautical engineer<br />
            <em>who builds CV systems</em>
          </motion.h2>

          <motion.div className="about-body" {...reveal(0.2)}>
            <p>
              I graduated in Aeronautical Engineering — then pivoted into Computer Vision
              because the aerospace background is a superpower when your job is making
              machines read engineering drawings.
            </p>
            <p>
              In 2 years at Kynea Solutions, I've solo-delivered or led 7 of 10 client
              projects across Indian Railways, L&T Shipbuilding, Mahindra Aerospace, Spark
              Minda, Hubbell, SASMOS, and Goa Shipyard.
            </p>
            <p>
              I also built <strong>Dockyard</strong> — a domain-agnostic drawing processing
              engine from scratch that now powers client projects.
            </p>
          </motion.div>

          <motion.div className="about-cards" {...reveal(0.3)}>
            {[
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
                title: '2 Publications',
                sub:   'Divergence in airplane wings (Int. Journal) · Human color perception (Nature, under review)',
              },
            ].map((c, i) => (
              <div className="abt-card" key={i}>
                <span className="abt-card-label">{c.label}</span>
                <p className="abt-card-title">{c.title}</p>
                <p className="abt-card-sub">{c.sub}</p>
              </div>
            ))}
          </motion.div>
        </div>

      </div>
    </section>
  )
}
