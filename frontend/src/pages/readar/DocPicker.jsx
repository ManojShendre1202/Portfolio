import { Link } from 'react-router-dom'
import { CURATED_DOCS } from './curatedDocs'
import { Icon } from './icons'
import './readar.css'

function DocLogo({ doc }) {
  if (!doc.logoDomain) {
    return <div className="rd-doc-card-icon"><Icon name={doc.type === 'html' ? 'globe' : 'pdf'} size={18} /></div>
  }
  return (
    <div className="rd-doc-card-icon rd-doc-card-icon-logo">
      <img
        src={`https://www.google.com/s2/favicons?sz=128&domain=${doc.logoDomain}`}
        alt=""
        onError={e => { e.currentTarget.style.display = 'none'; e.currentTarget.nextSibling.style.display = 'flex' }}
      />
      <span className="rd-doc-card-icon-fallback"><Icon name={doc.type === 'html' ? 'globe' : 'pdf'} size={18} /></span>
    </div>
  )
}

export default function DocPicker({ onSelect }) {
  return (
    <div className="rd-picker rd-theme-dark-glass">
      <p className="rd-logomark">Read<em>ar</em></p>

      <h1 className="rd-picker-title">Pick a document.<br /><em>Ask anything.</em></h1>
      <p className="rd-picker-sub">
        Each card below is a real developer documentation site you can have a conversation
        with — ask a question, get an answer grounded in the actual text, and jump straight
        to the exact passage it came from.
      </p>

      <div className="rd-doc-cards">
        {CURATED_DOCS.map(doc => (
          <button
            key={doc.id}
            className={`rd-doc-card ${!doc.ready ? 'disabled' : ''}`}
            onClick={() => doc.ready && onSelect(doc)}
            disabled={!doc.ready}
          >
            <DocLogo doc={doc} />
            <div className="rd-doc-card-title">{doc.title}</div>
            <div className="rd-doc-card-source">{doc.source}</div>
            <div className="rd-doc-card-hook">{doc.hook}</div>
            {!doc.ready && <div className="rd-doc-card-badge">Coming soon</div>}
          </button>
        ))}
      </div>

      <Link to="/" className="rd-back-link rd-picker-back">
        <Icon name="back" size={13} />
        Portfolio
      </Link>

      <p className="rd-picker-credits">
        Logos and icons shown are trademarks of their respective owners, used here for
        source identification only — Readar is an independent portfolio demo, not
        affiliated with or endorsed by any of them.
      </p>
    </div>
  )
}
