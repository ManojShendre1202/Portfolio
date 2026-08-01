const BASE = '/api/readar'

export function getOrCreateClientId() {
  let id = localStorage.getItem('readar_client_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('readar_client_id', id)
  }
  return id
}

export async function getOrCreateSession(docId) {
  const res = await fetch(`${BASE}/session/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: getOrCreateClientId(), doc_id: docId }),
  })
  if (!res.ok) throw new Error(`Session create failed: ${res.status}`)
  return res.json()  // { chat_id, doc_id, active }
}

export async function startNewSession(docId) {
  const res = await fetch(`${BASE}/session/new/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: getOrCreateClientId(), doc_id: docId }),
  })
  if (!res.ok) throw new Error(`New session failed: ${res.status}`)
  return res.json()  // { chat_id, doc_id, active }
}

export async function getSessionTurns(chatId) {
  const res = await fetch(`${BASE}/session/${chatId}/turns/`)
  if (!res.ok) throw new Error(`Turns fetch failed: ${res.status}`)
  return res.json()  // { turns: [...] }
}

export async function listSessions(docId) {
  const params = new URLSearchParams({ client_id: getOrCreateClientId(), doc_id: docId })
  const res = await fetch(`${BASE}/sessions/?${params}`)
  if (!res.ok) throw new Error(`Sessions fetch failed: ${res.status}`)
  return res.json()  // { sessions: [{ chat_id, active, turn_count, first_question, updated_at }] }
}

export async function switchSession(chatId, docId) {
  const res = await fetch(`${BASE}/session/${chatId}/switch/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ client_id: getOrCreateClientId(), doc_id: docId }),
  })
  if (!res.ok) throw new Error(`Session switch failed: ${res.status}`)
  return res.json()  // { chat_id, doc_id, active }
}

export async function deleteSession(chatId, docId) {
  const params = new URLSearchParams({ client_id: getOrCreateClientId(), doc_id: docId })
  const res = await fetch(`${BASE}/session/${chatId}/delete/?${params}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`Session delete failed: ${res.status}`)
  return res.json()
}

export function docPageUrl(docId, chapter) {
  return `${BASE}/doc/${docId}/page/${chapter}/`
}
