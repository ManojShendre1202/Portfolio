import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { visit } from 'unist-util-visit'
import { SUGGESTED_QUESTIONS, DOC_CHAPTERS } from './curatedDocs'
import { getOrCreateSession, startNewSession, getSessionTurns, listSessions, switchSession, deleteSession, fetchDocPage } from './api'
import { prepareDocPageHtml } from './docPageRender'
import { Icon } from './icons'
import './readar.css'

// remark plugin: turns literal "[n]" citation markers inside markdown text nodes into a
// dedicated inline node. This runs INSIDE the single markdown parse (rather than the old
// approach of pre-splitting the raw string on "[n]" and feeding each fragment through its
// own separate <ReactMarkdown>) — splitting the string made every fragment its own
// "paragraph", turning one flowing sentence with inline citations into a stack of
// disconnected blocks with a paragraph gap after every citation.
function remarkCitations() {
  return (tree) => {
    visit(tree, 'text', (node, index, parent) => {
      const re = /\[(\d+)\]/g
      if (!re.test(node.value)) return
      re.lastIndex = 0
      const out = []
      let last = 0
      let m
      while ((m = re.exec(node.value))) {
        if (m.index > last) out.push({ type: 'text', value: node.value.slice(last, m.index) })
        out.push({ type: 'citeMarker', n: Number(m[1]) })
        last = m.index + m[0].length
      }
      if (last < node.value.length) out.push({ type: 'text', value: node.value.slice(last) })
      parent.children.splice(index, 1, ...out)
      return index + out.length
    })
  }
}

// tells remark-rehype how to turn our custom `citeMarker` mdast node into real markup
const REMARK_REHYPE_OPTIONS = {
  handlers: {
    citeMarker: (_state, node) => ({
      type: 'element',
      tagName: 'sup',
      properties: { 'data-cite-n': node.n },
      children: [{ type: 'text', value: `[${node.n}]` }],
    }),
  },
}

// pulls the raw text out of a code element's children (string, array of
// strings/elements, or nested) so the copy button has something to copy —
// react-markdown hands code content as children, not a plain string prop
function textContent(node) {
  if (node == null) return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textContent).join('')
  if (node.props?.children != null) return textContent(node.props.children)
  return ''
}

// fenced code blocks: language badge + copy-to-clipboard button above the code
function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false)
  const codeEl = Array.isArray(children) ? children[0] : children
  const match = /language-(\w+)/.exec(codeEl?.props?.className || '')
  const code = textContent(codeEl?.props?.children).replace(/\n$/, '')

  function handleCopy() {
    navigator.clipboard?.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    })
  }

  return (
    <div className="rd-code-block">
      <div className="rd-code-block-header">
        <span className="rd-code-lang">{match ? match[1] : 'code'}</span>
        <button type="button" className="rd-code-copy" onClick={handleCopy}>
          <Icon name={copied ? 'check' : 'copy'} size={12} />
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  )
}

// `pre` renders through CodeBlock (language badge + copy button above the code, see
// above). `sup` intercepts our citation markers (data-cite-n) and wires them to the
// click handler; any other <sup> (real markdown superscript) just renders as-is.
// `p` is left as react-markdown's default — real block paragraphs, spaced by CSS
// margin (see .rd-ai-card p) — rather than manually injected <br/><br/>, which used
// to stack on top of adjacent elements' own margins (e.g. a code block right after a
// paragraph) and produce oversized gaps.
function mdComponents(citations, onCite) {
  return {
    pre: ({ children }) => <CodeBlock>{children}</CodeBlock>,
    sup: ({ children, ...rest }) => {
      const raw = rest['data-cite-n']
      if (raw == null) return <sup {...rest}>{children}</sup>
      const n = Number(raw)
      const cite = citations.find(c => c.n === n)
      return (
        <sup className="rd-cite" title={cite?.label} onClick={() => cite && onCite(cite)}>
          [{n}]
        </sup>
      )
    },
  }
}

function TraceStrip({ trace }) {
  const [open, setOpen] = useState(false)
  // older persisted turns (before trace['total'] was included in the write) won't
  // have a total — fall back to summing what we do have rather than showing "s"
  const total = trace.total ?? (trace.retrieve ?? 0) + (trace.gemini ?? 0)
  return (
    <div className="rd-trace">
      <button className="rd-trace-summary" onClick={() => setOpen(o => !o)}>
        <Icon name="sparkle" size={12} />
        <span>{total}s</span>
        <span className="rd-trace-dot" />
        <span>{trace.tokens} tokens</span>
        <span className="rd-trace-dot" />
        <span>{trace.retrieved} nodes</span>
        <span className={`rd-trace-chevron ${open ? 'open' : ''}`}>▾</span>
      </button>
      {open && (
        <div className="rd-trace-detail">
          <div className="rd-trace-row"><span>retrieve</span><span>{trace.retrieve}s</span></div>
          <div className="rd-trace-row"><span>gemini</span><span>{trace.gemini}s</span></div>
          <div className="rd-trace-row"><span>nodes retrieved</span><span>{trace.retrieved}</span></div>
          <div className="rd-trace-row"><span>nodes used in context</span><span>{trace.used}</span></div>
          <div className="rd-trace-row"><span>tokens</span><span>{trace.tokens}</span></div>
        </div>
      )}
    </div>
  )
}

// mock data shape: bullets = array of lines, each with inline [n] markers
function AiBullets({ bullets, citations, onCite }) {
  return (
    <ul className="rd-bullets">
      {bullets.map((b, i) => (
        <li key={i}><FormattedLine text={b} citations={citations} onCite={onCite} /></li>
      ))}
    </ul>
  )
}

// real streamed answers: a single text blob with inline [n] markers and markdown formatting
function CitedText({ text, citations, onCite }) {
  return (
    <div className="rd-cited-text"><FormattedLine text={text} citations={citations} onCite={onCite} /></div>
  )
}

// renders markdown (bold, inline/fenced code, lists, etc.) with [n] citation markers
// resolved inline as part of the same parse — see remarkCitations above
function FormattedLine({ text, citations, onCite }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkCitations]}
      remarkRehypeOptions={REMARK_REHYPE_OPTIONS}
      rehypePlugins={[rehypeHighlight]}
      components={mdComponents(citations, onCite)}
    >
      {text}
    </ReactMarkdown>
  )
}

export default function SplitView({ doc, onBack }) {
  const [chatId, setChatId]   = useState(null)
  const [turns, setTurns]     = useState([])
  const [input, setInput]     = useState('')
  const [chapter, setChapter] = useState(doc.startChapter)
  const [docHtml, setDocHtml] = useState(null)
  const [typing, setTyping]   = useState(false)
  const [docCollapsed, setDocCollapsed] = useState(false)
  const [historyCollapsed, setHistoryCollapsed] = useState(false)
  const [sessions, setSessions]         = useState([])
  const iframeRef               = useRef()
  const chatEndRef              = useRef()
  const wsRef                   = useRef(null)
  const pendingHighlight         = useRef(null)  // domId — applied once the target chapter finishes loading
  const pendingMessage           = useRef(null)  // question text queued for send once a freshly-created session's WS opens
  // typewriter reveal buffer — the backend streams real token chunks over the WS, but
  // Gemini's chunks can arrive in sentence-sized bursts. Decoupling "text received" from
  // "text shown" and draining it a few characters at a time gives a smooth, consistent
  // reveal regardless of how bursty the actual network chunks are.
  const streamRef = useRef({ buffer: '', timer: null, doneMsg: null })

  // ── session bootstrap: restore the last real conversation if one exists —
  //    never create a session just from loading the page. A session is only
  //    ever created lazily, on the first message actually sent (see sendMessage
  //    and handleNewChat), so an unopened/unused visit never shows up in history. ──
  useEffect(() => {
    let cancelled = false
    listSessions(doc.id)
      .then(({ sessions: list }) => {
        if (cancelled) return
        setSessions(list || [])
        const existing = (list || []).find(s => s.active) || (list || [])[0]
        if (existing && existing.turn_count > 0) {
          return switchSession(existing.chat_id, doc.id)
            .then(({ chat_id }) => {
              if (cancelled) return
              setChatId(chat_id)
              return getSessionTurns(chat_id)
            })
            .then(res => { if (!cancelled) setTurns(res?.turns || []) })
        }
        setChatId(null)
        setTurns([])
      })
      .catch(() => {
        if (cancelled) return
        setChatId(null)
        setTurns([])
      })
    return () => { cancelled = true }
  }, [doc.id])

  // ── open/reopen the chat WS whenever we have a real chat_id ──
  useEffect(() => {
    if (!chatId) return

    // Routed through nginx (location /ws/readar-chat/ in nginx.docker.conf),
    // same origin as the page — no separate port needed, and wss:// when the
    // page itself is https:// so the browser doesn't block a mixed-content WS.
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${wsProtocol}//${window.location.host}/ws/readar-chat/${chatId}`)

    wsRef.current = ws
    streamRef.current = { buffer: '', timer: null, doneMsg: null }  // fresh per connection

    function finalizeDone(msg) {
      setTurns(prev => {
        const next = [...prev]
        const last = next[next.length - 1]
        if (last && last.streaming) {
          next[next.length - 1] = {
            ...last,
            streaming: false,
            citations: msg.citations || [],
            trace: msg.trace || null,
          }
        }
        return next
      })
      setTyping(false)
      refreshSessions()  // pick up the updated title/turn-count now that a turn actually landed
    }

    // drains a few characters at a time on a fixed tick — the reveal speed the user
    // actually sees, independent of chunk size/arrival timing off the wire
    function pump() {
      const state = streamRef.current
      if (state.timer) return
      state.timer = setInterval(() => {
        const s = streamRef.current
        if (s.buffer.length > 0) {
          // reveal speed scales with backlog — smooth 3-char steps for normal
          // token pacing, but catches up quickly instead of trailing the actual
          // response by many seconds once a long/code-heavy answer has already
          // finished generating and the whole thing is sitting in the buffer
          const step = Math.max(3, Math.ceil(s.buffer.length / 20))
          const chunk = s.buffer.slice(0, step)
          s.buffer = s.buffer.slice(step)
          setTurns(prev => {
            const next = [...prev]
            const last = next[next.length - 1]
            if (last && last.role === 'ai' && last.streaming) {
              next[next.length - 1] = { ...last, text: last.text + chunk }
            }
            return next
          })
        }
        if (s.buffer.length === 0) {
          clearInterval(s.timer)
          s.timer = null
          if (s.doneMsg) {
            const doneMsg = s.doneMsg
            s.doneMsg = null
            finalizeDone(doneMsg)
          }
        }
      }, 18)
    }

    ws.onopen = () => {
      if (pendingMessage.current) {
        ws.send(JSON.stringify({ question: pendingMessage.current }))
        pendingMessage.current = null
      }
    }

    ws.onmessage = (e) => {
      let msg
      try { msg = JSON.parse(e.data) } catch { return }

      if (msg.type === 'token') {
        setTyping(false)
        setTurns(prev => {
          const last = prev[prev.length - 1]
          if (last && last.role === 'ai' && last.streaming) return prev
          return [...prev, { role: 'ai', text: '', streaming: true, citations: [] }]
        })
        streamRef.current.buffer += msg.text
        pump()
      }

      if (msg.type === 'done') {
        const state = streamRef.current
        if (state.buffer.length > 0 || state.timer) {
          state.doneMsg = msg  // finalize once the reveal buffer finishes draining
        } else {
          finalizeDone(msg)
        }
      }

      if (msg.type === 'error') {
        setTurns(prev => [...prev, { role: 'ai', text: msg.text }])
        setTyping(false)
      }
    }

    ws.onerror = () => {
      setTurns(prev => [...prev, { role: 'ai', text: 'Connection error — could not reach chat server.' }])
      setTyping(false)
    }

    return () => {
      ws.close()
      wsRef.current = null
      if (streamRef.current.timer) clearInterval(streamRef.current.timer)
    }
  }, [chatId])

  function refreshSessions() {
    listSessions(doc.id).then(({ sessions }) => setSessions(sessions || [])).catch(() => {})
  }

  // ── keep the history list in sync whenever the active session changes ──
  useEffect(() => {
    if (!chatId) return
    refreshSessions()
  }, [chatId, doc.id])

  function handleNewChat() {
    // don't touch the backend yet — an empty session with no turns would otherwise
    // show up in the history list the moment this is clicked. The real session is
    // created lazily, on the first message actually sent (see sendMessage).
    setChatId(null)
    setTurns([])
  }

  async function handleSwitchSession(targetChatId) {
    if (targetChatId === chatId) return
    try {
      const { chat_id } = await switchSession(targetChatId, doc.id)
      const { turns: restored } = await getSessionTurns(chat_id)
      setChatId(chat_id)  // effect above reopens the WS for the restored session
      setTurns(restored || [])
    } catch {
      // backend unreachable — leave current session as-is
    }
  }

  async function handleDeleteSession(e, targetChatId) {
    e.stopPropagation()  // don't trigger the item's switch click
    if (!window.confirm('Delete this conversation? This cannot be undone.')) return

    try {
      await deleteSession(targetChatId, doc.id)
    } catch (err) {
      console.error('Delete session failed:', err)
      alert('Could not delete this conversation — backend unreachable or out of date. Check the console.')
      return
    }
    setSessions(prev => prev.filter(s => s.chat_id !== targetChatId))

    if (targetChatId === chatId) {
      // deleted the session we were viewing — fall back to a fresh one
      try {
        const { chat_id } = await getOrCreateSession(doc.id)
        const { turns: restored } = await getSessionTurns(chat_id)
        setChatId(chat_id)
        setTurns(restored || [])
      } catch {
        setChatId(null)
        setTurns([])
      }
    }
  }

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns])

  // ── fetch + client-side-render the source doc page whenever the chapter changes ──
  useEffect(() => {
    let cancelled = false
    setDocHtml(null)
    fetchDocPage(doc.id, chapter)
      .then(({ html, base_href }) => {
        if (cancelled) return
        setDocHtml(prepareDocPageHtml(html, base_href))
      })
      .catch(() => { if (!cancelled) setDocHtml('<p style="padding:2rem;font-family:sans-serif">Could not load this page.</p>') })
    return () => { cancelled = true }
  }, [doc.id, chapter])

  // ── messages from the embedded doc page: chapter-link clicks stay inside the app ──
  useEffect(() => {
    function onMessage(e) {
      if (e.data?.type === 'navigate-chapter' && e.data.chapter) {
        setChapter(e.data.chapter)
      }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [])

  function highlight(domId) {
    iframeRef.current?.contentWindow?.postMessage({ type: 'highlight', id: domId }, '*')
  }

  function handleCite(cite) {
    // mock citations use domId (singular); real backend citations use domIds (array)
    const domId = cite.domId || cite.domIds?.[0]
    if (!domId) return
    if (cite.chapter && cite.chapter !== chapter) {
      pendingHighlight.current = domId
      setChapter(cite.chapter)  // iframe onLoad below fires the highlight once it's ready
    } else {
      highlight(domId)
    }
  }

  function handleFrameLoad() {
    if (pendingHighlight.current) {
      highlight(pendingHighlight.current)
      pendingHighlight.current = null
    }
  }

  function sendMessage(text) {
    if (!text.trim()) return
    setInput('')
    setTurns(prev => [...prev, { role: 'user', text }])
    setTyping(true)

    if (chatId && wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ question: text }))
      return
    }

    if (!chatId) {
      // first message of a fresh "New chat" — create the session now, then
      // send once its WS connects (see the ws.onopen handler above)
      pendingMessage.current = text
      startNewSession(doc.id)
        .then(({ chat_id }) => setChatId(chat_id))
        .catch(() => {
          pendingMessage.current = null
          setTurns(prev => [...prev, { role: 'ai', text: 'Not connected — please wait a moment and try again.' }])
          setTyping(false)
        })
      return
    }

    setTurns(prev => [...prev, { role: 'ai', text: 'Not connected — please wait a moment and try again.' }])
    setTyping(false)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  const chips = SUGGESTED_QUESTIONS[doc.id] || []
  // a session only belongs in history once it actually has a message in it —
  // a freshly-created, not-yet-answered session stays invisible until then
  const visibleSessions = sessions.filter(s => s.turn_count > 0)

  return (
    <div className={`rd-split ${docCollapsed ? 'doc-collapsed' : ''}`}>
      {/* ── LEFT: rendered source doc ── */}
      <div className="rd-split-left">
        <div className="rd-split-left-header">
          <button className="rd-split-back" onClick={onBack}>
            <Icon name="back" size={13} /> {doc.title}
          </button>
          <div className="rd-split-left-header-right">
            <select
              className="rd-chapter-select"
              value={chapter}
              onChange={e => setChapter(e.target.value)}
            >
              {(DOC_CHAPTERS[doc.id] || []).map(c => (
                <option key={c.slug} value={c.slug}>{c.label}</option>
              ))}
            </select>
            <button
              className="rd-doc-collapse-btn"
              onClick={() => setDocCollapsed(true)}
              title="Hide document"
            >
              <Icon name="chevronLeft" size={14} />
            </button>
          </div>
        </div>
        {docHtml == null ? (
          <div className="rd-doc-frame-loading">Loading…</div>
        ) : (
          <iframe
            key={chapter}
            ref={iframeRef}
            className="rd-doc-frame"
            title="source document"
            srcDoc={docHtml}
            onLoad={handleFrameLoad}
          />
        )}
      </div>

      {docCollapsed && (
        <button
          className="rd-doc-expand-rail"
          onClick={() => setDocCollapsed(false)}
          title="Show document"
        >
          <Icon name="panelLeft" size={14} />
          <span>{doc.title}</span>
        </button>
      )}

      {/* ── RIGHT: chat sidebar + conversation ── */}
      <div className="rd-split-right rd-theme-dark-glass">
        {!historyCollapsed && (
          <aside className="rd-chat-sidebar">
            <div className="rd-sidebar-top">
              <button className="rd-new-chat-btn" onClick={handleNewChat}>
                <Icon name="plus" size={13} /> New chat
              </button>
              <button
                className="rd-history-collapse-btn"
                onClick={() => setHistoryCollapsed(true)}
                title="Hide history"
              >
                <Icon name="chevronLeft" size={14} />
              </button>
            </div>
            <div className="rd-sidebar-label">
              <Icon name="book" size={12} /> History
            </div>
            <div className="rd-sidebar-list">
              {visibleSessions.length === 0 ? (
                <div className="rd-history-empty">No past sessions yet</div>
              ) : (
                visibleSessions.map(s => (
                  <div
                    key={s.chat_id}
                    className={`rd-history-item ${s.chat_id === chatId ? 'active' : ''}`}
                    onClick={() => handleSwitchSession(s.chat_id)}
                  >
                    <div className="rd-history-item-text">
                      <span className="rd-history-item-title">
                        {s.first_question || 'New conversation'}
                      </span>
                      <span className="rd-history-item-meta">
                        {s.turn_count} turns · {new Date(s.updated_at).toLocaleDateString()}
                      </span>
                    </div>
                    <button
                      className="rd-history-item-delete"
                      title="Delete this conversation"
                      onClick={(e) => handleDeleteSession(e, s.chat_id)}
                    >
                      <Icon name="trash" size={13} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </aside>
        )}

        {historyCollapsed && (
          <button
            className="rd-history-expand-rail"
            onClick={() => setHistoryCollapsed(false)}
            title="Show history"
          >
            <Icon name="panelLeft" size={14} />
            <span>History</span>
          </button>
        )}

        <div className="rd-chat-main">
          <div className="rd-chat-area">
            {turns.length === 0 && !typing && (
              <div className="rd-chat-empty">
                <Icon name="sparkle" size={20} />
                <p>Ask anything about this document to get started.</p>
              </div>
            )}
            {turns.map((m, i) => (
              <div key={i} className={`rd-msg ${m.role}`}>
                {m.role === 'ai' && <div className="rd-msg-avatar">R</div>}
                <div className={`rd-msg-content ${m.role === 'ai' ? 'rd-ai-card' : ''}`}>
                  {m.bullets?.length > 0 ? (
                    <>
                      <FormattedLine text={m.text} citations={m.citations || []} onCite={handleCite} />
                      <AiBullets bullets={m.bullets} citations={m.citations || []} onCite={handleCite} />
                    </>
                  ) : m.citations?.length > 0 ? (
                    <CitedText text={m.text} citations={m.citations} onCite={handleCite} />
                  ) : (
                    <>
                      <FormattedLine text={m.text} citations={m.citations || []} onCite={handleCite} />
                      {m.streaming && <span className="rd-cursor" />}
                    </>
                  )}
                  {m.trace && <TraceStrip trace={m.trace} />}
                </div>
              </div>
            ))}
            {typing && (
              <div className="rd-msg ai">
                <div className="rd-msg-avatar">R</div>
                <div className="rd-msg-content rd-ai-card">
                  <div className="rd-typing-dots"><span /><span /><span /></div>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="rd-input-wrap">
            {chips.length > 0 && (
              <div className="rd-chip-row">
                {chips.map(q => (
                  <button key={q} className="rd-chip" onClick={() => sendMessage(q)}>{q}</button>
                ))}
              </div>
            )}
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
                <Icon name="send" size={14} className="rd-send-icon" />
              </button>
            </div>
            <div className="rd-attribution">
              Sourced from{' '}
              {doc.sourceUrl
                ? <a href={doc.sourceUrl} target="_blank" rel="noopener noreferrer">{doc.source}</a>
                : doc.source}
              {' '}· not affiliated with or endorsed by the original publisher · personal interview/portfolio demo
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
