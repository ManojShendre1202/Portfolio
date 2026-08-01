import { Link } from 'react-router-dom'
import { CURATED_DOCS } from './curatedDocs'
import { Icon } from './icons'
import './readar.css'

export default function DocPicker({ onSelect }) {
  return (
    <div className="rd-picker rd-theme-dark-glass">
      <p className="rd-logomark">Read<em>ar</em></p>

      <h1 className="rd-picker-title">Pick a document.<br /><em>Ask anything.</em></h1>
      <p className="rd-picker-sub">
        Curated, pre-verified documents only — no upload. Every one of these has already
        been parsed, ingested, and stress-tested end-to-end.
      </p>

      <div className="rd-doc-cards">
        {CURATED_DOCS.map(doc => (
          <button
            key={doc.id}
            className={`rd-doc-card ${!doc.ready ? 'disabled' : ''}`}
            onClick={() => doc.ready && onSelect(doc)}
            disabled={!doc.ready}
          >
            <div className="rd-doc-card-icon"><Icon name={doc.type === 'html' ? 'globe' : 'pdf'} size={18} /></div>
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
    </div>
  )
}
