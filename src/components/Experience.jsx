import { useRef, useState } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import ProjectModal from './ProjectModal'
import './Experience.css'

const STATUS_COLOR = {
  'Production': '#16a34a',
  'Delivered':  '#16a34a',
  'UAT':        '#2563eb',
  'Near-Prod':  '#d97706',
  'In Dev':     '#78716c',
}

const PROJECTS = [
  {
    num: '01', client: 'Indian Railways', title: 'Automated BOM Generation',
    status: 'Production', impact: '95% reduction — 1 month → 2 hours',
    tags: ['Python', 'OpenCV', 'OCR', 'Azure'],
    desc: 'Reads railway engineering drawings up to 3km long and generates complete Bills of Materials.',
    fullDesc: 'Reads PDFs and images of railway engineering drawings — some spanning up to 3km in length. Encodes complex domain flowchart logic in Python to identify components, interpret symbols, and generate complete Bills of Materials automatically. Handles scale variations, noisy scans, and domain-specific notation.',
    techDetails: [
      'Multi-scale PDF processing with adaptive resolution based on drawing density',
      'Custom OCR pipeline fine-tuned for railway engineering notation and symbols',
      'Flowchart logic encoder that replicates domain expert decision trees in Python',
      'Azure cloud integration for parallel processing of large drawing sets',
    ],
    beforeAfter: { before: '10–20 engineers, ~1 month per drawing set', after: '2–3 people, ~2 hours including human verification' },
  },
  {
    num: '02', client: 'L&T Shipbuilding', title: 'Cable Routing System',
    status: 'UAT', impact: 'Lakhs of cables · Lakhs of km routed', solo: true,
    tags: ['Python', 'ezdxf', 'Shapely', 'Dijkstra', 'Graph Algorithms'],
    desc: 'Flood Fill + Dijkstra hybrid routes cables across ship decks via a universal graph from DXF drawings.',
    fullDesc: 'Parses complex DXF ship drawings to identify multiple decks and cable trays — a significant challenge given the varied curves, angles, and representations across different ship departments. Builds a universal topological graph of the ship, then routes cables using a custom Flood Fill + Dijkstra hybrid algorithm that accounts for tray capacity, routing constraints, and cable specifications.',
    techDetails: [
      'DXF parsing with ezdxf to extract cable tray geometry across multiple ship decks',
      'Shapely-based geometric analysis to classify tray types from varied curve representations',
      'Universal graph construction representing all possible routing paths',
      'Flood Fill + Dijkstra hybrid for optimal cable routing with constraint satisfaction',
      'BOM output: cable lengths, tray assignments, routing paths',
    ],
    beforeAfter: { before: 'Manual routing by engineers — weeks per ship, lakhs of cables', after: 'Automated routing in hours — same accuracy, full BOM output' },
  },
  {
    num: '03', client: 'L&T Shipbuilding', title: 'Hull Weld Seam BOM',
    status: 'In Dev', impact: 'Thousands of weld spots per drawing', solo: true, lead: true,
    tags: ['Python', 'ezdxf', 'Shapely', 'OpenCV'],
    desc: 'On-spot geometric computation of weld seam lengths — no graph, no ML. Pure shape analysis.',
    fullDesc: 'Second independent project from L&T — different department, demonstrating client trust and repeat business. Detects thousands of welding spots and blocks across hull drawings, then computes weld seam lengths via on-spot geometric calculation. Deliberately contrasts with the cable routing approach — no graph-based algorithm, no ML models. Pure shape analysis because the problem structure demands it.',
    techDetails: [
      'Hull drawing parsing with ezdxf — different schema from cable routing drawings',
      'Weld spot and block detection using Shapely geometric analysis',
      'On-spot seam length computation via direct geometric measurement',
      'No ML, no graph — pure engineering solution matching the problem structure',
      'BOM output: weld seam lengths, weld types, location references',
    ],
    beforeAfter: { before: 'Manual measurement by engineers — error-prone on complex hull geometries', after: 'Automated geometric computation — thousands of spots in minutes' },
  },
  {
    num: '04', client: 'Spark Minda', title: 'Automotive Wiring Harness BOM',
    status: 'Near-Prod', impact: '~99% reduction — 1 week → 1 hour',
    tags: ['FasterRCNN', 'AWS', 'Azure', 'OpenCV', 'OCR'],
    desc: 'FasterRCNN detection + graph association generates full BOM from automotive wiring drawings.',
    fullDesc: 'Processes complex automotive wiring harness drawings — among the most intricate engineering drawings in any domain. Element detection using a locally-trained FasterRCNN model identifies connectors, terminals, splices, and wiring components. Custom graph association logic (core contribution) links detected elements to tables and BOM entries, calculates wiring lengths and bundle configurations, and generates complete manufacturing BOMs.',
    techDetails: [
      'FasterRCNN trained locally on automotive wiring harness components',
      'Custom graph/association logic linking detected elements to BOM tables',
      'Wiring length calculation from geometric analysis of harness paths',
      'Bundle calculation combining individual wire specifications',
      'AWS + Azure cloud processing for large drawing batches',
    ],
    beforeAfter: { before: '6–10 engineers, ~1 week per harness drawing set', after: '~1 hour including manual verification step' },
  },
  {
    num: '05', client: 'Goa Shipyard', title: 'Cable Routing POC',
    status: 'Delivered', impact: 'Solo · On-site · No internet · 120m ships', solo: true,
    tags: ['Python', 'ezdxf', 'Shapely', 'OpenCV'],
    desc: 'Solo on-site live delivery with zero internet access on 120m+ ships.',
    fullDesc: 'Sent alone by the company to deliver a live proof-of-concept at Goa Shipyard — on-site, with no internet access. Ships 120+ meters in length with DXF and SVG format drawings (different from L&T). Adapted the cable routing engine on-site for the new format, ran live demonstrations, and delivered a technically successful POC. Project was not pursued commercially — management-level disagreement on pricing, not a technical failure.',
    techDetails: [
      'Adapted cable routing engine for Goa Shipyard DXF + SVG drawing formats',
      'On-site adaptation with zero internet — all dependencies pre-packaged',
      '120m+ ship drawings with significantly different deck layout conventions',
      'Live demonstration to Goa Shipyard engineering team',
    ],
  },
  {
    num: '06', client: 'Mahindra Aerospace', title: 'Aircraft BOM Generation',
    status: 'In Dev', impact: 'Airbus + Boeing aircraft database', solo: true,
    tags: ['Python', 'OpenCV', 'OCR'],
    desc: 'Table detection without ML — deliberate engineering constraint. Pure OpenCV on scanned aerospace drawings.',
    fullDesc: 'Processes complex scanned engineering drawings for Airbus and Boeing aircraft databases. The defining technical choice: table detection without ML models. This is a deliberate engineering constraint — fax-format unstructured tables in scanned aerospace drawings have enough consistent geometric structure that a pure OpenCV approach is more robust and maintainable than a neural network. Advanced OpenCV for noisy scan handling and optimized cross-document reference resolution across large drawing datasets.',
    techDetails: [
      'Fax-format unstructured table detection — pure OpenCV, no ML by design',
      'Advanced scan noise handling for aged aerospace technical documents',
      'Cross-document reference resolution across large Airbus/Boeing drawing sets',
      'OCR pipeline optimised for aerospace part numbers and notation',
    ],
  },
  {
    num: '07', client: 'Hubbell', title: 'SAP Deduction Validation',
    status: 'Production', impact: '1+ year live · Sole owner', solo: true,
    tags: ['Python', 'Azure ADF', 'ADLS', 'SQL'],
    desc: 'ML model validates SAP deductions. Full ownership: retraining, dashboard, all change requests.',
    fullDesc: 'ML model that validates the genuineness of deductions across SAP enterprise documents. The only non-drawing project in the portfolio — demonstrates stack versatility beyond computer vision, enterprise data pipeline experience, and SAP domain knowledge. Full sole ownership for 1+ year: model retraining when distribution shifts, dashboard management, handling all client change requests, and production monitoring.',
    techDetails: [
      'ML classification model for SAP deduction validation',
      'Azure Data Factory (ADF) pipelines for automated data ingestion',
      'Azure Data Lake Storage (ADLS) for document and result storage',
      'SQL-based reporting and dashboard for business users',
      'Model retraining pipeline triggered on accuracy drift detection',
    ],
    beforeAfter: { before: 'Manual review of deductions by finance team — slow, inconsistent', after: 'Automated ML validation — 1+ year in production, sole owner' },
  },
]

function ProjectCard({ p, onOpen }) {
  const ref = useRef(null)

  const onMove = (e) => {
    const r  = ref.current.getBoundingClientRect()
    const dx = (e.clientX - r.left)  / r.width  - 0.5
    const dy = (e.clientY - r.top)   / r.height - 0.5
    ref.current.style.transform =
      `perspective(900px) rotateY(${dx * 7}deg) rotateX(${-dy * 7}deg) translateZ(10px)`
  }
  const onLeave = () => {
    ref.current.style.transition = 'transform 0.6s cubic-bezier(0.25,0.1,0.25,1)'
    ref.current.style.transform  = 'perspective(900px) rotateY(0) rotateX(0) translateZ(0)'
    setTimeout(() => { if (ref.current) ref.current.style.transition = '' }, 600)
  }

  const sc = STATUS_COLOR[p.status] || '#78716c'

  return (
    <motion.div
      ref={ref}
      className="proj-card"
      initial={{ opacity: 0, y: 40 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.6, delay: 0.05, ease: [0.25, 0.1, 0.25, 1] }}
      onMouseMove={onMove}
      onMouseLeave={onLeave}
      onClick={() => onOpen({ ...p, statusColor: sc })}
      data-cursor
    >
      <div className="pc-top">
        <span className="pc-num">{p.num}</span>
        <div className="pc-badges">
          <span className="pc-status" style={{ color: sc }}>● {p.status}</span>
          {p.solo && <span className="pc-solo">{p.lead ? 'Lead' : 'Solo'}</span>}
        </div>
      </div>

      <p className="pc-client">{p.client}</p>
      <h3 className="pc-title">{p.title}</h3>
      <p className="pc-impact">{p.impact}</p>
      <p className="pc-desc">{p.desc}</p>

      <div className="pc-footer">
        <div className="pc-tags">
          {p.tags.slice(0, 3).map(t => <span key={t} className="pc-tag">{t}</span>)}
          {p.tags.length > 3 && <span className="pc-tag">+{p.tags.length - 3}</span>}
        </div>
        <span className="pc-open">View details →</span>
      </div>
    </motion.div>
  )
}

export default function Experience() {
  const [modal, setModal] = useState(null)
  const sectionRef = useRef(null)
  const { scrollYProgress } = useScroll({ target: sectionRef, offset: ['start end', 'end start'] })
  const y = useTransform(scrollYProgress, [0, 1], [50, -50])

  return (
    <>
      <section className="exp-section" id="experience" ref={sectionRef}>
        <div className="exp-header-wrap">
          <motion.div className="exp-header" style={{ y }}>
            <p className="section-label">Professional Experience</p>
            <h2 className="section-title">
              Kynea Solutions LLP<br />
              <em>May 2024 — Present</em>
            </h2>
            <p className="exp-sub">
              ML Engineer · Bangalore<br />
              7 of 10 projects — solo-delivered or led
            </p>
            <p className="exp-hint">Click any card for full details</p>
          </motion.div>
        </div>

        <div className="proj-grid">
          {PROJECTS.map((p, i) => (
            <ProjectCard key={i} p={p} onOpen={setModal} />
          ))}
        </div>
      </section>

      {modal && <ProjectModal project={modal} onClose={() => setModal(null)} />}
    </>
  )
}
