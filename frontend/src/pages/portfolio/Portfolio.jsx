import Cursor      from './Cursor'
import Navbar      from './Navbar'
import SidePanel   from './SidePanel'
import Intro       from './Intro'
import Marquee     from './Marquee'
import About       from './About'
import Experience  from './Experience'
import Dockyard    from './Dockyard'
import Skills      from './Skills'
import Contact     from './Contact'
import Footer      from './Footer'
import RobotWidget from './RobotWidget'

export default function Portfolio() {
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
