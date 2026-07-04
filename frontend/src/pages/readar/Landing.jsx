import { useRef } from 'react'
import { SAMPLES } from './readarData'
import './readar.css'

export default function Landing({ onFile }) {
  const inputRef = useRef()

  function handleFileInput(e) {
    if (e.target.files[0]) onFile(e.target.files[0])
  }

  function loadSample(key) {
    const s = SAMPLES[key]
    onFile({ name: s.name, size: s.size, _sample: s._sample })
  }

  return (
    <div className="rd-landing">
      <p className="rd-logomark">Read<em>ar</em></p>

      <h1 className="rd-hero-title">
        Upload <em>anything.</em><br />Ask anything.
      </h1>
      <p className="rd-hero-sub">
        Drop any file — PDF, image, spreadsheet, DXF drawing.<br />
        Readar reads it. You ask questions.
      </p>

      <label className="rd-upload-trigger">
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.webp,.tiff,.xlsx,.xls,.csv,.dxf"
          onChange={handleFileInput}
        />
        <div className="rd-upload-ring">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#ff4d00" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
        </div>
        <span className="rd-upload-hint">Click to upload</span>
      </label>

      <p className="rd-samples-label">or try a sample</p>
      <div className="rd-samples">
        <div className="rd-sample-pill" onClick={() => loadSample('resume')}><span>📄</span> Resume</div>
        <div className="rd-sample-pill" onClick={() => loadSample('paper')}><span>📰</span> Research Paper</div>
        <div className="rd-sample-pill" onClick={() => loadSample('image')}><span>🖼️</span> Random Image</div>
      </div>

      <p className="rd-drop-hint">or drop a file anywhere</p>
    </div>
  )
}
