import { useParams, useNavigate } from 'react-router-dom'
import DocPicker from './DocPicker'
import SplitView from './SplitView'
import { CURATED_DOCS } from './curatedDocs'
import './readar.css'

export default function Readar() {
  const { docId } = useParams()
  const navigate = useNavigate()

  // URL is the source of truth for which doc is open — this is what makes a
  // refresh land back on the same screen instead of bouncing to the picker
  const activeDoc = docId ? CURATED_DOCS.find(d => d.id === docId && d.ready) : null

  function selectDoc(doc) {
    navigate(`/readar/${doc.id}`)
  }

  function backToPicker() {
    navigate('/readar')
  }

  return (
    <div className="rd-page">
      {/* aurora */}
      <div className="rd-aurora">
        <div className="rd-blob rd-blob-1" />
        <div className="rd-blob rd-blob-2" />
        <div className="rd-blob rd-blob-3" />
      </div>

      {activeDoc
        ? <SplitView doc={activeDoc} onBack={backToPicker} />
        : <DocPicker onSelect={selectDoc} />}
    </div>
  )
}
