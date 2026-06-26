import { useState, useCallback } from 'react'
import Cursor     from './components/Cursor'
import Terminal   from './components/Terminal'
import Navbar     from './components/Navbar'
import SidePanel  from './components/SidePanel'
import Intro      from './components/Intro'
import Marquee    from './components/Marquee'
import About      from './components/About'
import Experience from './components/Experience'
import Dockyard   from './components/Dockyard'
import Skills     from './components/Skills'
import Contact    from './components/Contact'
import Footer     from './components/Footer'
import './App.css'

export default function App() {
  const [done, setDone] = useState(false)
  const onDone = useCallback(() => setDone(true), [])

  return (
    <>
      <Cursor />
      {!done && <Terminal onDone={onDone} />}
      <Navbar />
      <SidePanel />
      <main>
        <Intro />
        <Marquee />
        <About />
        <Marquee />
        <Experience />
        <Marquee />
        <Dockyard />
        <Marquee dark />
        <Skills />
        <Contact />
      </main>
      <Footer />
    </>
  )
}
