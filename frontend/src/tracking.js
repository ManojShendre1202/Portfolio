// First-party pageview tracking — posts to our own Django backend, which
// stores one PageView row (see api/core/tracking_views.py). Identity is a
// server-issued HttpOnly cookie (pv_vid), so nothing is generated or stored
// here, and no IP / fingerprint is collected.

const ENDPOINT = '/api/track/'

// Dev builds and local previews shouldn't pollute the real numbers.
const IS_LOCAL = ['localhost', '127.0.0.1', '[::1]'].includes(window.location.hostname)

// document.referrer only describes how the visitor *arrived*; for in-app
// route changes it's still that original referrer, so send it once.
let referrerSent = false

export function trackPageView(path) {
  if (IS_LOCAL) return
  const referrer = referrerSent ? '' : document.referrer
  referrerSent = true

  fetch(ENDPOINT, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path, referrer }),
    keepalive: true,
  }).catch(() => {})
}

// Visit the site once with ?notrack=1 on each of your own devices to stop
// counting that browser; ?notrack=0 turns counting back on.
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
    console.info(off ? '[tracking] this browser is now excluded' : '[tracking] this browser is counted again')
  } catch {
    // best effort
  }
  return off
}
