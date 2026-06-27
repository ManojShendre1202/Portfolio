import './Marquee.css'

const ITEMS = [
  'Indian Railways', 'L&T Shipbuilding', 'Spark Minda',
  'Mahindra Aerospace', 'Goa Shipyard', 'SASMOS Defence',
  'Hubbell', 'Motherson', 'Computer Vision', 'Graph Algorithms',
]

export default function Marquee({ dark = false }) {
  const repeated = [...ITEMS, ...ITEMS, ...ITEMS]

  return (
    <div className={`marquee-wrap ${dark ? 'marquee-dark' : ''}`}>
      <div className="marquee-track">
        {repeated.map((item, i) => (
          <span key={i} className="marquee-item">
            {item} <span className="marquee-dot">·</span>
          </span>
        ))}
      </div>
    </div>
  )
}
