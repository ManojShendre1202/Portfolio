import './Footer.css'

export default function Footer() {
  const year = new Date().getFullYear()

  return (
    <footer className="footer">
      <div className="footer-inner">
        <div className="footer-left">
          <span className="footer-logo">M<em>S</em></span>
          <p className="footer-copy">
            © {year} Manoj Shendre. All rights reserved.
          </p>
        </div>

        <p className="footer-note">
          Built with React · Designed with AI-assisted tools · Backend skills are all mine 😄
        </p>

        <div className="footer-right">
          <a href="mailto:manojshendre.1202@gmail.com" className="footer-link">Email</a>
          <span className="footer-sep">·</span>
          <a href="tel:+918884812422" className="footer-link">Phone</a>
          <span className="footer-sep">·</span>
          <a href="#" className="footer-link footer-link-dim">GitHub ↗</a>
          <span className="footer-sep">·</span>
          <a href="#" className="footer-link footer-link-dim">LinkedIn ↗</a>
        </div>
      </div>
    </footer>
  )
}
