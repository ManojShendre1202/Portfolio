import Cursor     from './components/Cursor'
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
import RobotWidget from './components/RobotWidget'
import './App.css'

export default function App() {
  return (
    <>
      <Cursor />
      <RobotWidget />
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
