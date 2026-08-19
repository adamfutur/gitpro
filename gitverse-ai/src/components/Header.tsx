import { Link } from 'react-router-dom'
import type { User } from '../api'
import GitcatMark from './GitcatMark'
import './Header.css'

export default function Header({
  user,
  onSignOut,
}: {
  user: User | null
  onSignOut: () => void
}) {
  return (
    <header className="gc-header">
      <div className="gc-header-inner">
        <Link to="/repos" className="gc-header-brand">
          <GitcatMark size={32} bg="var(--header-bg)" />
          <span>gitcat</span>
        </Link>

        {user && (
          <div className="gc-header-user">
            <img className="avatar gc-header-avatar" src={user.avatar_url} alt="" width={28} height={28} />
            <span className="gc-header-username">{user.login}</span>
            <button type="button" className="gc-header-signout" onClick={onSignOut}>
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
