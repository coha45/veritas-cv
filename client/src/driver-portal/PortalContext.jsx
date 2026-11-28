import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { portalRequest, portalToken } from './api'

const PortalContext = createContext(null)

export function PortalProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!portalToken.get()) {
      setUser(null)
      setLoading(false)
      return null
    }
    try {
      const result = await portalRequest('/me')
      setUser(result.user)
      return result.user
    } catch {
      portalToken.clear()
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void refreshUser() }, [refreshUser])

  const signIn = useCallback(async (email, password) => {
    const result = await portalRequest('/auth/login', { method: 'POST', body: { email, password } })
    portalToken.set(result.token)
    setUser(result.user)
    return result.user
  }, [])

  const signUp = useCallback(async (details) => {
    const result = await portalRequest('/auth/signup', { method: 'POST', body: details })
    portalToken.set(result.token)
    setUser(result.user)
    return result.user
  }, [])

  const signOut = useCallback(async () => {
    try { if (portalToken.get()) await portalRequest('/auth/logout', { method: 'POST' }) } finally {
      portalToken.clear()
      setUser(null)
    }
  }, [])

  return (
    <PortalContext.Provider value={{ user, loading, signIn, signUp, signOut, refreshUser, setUser }}>
      {children}
    </PortalContext.Provider>
  )
}

export function usePortal() {
  const context = useContext(PortalContext)
  if (!context) throw new Error('usePortal must be used within PortalProvider')
  return context
}
