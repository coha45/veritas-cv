import Sidebar from './components/Sidebar'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Database from './pages/Database'
import TopDown from './pages/TopDown'
import PortalApp from './driver-portal/PortalApp'

const App = () => {
  const { pathname } = useLocation()
  const isPortal = pathname.startsWith('/portal') || ['/index.html', '/login.html', '/register.html', '/forgot.html'].includes(pathname)

  return (
    <div className={isPortal ? 'min-h-screen' : 'flex w-screen min-h-screen h-full relative'}>
      {!isPortal && <Sidebar />}
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/top-down" element={<TopDown />} />
        <Route path="/topdown" element={<TopDown />} />
        <Route path="/database" element={<Database />} />
        <Route path="/portal/*" element={<PortalApp />} />
        <Route path="/portal.html" element={<Navigate to="/portal" replace />} />
        <Route path="/index.html" element={<Navigate to="/portal" replace />} />
        <Route path="/login.html" element={<Navigate to="/portal/login" replace />} />
        <Route path="/register.html" element={<Navigate to="/portal/register" replace />} />
        <Route path="/forgot.html" element={<Navigate to="/portal/forgot" replace />} />
      </Routes>
    </div>
  )
}

export default App
