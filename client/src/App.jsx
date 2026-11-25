import React from 'react'
import VeritasDashboard from './VeritasDashboard'
import Sidebar from './components/Sidebar'
import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'

const App = () => {
  return (
    <div className="flex w-screen min-h-screen h-full relative">
      <Sidebar />
      <Routes>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/top-down" element={<Dashboard />} />
        <Route path="/payments" element={<Dashboard />} />
        <Route path="/database" element={<Dashboard />} />
      </Routes>
    </div>
  )
}

export default App