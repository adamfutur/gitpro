import { useEffect, useMemo, useState } from 'react'
import { listRepos, type Repo } from '../api'
import EmptyState from '../components/EmptyState'
import RepoCard from '../components/RepoCard'
import Spinner from '../components/Spinner'
import './Dashboard.css'

export default function Dashboard() {
  const [repos, setRepos] = useState<Repo[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [query, setQuery] = useState('')

  useEffect(() => {
    listRepos()
      .then(setRepos)
      .catch((err) => setError(err.message ?? 'Failed to load repositories'))
  }, [])

  const filtered = useMemo(() => {
    if (!repos) return []
    const q = query.trim().toLowerCase()
    if (!q) return repos
    return repos.filter(
      (r) => r.name.toLowerCase().includes(q) || r.description?.toLowerCase().includes(q)
    )
  }, [repos, query])

  return (
    <div className="gc-page gc-dashboard">
      <div className="gc-dashboard-header">
        <h1>Your repositories</h1>
        <input
          className="gc-dashboard-search"
          placeholder="Find a repository..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="card gc-dashboard-list">
        {error && (
          <EmptyState title="Couldn't load repositories" description={error} />
        )}

        {!error && !repos && (
          <div className="gc-dashboard-loading">
            <Spinner label="Loading repositories..." />
          </div>
        )}

        {!error && repos && filtered.length === 0 && (
          <EmptyState
            title={repos.length === 0 ? 'No repositories found' : 'No matches'}
            description={
              repos.length === 0
                ? 'We could not find any GitHub repositories for your account.'
                : 'Try a different search term.'
            }
          />
        )}

        {!error && filtered.map((repo) => <RepoCard key={repo.id} repo={repo} />)}
      </div>
    </div>
  )
}
