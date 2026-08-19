import { useEffect, useState } from 'react'
import { Outlet, useParams } from 'react-router-dom'
import {
  getRepo,
  type AnalysisResult,
  type DiagramResult,
  type FixScanResult,
  type PrAnalysisResult,
  type Repo,
} from '../api'
import EmptyState from '../components/EmptyState'
import Spinner from '../components/Spinner'
import Tabs from '../components/Tabs'
import { useJobPolling } from '../hooks/useJobPolling'
import { getLanguageColor } from '../lib/languageColors'
import './RepoDetail.css'

export interface RepoOutletContext {
  repo: Repo
  analysisJobs: ReturnType<typeof useJobPolling<AnalysisResult>>
  prJobs: ReturnType<typeof useJobPolling<PrAnalysisResult>>
  fixJobs: ReturnType<typeof useJobPolling<FixScanResult>>
  diagramJobs: ReturnType<typeof useJobPolling<DiagramResult>>
}

export default function RepoDetail() {
  const { repoId } = useParams<{ repoId: string }>()
  const [repo, setRepo] = useState<Repo | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Instantiated here (not inside the tabs themselves) so an in-flight "Run analysis",
  // "Review this PR", "Scan for fixes", or "Generate diagram" job keeps being tracked even
  // if the user switches tabs — this component stays mounted across Overview/Analysis/Pulls/
  // Auto-fix/Diagram/Chat, only its Outlet child swaps.
  const analysisJobs = useJobPolling<AnalysisResult>()
  const prJobs = useJobPolling<PrAnalysisResult>()
  const fixJobs = useJobPolling<FixScanResult>()
  const diagramJobs = useJobPolling<DiagramResult>()

  useEffect(() => {
    if (!repoId) return
    setRepo(null)
    setError(null)
    getRepo(Number(repoId))
      .then(setRepo)
      .catch((err) => setError(err.message ?? 'Failed to load repository'))
  }, [repoId])

  if (error) {
    return (
      <div className="gc-page">
        <EmptyState title="Couldn't load this repository" description={error} />
      </div>
    )
  }

  if (!repo) {
    return (
      <div className="gc-page gc-repo-loading">
        <Spinner label="Loading repository..." />
      </div>
    )
  }

  return (
    <div className="gc-page gc-repo-detail">
      <div className="gc-repo-header">
        <div className="gc-repo-header-top">
          <h1>{repo.name}</h1>
          <a className="btn" href={repo.html_url} target="_blank" rel="noreferrer">
            View on GitHub
          </a>
        </div>
        {repo.description && <p className="gc-repo-desc">{repo.description}</p>}
        <div className="gc-repo-stats">
          {repo.language && (
            <span className="gc-repo-stat">
              <span className="gc-lang-dot" style={{ background: getLanguageColor(repo.language) }} />
              {repo.language}
            </span>
          )}
          <span className="gc-repo-stat">⭐ {repo.stars_count} stars</span>
          <span className="gc-repo-stat">🍴 {repo.forks_count} forks</span>
          <span className="gc-repo-stat">{repo.open_issues_count} open issues</span>
          <span className="gc-repo-stat">Default branch: {repo.default_branch}</span>
        </div>
      </div>

      <Tabs
        items={[
          { to: `/repos/${repo.id}/overview`, label: 'Overview' },
          { to: `/repos/${repo.id}/analysis`, label: 'Analysis' },
          { to: `/repos/${repo.id}/pulls`, label: 'Pull requests' },
          { to: `/repos/${repo.id}/fixes`, label: 'Auto-fix' },
          { to: `/repos/${repo.id}/diagram`, label: 'Diagram' },
          { to: `/repos/${repo.id}/chat`, label: 'Chat' },
        ]}
      />

      <div className="gc-repo-tab-content">
        <Outlet context={{ repo, analysisJobs, prJobs, fixJobs, diagramJobs } satisfies RepoOutletContext} />
      </div>
    </div>
  )
}
