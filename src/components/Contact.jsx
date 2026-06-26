import { motion } from 'framer-motion'
import './Contact.css'

export default function Contact() {
  return (
    <section className="contact-section" id="contact">
      <div className="contact-inner">

        <motion.div
          className="contact-left"
          initial={{ opacity: 0, x: -32 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7 }}
        >
          <p className="section-label">Contact</p>
          <h2 className="contact-headline">
            Let's build<br />
            <em>something real.</em>
          </h2>
          <p className="contact-sub">
            Open to senior CV / ML / Backend engineering roles.<br />
            Target: 25–28 LPA · Bangalore or remote.
          </p>
          <p className="contact-footnote">
            Built with React + Vite, designed and shipped with AI-assisted development.
            Because shipping fast is also a skill.
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

      </div>
    </section>
  )
}
