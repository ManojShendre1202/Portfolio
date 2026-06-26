import { useEffect, useRef, useState } from 'react'
import './Cursor.css'

export default function Cursor() {
  const dotRef   = useRef(null)
  const ringRef  = useRef(null)
  const pos      = useRef({ x: -100, y: -100 })
  const ring     = useRef({ x: -100, y: -100 })
  const raf      = useRef(null)
  const [hovered, setHovered] = useState(false)
  const [clicked, setClicked] = useState(false)

  useEffect(() => {
    const move = (e) => { pos.current = { x: e.clientX, y: e.clientY } }
    const down = () => setClicked(true)
    const up   = () => setClicked(false)

    const onEnter = (e) => {
      if (e.target.closest('a, button, [data-cursor]')) setHovered(true)
    }
    const onLeave = (e) => {
      if (e.target.closest('a, button, [data-cursor]')) setHovered(false)
    }

    window.addEventListener('mousemove', move)
    window.addEventListener('mousedown', down)
    window.addEventListener('mouseup',   up)
    document.addEventListener('mouseover',  onEnter)
    document.addEventListener('mouseout',   onLeave)

    const loop = () => {
      if (dotRef.current && ringRef.current) {
        // dot — instant
        dotRef.current.style.transform =
          `translate(${pos.current.x - 4}px, ${pos.current.y - 4}px)`

        // ring — lerp (lazy follow)
        ring.current.x += (pos.current.x - ring.current.x) * 0.12
        ring.current.y += (pos.current.y - ring.current.y) * 0.12
        ringRef.current.style.transform =
          `translate(${ring.current.x - 20}px, ${ring.current.y - 20}px)`
      }
      raf.current = requestAnimationFrame(loop)
    }
    raf.current = requestAnimationFrame(loop)

    return () => {
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mousedown', down)
      window.removeEventListener('mouseup',   up)
      document.removeEventListener('mouseover',  onEnter)
      document.removeEventListener('mouseout',   onLeave)
      cancelAnimationFrame(raf.current)
    }
  }, [])

  return (
    <>
      <div ref={dotRef}  className={`cur-dot  ${clicked ? 'clicked' : ''}`} />
      <div ref={ringRef} className={`cur-ring ${hovered ? 'hovered' : ''} ${clicked ? 'clicked' : ''}`} />
    </>
  )
}
