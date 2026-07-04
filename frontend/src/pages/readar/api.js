const BASE = '/api'

export function getOrCreateClientId() {
  let id = localStorage.getItem('readar_client_id')
  if (!id) {
    id = crypto.randomUUID()
    localStorage.setItem('readar_client_id', id)
  }
  return id
}

export async function uploadDrawing(file) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('client_id', getOrCreateClientId())

  const res = await fetch(`${BASE}/upload/`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) throw new Error(`Upload failed: ${res.status}`)
  const data = await res.json()
  return data.job_id
}

export async function fetchJob(jobId) {
  const res = await fetch(`${BASE}/job/${jobId}/`)
  if (!res.ok) throw new Error(`Job fetch failed: ${res.status}`)
  return res.json()
}

export async function fetchClientJobs() {
  const clientId = getOrCreateClientId()
  const res = await fetch(`${BASE}/jobs/?client_id=${clientId}`)
  if (!res.ok) throw new Error(`Jobs fetch failed: ${res.status}`)
  return res.json()  // { jobs: [...] }
}
