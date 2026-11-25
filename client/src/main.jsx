import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { BrowserRouter } from 'react-router-dom'
import { VeritasProvider } from './context/VeritasContext.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <VeritasProvider>
        <App />
      </VeritasProvider>
    </BrowserRouter>
  </StrictMode>,
)
