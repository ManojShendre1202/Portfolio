import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { getActions, getWelcomeMessage, getFileEmoji, fmtSize } from './readarData'
import './readar.css'

export default function ChatApp({ docs, onNewFile }) {
  const [activeId, setActiveId]   = useState(docs[docs.length - 1]?.id)
  const [messages, setMessages]   = useState({})
  const [input, setInput]         = useState('')
  const [typing, setTyping]       = useState(false)
  const chatEndRef                = useRef()
  const fileInputRef              = useRef()
  const wsRef                     = useRef(null)

  const activeDoc = docs.find(d => d.id === activeId)

  // Welcome message when a new doc is activated
  useEffect(() => {
    if (!activeDoc) return
    if (messages[activeDoc.id]) return
    const welcome = getWelcomeMessage(activeDoc.type, activeDoc.name)
    setMessages(prev => ({ ...prev, [activeDoc.id]: [{ role: 'ai', text: welcome }] }))
  }, [activeDoc?.id])

  // Switch to latest doc when docs list grows
  useEffect(() => {
    if (docs.length) setActiveId(docs[docs.length - 1].id)
  }, [docs.length])

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, typing])

  // Open/reopen chat WS when active doc changes
  useEffect(() => {
    if (!activeDoc) return

    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }

    const ws = new WebSocket(`ws://${window.location.host}/ws/chat/${activeDoc.id}`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      let msg
      try { msg = JSON.parse(e.data) } catch { return }

      if (msg.type === 'token') {
        // Append token to the last AI message (streaming)
        setMessages(prev => {
          const docMsgs = [...(prev[activeDoc.id] || [])]
          const last    = docMsgs[docMsgs.length - 1]
          if (last && last.role === 'ai' && last.streaming) {
            docMsgs[docMsgs.length - 1] = { ...last, text: last.text + msg.text }
          } else {
            docMsgs.push({ role: 'ai', text: msg.text, streaming: true })
          }
          return { ...prev, [activeDoc.id]: docMsgs }
        })
        setTyping(false)
      }

      if (msg.type === 'done') {
        // Mark last message as no longer streaming
        setMessages(prev => {
          const docMsgs = [...(prev[activeDoc.id] || [])]
          const last    = docMsgs[docMsgs.length - 1]
          if (last && last.streaming) {
            docMsgs[docMsgs.length - 1] = { ...last, streaming: false }
          }
          return { ...prev, [activeDoc.id]: docMsgs }
        })
        setTyping(false)
      }

      if (msg.type === 'error') {
        setMessages(prev => ({
          ...prev,
          [activeDoc.id]: [...(prev[activeDoc.id] || []), { role: 'ai', text: `Error: ${msg.text}` }],
        }))
        setTyping(false)
      }
    }

    ws.onerror = () => {
      setMessages(prev => ({
        ...prev,
        [activeDoc.id]: [...(prev[activeDoc.id] || []), { role: 'ai', text: 'Connection error — could not reach chat server.' }],
      }))
      setTyping(false)
    }

    return () => { ws.close(); wsRef.current = null }
  }, [activeDoc?.id])

  function sendMessage(text) {
    if (!text.trim() || !activeDoc) return
    setInput('')

    setMessages(prev => ({
      ...prev,
      [activeDoc.id]: [...(prev[activeDoc.id] || []), { role: 'user', text }],
    }))

    setTyping(true)

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ question: text }))
    } else {
      setMessages(prev => ({
        ...prev,
        [activeDoc.id]: [...(prev[activeDoc.id] || []), { role: 'ai', text: 'Not connected — please wait a moment and try again.' }],
      }))
      setTyping(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const currentMessages = messages[activeDoc?.id] || []
  const actions         = activeDoc ? getActions(activeDoc.type) : []

  return (
    <div className="rd-app">
      {/* ── LEFT PANEL ── */}
      <div className="rd-left">
        <div className="rd-left-header">
          <div className="rd-left-logo">Read<em>ar</em></div>
          <button className="rd-btn-new" onClick={() => fileInputRef.current.click()}>
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.txt,.png,.jpg,.jpeg,.webp,.tiff,.xlsx,.xls,.csv,.dxf"
              onChange={e => { if (e.target.files[0]) onNewFile(e.target.files[0]) }}
              style={{ display: 'none' }}
            />
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            New document
          </button>
        </div>

        <div className="rd-docs-section">
          <p className="rd-docs-label">Documents</p>
          {docs.map(doc => (
            <div
              key={doc.id}
              className={`rd-doc-item ${doc.id === activeId ? 'active' : ''}`}
              onClick={() => setActiveId(doc.id)}
            >
              <div className="rd-doc-icon">{doc.emoji}</div>
              <div className="rd-doc-info">
                <div className="rd-doc-name">{doc.name}</div>
                <div className="rd-doc-meta">{doc.type} · {doc.size}</div>
              </div>
            </div>
          ))}
        </div>

        <div className="rd-left-footer">
          <Link to="/" className="rd-back-link">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg>
            Portfolio
          </Link>
        </div>
      </div>

      {/* ── RIGHT PANEL ── */}
      <div className="rd-right">
        <div className="rd-action-bar">
          <p className="rd-action-label">Suggested actions</p>
          <div className="rd-action-cards">
            {actions.map(a => (
              <button key={a.label} className="rd-action-card" onClick={() => sendMessage(a.label)}>
                <span>{a.emoji}</span>{a.label}
              </button>
            ))}
          </div>
        </div>

        <div className="rd-chat-area">
          {currentMessages.map((m, i) => (
            <div key={i} className={`rd-msg ${m.role}`}>
              <div className="rd-msg-avatar">{m.role === 'ai' ? 'R' : 'U'}</div>
              <div className="rd-msg-bubble">
                {m.text}
                {m.streaming && <span className="rd-cursor" />}
              </div>
            </div>
          ))}
          {typing && (
            <div className="rd-msg ai">
              <div className="rd-msg-avatar">R</div>
              <div className="rd-msg-bubble">
                <div className="rd-typing-dots"><span /><span /><span /></div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        <div className="rd-input-wrap">
          <div className="rd-input-row">
            <textarea
              className="rd-input"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask anything about this document..."
              rows={1}
            />
            <button className="rd-send-btn" onClick={() => sendMessage(input)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
