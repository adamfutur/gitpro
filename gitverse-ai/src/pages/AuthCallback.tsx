import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { setToken } from '../api'
import Spinner from '../components/Spinner'
import './AuthCallback.css'

const ERROR_MESSAGES: Record<string, string> = {
  no_code: 'GitHub did not return an authorization code. Please try again.',
  oauth_failed: 'GitHub rejected the authorization request.',
  oauth_error: 'Something went wrong while signing you in.',
}

export default function AuthCallback() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const token = searchParams.get('token')
    const errorCode = searchParams.get('error')

    if (token) {
      setToken(token)
      navigate('/repos', { replace: true })
      return
    }

    setError(errorCode ? ERROR_MESSAGES[errorCode] ?? 'Sign-in failed.' : 'No token received.')
  }, [searchParams, navigate])

  if (error) {
    return (
      <div className="gc-callback">
        <p className="gc-callback-error">{error}</p>
        <Link to="/" className="btn">
          Back to login
        </Link>
      </div>
    )
  }

  return (
    <div className="gc-callback">
      <Spinner label="Signing you in..." />
    </div>
  )
}
