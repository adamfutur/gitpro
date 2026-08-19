import { Link } from 'react-router-dom'
import type { Repo } from '../api'
import { getLanguageColor } from '../lib/languageColors'
import { formatRelativeTime } from '../lib/time'
import './RepoCard.css'

export default function RepoCard({ repo }: { repo: Repo }) {
  return (
    <div className="gc-repo-card">
      <div className="gc-repo-card-main">
        <Link to={`/repos/${repo.id}`} className="gc-repo-card-name">
          {repo.name}
        </Link>
        <span className={`gc-repo-card-badge ${repo.private ? 'is-private' : 'is-public'}`}>
          {repo.private ? 'Private' : 'Public'}
        </span>
      </div>

      {repo.description && <p className="gc-repo-card-desc">{repo.description}</p>}

      <div className="gc-repo-card-meta">
        {repo.language && (
          <span className="gc-repo-card-meta-item">
            <span className="gc-lang-dot" style={{ background: getLanguageColor(repo.language) }} />
            {repo.language}
          </span>
        )}
        <span className="gc-repo-card-meta-item">
          <StarIcon /> {repo.stars_count}
        </span>
        <span className="gc-repo-card-meta-item">
          <ForkIcon /> {repo.forks_count}
        </span>
        {repo.updated_at && (
          <span className="gc-repo-card-meta-item">Updated {formatRelativeTime(repo.updated_at)}</span>
        )}
      </div>
    </div>
  )
}

function StarIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046
        2.97.719 4.192a.75.75 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818
        6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z" />
    </svg>
  )
}

function ForkIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M5 5.372v.878c0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75v-.878a2.25 2.25 0 1 1 1.5 0v.878a2.25
        2.25 0 0 1-2.25 2.25h-1.5v2.128a2.251 2.251 0 1 1-1.5 0V8.5h-1.5A2.25 2.25 0 0 1 3.5 6.25v-.878a2.25
        2.25 0 1 1 1.5 0ZM5 3.25a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Zm6.75.75a.75.75 0 1 0 0-1.5.75.75 0 0
        0 0 1.5Zm-3 8.75a.75.75 0 1 0-1.5 0 .75.75 0 0 0 1.5 0Z" />
    </svg>
  )
}
