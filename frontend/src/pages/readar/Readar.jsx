import { useEffect, useRef, useState } from 'react'
import Landing    from './Landing'
import Processing from './Processing'
import ChatApp    from './ChatApp'
import { getDocType, getFileEmoji, fmtSize } from './readarData'
import { uploadDrawing, fetchJob, fetchClientJobs } from './api'
import './readar.css'

const STATE = { LANDING: 'landing', PROCESSING: 'processing', APP: 'app' }

function jobToDoc(job) {
  return {
    id:      job.id,
    name:    job.file_name,
    type:    job.section_data?.document_type || 'Document',
    emoji:   getFileEmoji(job.file_name),
    size:    fmtSize(job.file_size),
  }
}

export default function Readar() {
  const [state, setState]     = useState(STATE.LANDING)
  const [pendingFile, setPending] = useState(null)
  const [jobId, setJobId]     = useState(null)
  const [docs, setDocs]       = useState([])
  const [dragging, setDragging] = useState(false)
  const dragCounter           = useRef(0)

  // restore session on mount
  useEffect(() => {
    fetchClientJobs()
      .then(({ jobs }) => {
        if (!jobs.length) return
        const restored = jobs
          .filter(j => j.status === 'completed')
          .map(jobToDoc)
        if (restored.length) {
          setDocs(restored)
          setState(STATE.APP)
        }
      })
      .catch(() => {/* backend not running — just show landing */})
  }, [])

  // drag & drop on entire window
  useEffect(() => {
    function onEnter(e) { e.preventDefault(); dragCounter.current++; setDragging(true) }
    function onLeave()  { dragCounter.current--; if (dragCounter.current === 0) setDragging(false) }
    function onOver(e)  { e.preventDefault() }
    function onDrop(e)  {
      e.preventDefault()
      dragCounter.current = 0
      setDragging(false)
      const file = e.dataTransfer.files[0]
      if (file) handleFile(file)
    }
    window.addEventListener('dragenter', onEnter)
    window.addEventListener('dragleave', onLeave)
    window.addEventListener('dragover',  onOver)
    window.addEventListener('drop',      onDrop)
    return () => {
      window.removeEventListener('dragenter', onEnter)
      window.removeEventListener('dragleave', onLeave)
      window.removeEventListener('dragover',  onOver)
      window.removeEventListener('drop',      onDrop)
    }
  }, [])

  async function handleFile(file) {
    if (file._sample) {
      // samples have no real backend job — go straight to chat
      const doc = {
        id:    Date.now(),
        name:  file.name,
        type:  getDocType(file),
        emoji: getFileEmoji(file.name),
        size:  fmtSize(file.size),
      }
      setDocs(prev => [...prev, doc])
      setState(STATE.APP)
      return
    }

    setPending(file)
    setJobId(null)
    setState(STATE.PROCESSING)
    try {
      const id = await uploadDrawing(file)
      setJobId(id)
    } catch (e) {
      console.error('Upload error:', e)
    }
  }

  async function onProcessingDone(completedJobId) {
    try {
      const job = await fetchJob(completedJobId)
      setDocs(prev => [...prev, jobToDoc(job)])
    } catch {
      // fallback to browser file info if fetch fails
      const file = pendingFile
      setDocs(prev => [...prev, {
        id:    completedJobId,
        name:  file.name,
        type:  getDocType(file),
        emoji: getFileEmoji(file.name),
        size:  fmtSize(file.size),
      }])
    }
    setState(STATE.APP)
  }

  return (
    <div className="rd-page">
      {/* aurora */}
      <div className="rd-aurora">
        <div className="rd-blob rd-blob-1" />
        <div className="rd-blob rd-blob-2" />
        <div className="rd-blob rd-blob-3" />
      </div>

      {/* drag overlay */}
      <div className={`rd-drag-overlay ${dragging ? 'active' : ''}`} />

      {state === STATE.LANDING && (
        <Landing onFile={handleFile} />
      )}

      {state === STATE.PROCESSING && pendingFile && (
        <Processing
          fileName={pendingFile.name}
          jobId={jobId}
          onDone={onProcessingDone}
        />
      )}

      {state === STATE.APP && (
        <ChatApp
          docs={docs}
          onNewFile={handleFile}
        />
      )}
    </div>
  )
}
