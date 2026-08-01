import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Portfolio from './pages/portfolio/Portfolio'
import Readar    from './pages/readar/Readar'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/"         element={<Portfolio />} />
        <Route path="/readar"          element={<Readar />} />
        <Route path="/readar/:docId"   element={<Readar />} />
      </Routes>
    </BrowserRouter>
  )
}
