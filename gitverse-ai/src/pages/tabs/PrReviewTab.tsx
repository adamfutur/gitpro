import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useOutletContext, useParams } from 'react-router-dom'
import remarkGfm from 'remark-gfm'
import { getPrAnalysis, getPrAnalysisJob, startPrAnalysis, type PrAnalysisResult, type PrVerdict } from '../../api'
import EmptyState from '../../components/EmptyState'
import Spinner from '../../components/Spinner'
import type { RepoOutletContext } from '../RepoDetail'
import './PrReviewTab.css'

export default function PrReviewTab() {
  const { repo, prJobs } = useOutletContext<RepoOutletContext>()
  const { prNumber } = useParams<{ prNumber: string }>()
  const prNum = Number(prNumber)
  const jobKey = `pr-${prNum}`

  const [checkingExisting, setCheckingExisting] = useState(true)
  const job = prJobs.getState(jobKey)

  useEffect(() => {
    // Same rationale as AnalysisTab: skip the one-time cache check if this PR's job is
    // already tracked (running/done/failed) from an earlier visit in this session — that
    // state lives in RepoDetail and survives switching tabs or browsing to another PR.
    if (job.status !== 'idle') {
      setCheckingExisting(false)
      return
    }
    let cancelled = false
    getPrAnalysis(repo.id, prNum)
      .then((data) => {
        if (cancelled || !data) return
        prJobs.hydrate(jobKey, data)
      })
      .finally(() => !cancelled && setCheckingExisting(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repo.id, prNum])

  function runReview() {
    prJobs.run(
      jobKey,
      () => startPrAnalysis(repo.id, prNum),
      (jobId) => getPrAnalysisJob(repo.id, prNum, jobId)
    )
  }

  const reviewing = job.status === 'running'
  const result: PrAnalysisResult | null = job.status === 'completed' ? job.result : null

  if (checkingExisting) {
    return (
      <div className="gc-pr-loading">
        <Spinner label="Checking for existing review..." />
      </div>
    )
  }

  return (
    <div className="gc-pr-review">
      <div className="gc-pr-toolbar">
        {result ? (
          <p className="gc-pr-generated">Last reviewed {new Date(result.generated_at).toLocaleString()}</p>
        ) : (
          <span />
        )}
        <button className="btn btn-primary" onClick={runReview} disabled={reviewing}>
          {reviewing ? 'Reviewing…' : result ? 'Re-review PR' : 'Review this PR'}
        </button>
      </div>

      {job.status === 'failed' && <p className="gc-pr-error">{job.error}</p>}

      {reviewing && (
        <div className="card gc-pr-progress">
          <Spinner label={job.stage ?? 'Starting review...'} />
        </div>
      )}

      {!reviewing && !result && (
        <EmptyState
          title="Not reviewed yet"
          description="Run a review to get an AI code review focused on this PR's diff."
        />
      )}

      {!reviewing && result && (
        <>
          {result.verdict && <VerdictBanner verdict={result.verdict} />}

          <div className="card gc-pr-stats">
            <div className="gc-pr-stats-summary">
              <span>{result.files_changed} files changed</span>
              <span className="gc-pr-additions">+{result.additions}</span>
              <span className="gc-pr-deletions">-{result.deletions}</span>
            </div>
            <ul className="gc-pr-file-list">
              {result.files.map((f) => (
                <li key={f.filename} className="gc-pr-file">
                  <code>{f.filename}</code>
                  <span className="gc-pr-file-badge">{f.status}</span>
                  <span className="gc-pr-additions">+{f.additions}</span>
                  <span className="gc-pr-deletions">-{f.deletions}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="card gc-pr-writeup">
            <h3>AI review</h3>
            <div className="gc-markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.review}</ReactMarkdown>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function VerdictBanner({ verdict }: { verdict: PrVerdict }) {
  const pass = verdict.status === 'pass'
  return (
    <div className={`card gc-pr-verdict ${pass ? 'is-pass' : 'is-fail'}`}>
      {pass ? <CheckIcon /> : <XIcon />}
      <div>
        <div className="gc-pr-verdict-status">{pass ? 'Passes gitcat checks' : 'Blocked by gitcat checks'}</div>
        <div className="gc-pr-verdict-reason">{verdict.reason}</div>
      </div>
    </div>
  )
}

function CheckIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1
        1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
    </svg>
  )
}

function XIcon() {
  return (
    <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M3.72 3.72a.75.75 0 0 1 1.06 0L8 6.94l3.22-3.22a.75.75 0 1 1 1.06 1.06L9.06 8l3.22
        3.22a.75.75 0 1 1-1.06 1.06L8 9.06l-3.22 3.22a.75.75 0 0 1-1.06-1.06L6.94 8 3.72 4.78a.75.75
        0 0 1 0-1.06Z" />
    </svg>
  )
}
