import { useEffect, useState } from 'react'
import { Navigate, Outlet, useNavigate } from 'react-router-dom'
import { clearToken, getMe, getToken, type User } from '../api'
import Header from './Header'
import Spinner from './Spinner'
import './AppLayout.css'

export default function AppLayout() {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const [authFailed, setAuthFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    getMe()
      .then((u) => {
        if (!cancelled) setUser(u)
      })
      .catch(() => {
        if (!cancelled) setAuthFailed(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (!getToken()) return <Navigate to="/" replace />
  if (authFailed) {
    clearToken()
    return <Navigate to="/" replace />
  }

  function handleSignOut() {
    clearToken()
    navigate('/')
  }

  return (
    <div className="gc-app">
      <Header user={user} onSignOut={handleSignOut} />
      <main className="gc-main">
        {loading ? (
          <div className="gc-app-loading">
            <Spinner />
          </div>
        ) : (
          <Outlet context={{ user }} />
        )}
      </main>
    </div>
  )
}
