// First-party pageview tracking — posts to our own Django backend, which
// stores one PageView row (see api/core/tracking_views.py). Identity is a
// server-issued HttpOnly cookie (pv_vid), so nothing is generated or stored
// here. No IP or fingerprint is stored: the three extra values sent with a
// view (webdriver flag, screen width/height) are used once, server-side, to
// spot automated browsers, and are not saved.

const ENDPOINT = '/api/track/'

// Dev builds and local previews shouldn't pollute the real numbers.
const IS_LOCAL = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)

// document.referrer only describes how the visitor *arrived*; for in-app
// route changes it's still that original referrer, so send it once.
let referrerSent = false

// A view only becomes "genuine" once the person has been on the page for a
// few seconds AND actually touched it. Scripts that just load the page never do.
const MIN_DWELL_MS = 3000
const INTERACTION_EVENTS = ['pointermove', 'pointerdown', 'keydown', 'scroll', 'wheel', 'touchstart']
let disarmEngagement = null

function armEngagement(path) {
  if (disarmEngagement) disarmEngagement()   // route changed before the last one qualified

  let waited = false
  let interacted = false
  let sent = false

  const cleanup = () => {
    clearTimeout(timer)
    INTERACTION_EVENTS.forEach(e => window.removeEventListener(e, onInteract))
    if (disarmEngagement === cleanup) disarmEngagement = null
  }

  const trySend = () => {
    if (sent || !waited || !interacted) return
    sent = true
    cleanup()
    fetch(`${ENDPOINT}engaged/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
      keepalive: true,
    }).catch(() => {})
  }

  const onInteract = () => { interacted = true; trySend() }
  const timer = setTimeout(() => { waited = true; trySend() }, MIN_DWELL_MS)

  INTERACTION_EVENTS.forEach(e => window.addEventListener(e, onInteract, { passive: true }))
  disarmEngagement = cleanup
}

export function trackPageView(path) {
  if (IS_LOCAL) return
  const referrer = referrerSent ? '' : document.referrer
  referrerSent = true

  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      path,
      referrer,
      webdriver: navigator.webdriver === true,
      sw: window.screen ? window.screen.width : null,
      sh: window.screen ? window.screen.height : null,
    }),
    keepalive: true,
  }).catch(() => {})

  armEngagement(path)
}

// Visit the site once with ?notrack=1 on each of your own devices to mark
// that browser as yours (its visits are labelled "you" and not counted);
// ?notrack=0 turns counting back on. Logging in to /admin/ in a browser does
// the same thing automatically.
export async function applyOptOutFromUrl(search) {
  const flag = new URLSearchParams(search).get('notrack')
  if (flag === null) return false
  const off = flag !== '0'
  try {
    await fetch(`${ENDPOINT}optout/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ off }),
    })
    console.info(off ? '[tracking] this browser is now marked as yours' : '[tracking] this browser is counted again')
  } catch {
    // best effort
  }
  return off
}
