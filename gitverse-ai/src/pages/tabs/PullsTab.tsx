import { useEffect, useState } from 'react'
import { Link, useOutletContext } from 'react-router-dom'
import {
  disableAutoReview,
  enableAutoReview,
  getAutoReviewStatus,
  listPullRequests,
  type PullRequestSummary,
} from '../../api'
import EmptyState from '../../components/EmptyState'
import Spinner from '../../components/Spinner'
import { formatRelativeTime } from '../../lib/time'
import type { RepoOutletContext } from '../RepoDetail'
import './PullsTab.css'

export default function PullsTab() {
  const { repo } = useOutletContext<RepoOutletContext>()
  const [prs, setPrs] = useState<PullRequestSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setPrs(null)
    setError(null)
    listPullRequests(repo.id)
      .then(setPrs)
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load pull requests'))
  }, [repo.id])

  return (
    <div className="gc-pulls">
      <AutoReviewToggle repoId={repo.id} />

      {error && <EmptyState title="Couldn't load pull requests" description={error} />}

      {!error && !prs && (
        <div className="gc-pulls-loading">
          <Spinner label="Loading pull requests..." />
        </div>
      )}

      {!error && prs && prs.length === 0 && (
        <EmptyState
          title="No open pull requests"
          description="This repository has no open pull requests to review right now."
        />
      )}

      {!error && prs && prs.length > 0 && (
        <div className="card gc-pulls-list">
          {prs.map((pr) => (
            <Link key={pr.number} to={`/repos/${repo.id}/pulls/${pr.number}`} className="gc-pull-item">
              <PrIcon draft={pr.draft} />
              <div className="gc-pull-item-main">
                <span className="gc-pull-item-title">{pr.title}</span>
                <span className="gc-pull-item-meta">
                  #{pr.number} opened by {pr.user} · updated {formatRelativeTime(pr.updated_at)}
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

function AutoReviewToggle({ repoId }: { repoId: number }) {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setEnabled(null)
    setError(null)
    getAutoReviewStatus(repoId)
      .then((res) => setEnabled(res.enabled))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load auto-review status'))
  }, [repoId])

  async function toggle() {
    setBusy(true)
    setError(null)
    try {
      const res = enabled ? await disableAutoReview(repoId) : await enableAutoReview(repoId)
      setEnabled(res.enabled)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update auto-review')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card gc-auto-review">
      <div className="gc-auto-review-main">
        <div>
          <h3 className="gc-auto-review-title">Auto-review</h3>
          <p className="gc-auto-review-desc">
            When enabled, gitcat automatically reviews every new or updated pull request, posts
            the review as a comment, and sets a <code>gitcat/review</code> commit status — pass
            or fail — that shows up in the PR merge box and can be required via GitHub branch
            protection rules.
          </p>
        </div>
        <button
          className={`btn ${enabled ? '' : 'btn-primary'}`}
          onClick={toggle}
          disabled={enabled === null || busy}
        >
          {busy ? 'Working…' : enabled ? 'Disable' : 'Enable'}
        </button>
      </div>
      {error && <p className="gc-auto-review-error">{error}</p>}
    </div>
  )
}

function PrIcon({ draft }: { draft: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="currentColor"
      aria-hidden="true"
      className={`gc-pull-icon ${draft ? 'is-draft' : 'is-open'}`}
    >
      <path d="M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5
        3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1
        1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75
        2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75
        0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z" />
    </svg>
  )
}
