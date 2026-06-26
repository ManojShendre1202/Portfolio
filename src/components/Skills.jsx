import { motion } from 'framer-motion'
import './Skills.css'

const SKILLS = [
  { cat: 'Computer Vision & ML',    items: ['OpenCV (advanced)', 'FasterRCNN', 'OCR', 'Azure Computer Vision', 'ChangeFormer', 'PyTorch'] },
  { cat: 'Drawing & Geometry',      items: ['ezdxf', 'Shapely', 'DXF processing', 'SVG processing', 'PDF processing'] },
  { cat: 'Algorithms',              items: ['Dijkstra', 'Flood Fill', 'Graph Algorithms', 'Geometric Computation', 'BFS / DFS'] },
  { cat: 'Cloud & Infrastructure',  items: ['Azure ADF', 'Azure ADLS', 'AWS', 'GCP Vertex AI', 'Cloud Run', 'Docker'] },
  { cat: 'Backend & Systems',       items: ['Python', 'Django', 'FastAPI', 'WebSockets', 'Custom Worker Pools', 'SQL'] },
  { cat: 'Databases',               items: ['MSSQL', 'MySQL', 'ArangoDB', 'Azure Data Lake', 'Firebase'] },
]

export default function Skills() {
  return (
    <section className="skills-section" id="skills">
      <div className="skills-inner">
        <motion.div
          className="skills-header"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
        >
          <p className="section-label">Technical Skills</p>
          <h2 className="section-title">What I work with</h2>
        </motion.div>

        <div className="skills-grid">
          {SKILLS.map((g, i) => (
            <motion.div
              key={i}
              className="skill-group"
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ duration: 0.5, delay: (i % 3) * 0.08 }}
            >
              <p className="sg-cat">{g.cat}</p>
              <div className="sg-items">
                {g.items.map(item => (
                  <span key={item} className="sg-item">{item}</span>
                ))}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
