import Sidebar from './components/Sidebar'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Database from './pages/Database'
import TopDown from './pages/TopDown'

const App = () => {
  return (
    <div className="flex w-screen min-h-screen h-full relative">
      <Sidebar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/top-down" element={<TopDown />} />
        <Route path="/topdown" element={<TopDown />} />
        <Route path="/database" element={<Database />} />
      </Routes>
    </div>
  )
}

export default App
