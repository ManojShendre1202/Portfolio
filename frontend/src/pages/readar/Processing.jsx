import { useEffect, useRef, useState } from 'react'
import './readar.css'

export default function Processing({ fileName, jobId, onDone }) {
  const [logs, setLogs]     = useState([])
  const [error, setError]   = useState(null)
  const logsEndRef          = useRef()

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  useEffect(() => {
    if (!jobId) return   // still waiting for upload to return job_id

    const ws = new WebSocket(`ws://${window.location.host}/ws/revision/${jobId}`)

    ws.onmessage = (e) => {
      let msg
      try { msg = JSON.parse(e.data) } catch { return }

      if (msg.type === 'log') {
        setLogs(prev => [...prev, msg.text])
      }

      if (msg.type === 'done') {
        if (msg.status === 'failed') {
          setError(msg.error || 'Processing failed')
        } else {
          onDone(jobId)
        }
        ws.close()
      }
    }

    ws.onerror = () => setError('WebSocket connection failed')

    return () => ws.close()
  }, [jobId])

  return (
    <div className="rd-processing">
      <p className="rd-proc-filename">{fileName}</p>

      {!jobId && (
        <p className="rd-proc-status">Uploading...</p>
      )}

      {jobId && !error && (
        <p className="rd-proc-status">Processing...</p>
      )}

      {error && (
        <p className="rd-proc-error">{error}</p>
      )}

      {logs.length > 0 && (
        <div className="rd-proc-logs">
          {logs.map((line, i) => (
            <p key={i} className="rd-proc-log-line">{line}</p>
          ))}
          <div ref={logsEndRef} />
        </div>
      )}
    </div>
  )
}
