import { useEffect, useRef, useState } from 'react'
import lottie from 'lottie-web'
import robotData from '../../assets/robot.json'
import './RobotWidget.css'

export default function RobotWidget() {
  const [mounted, setMounted] = useState(false)
  const [hovered, setHovered] = useState(false)
  const containerRef = useRef(null)
  const animRef      = useRef(null)

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 1000)
    return () => clearTimeout(t)
  }, [])

  useEffect(() => {
    if (!mounted || !containerRef.current) return
    animRef.current = lottie.loadAnimation({
      container:     containerRef.current,
      animationData: robotData,
      renderer:      'svg',
      loop:          true,
      autoplay:      true,
    })
    return () => animRef.current?.destroy()
  }, [mounted])

  return (
    <div className="robot-widget">
      <a
        href="http://127.0.0.1:8020/readar/"
        target="_blank"
        rel="noopener noreferrer"
        className="robot-widget-link"
        title="Try Readar"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {mounted
          ? <div ref={containerRef} className={`robot-lottie-wrap ${hovered ? 'hovered' : ''}`} />
          : <div className="robot-widget-skeleton" />
        }
        <div className="robot-widget-label">
          <span className="robot-widget-dot" />
          Try Readar
        </div>
      </a>
    </div>
  )
}
