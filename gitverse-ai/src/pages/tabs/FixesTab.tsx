import { useEffect, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import {
  applyFixes,
  getFixScanJob,
  startFixScan,
  type CreatedFixPr,
  type SuggestedFix,
} from '../../api'
import EmptyState from '../../components/EmptyState'
import Spinner from '../../components/Spinner'
import type { RepoOutletContext } from '../RepoDetail'
import './FixesTab.css'

const JOB_KEY = 'fix-scan'

export default function FixesTab() {
  const { repo, fixJobs } = useOutletContext<RepoOutletContext>()
  const job = fixJobs.getState(JOB_KEY)
  const scanning = job.status === 'running'
  const result = job.status === 'completed' ? job.result : null

  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [applying, setApplying] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)
  const [createdPr, setCreatedPr] = useState<CreatedFixPr | null>(null)

  useEffect(() => {
    if (!result) return
    setSelected(Object.fromEntries(result.fixes.map((f) => [f.file, true])))
    setCreatedPr(null)
    setApplyError(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [result?.fixes])

  function runScan() {
    setCreatedPr(null)
    setApplyError(null)
    fixJobs.run(
      JOB_KEY,
      () => startFixScan(repo.id),
      (jobId) => getFixScanJob(repo.id, jobId)
    )
  }

  function toggle(file: string) {
    setSelected((prev) => ({ ...prev, [file]: !prev[file] }))
  }

  const selectedFixes: SuggestedFix[] = (result?.fixes ?? []).filter((f) => selected[f.file])

  async function handleApply() {
    if (!result || selectedFixes.length === 0) return
    setApplying(true)
    setApplyError(null)
    try {
      const pr = await applyFixes(repo.id, result.branch, selectedFixes)
      setCreatedPr(pr)
    } catch (err) {
      setApplyError(err instanceof Error ? err.message : 'Failed to create fix PR')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div className="gc-fixes">
      <div className="card gc-fixes-intro">
        <div>
          <h3 className="gc-fixes-title">Auto-fix</h3>
          <p className="gc-fixes-desc">
            Scans up to 10 files for safe, mechanical issues — hardcoded paths, unsafe{' '}
            <code>pickle</code> usage, missing type hints — and proposes fixes as a real diff.
            Nothing touches GitHub until you review and click "Create fix PR".
          </p>
        </div>
        <button className="btn btn-primary" onClick={runScan} disabled={scanning}>
          {scanning ? 'Scanning…' : result ? 'Scan again' : 'Scan for fixes'}
        </button>
      </div>

      {job.status === 'failed' && <p className="gc-fixes-error">{job.error}</p>}

      {scanning && (
        <div className="card gc-fixes-progress">
          <Spinner label={job.stage ?? 'Starting scan...'} />
        </div>
      )}

      {!scanning && !result && (
        <EmptyState
          title="No scan yet"
          description="Run a scan to find safe, auto-fixable issues in this repository."
        />
      )}

      {!scanning && result && result.fixes.length === 0 && (
        <EmptyState
          title="No safe fixes found"
          description="gitcat only proposes fixes it's fully confident about — nothing mechanical stood out this time."
        />
      )}

      {!scanning && result && result.fixes.length > 0 && (
        <>
          <div className="gc-fixes-list">
            {result.fixes.map((fix) => (
              <FixCard key={fix.file} fix={fix} checked={!!selected[fix.file]} onToggle={() => toggle(fix.file)} />
            ))}
          </div>

          <div className="card gc-fixes-apply">
            {createdPr ? (
              <p className="gc-fixes-success">
                Opened{' '}
                <a href={createdPr.html_url} target="_blank" rel="noreferrer">
                  #{createdPr.number} {createdPr.title}
                </a>{' '}
                — review it on GitHub before merging.
              </p>
            ) : (
              <>
                {applyError && <p className="gc-fixes-error">{applyError}</p>}
                <button
                  className="btn btn-primary"
                  onClick={handleApply}
                  disabled={applying || selectedFixes.length === 0}
                >
                  {applying
                    ? 'Creating PR…'
                    : `Create fix PR (${selectedFixes.length} file${selectedFixes.length === 1 ? '' : 's'})`}
                </button>
              </>
            )}
          </div>
        </>
      )}
    </div>
  )
}

function FixCard({
  fix,
  checked,
  onToggle,
}: {
  fix: SuggestedFix
  checked: boolean
  onToggle: () => void
}) {
  return (
    <div className="card gc-fix-card">
      <label className="gc-fix-header">
        <input type="checkbox" checked={checked} onChange={onToggle} />
        <code className="gc-fix-file">{fix.file}</code>
      </label>
      <p className="gc-fix-desc">{fix.description}</p>
      <DiffView diff={fix.diff} />
    </div>
  )
}

function DiffView({ diff }: { diff: string }) {
  const lines = diff.split('\n')
  return (
    <pre className="gc-diff">
      {lines.map((line, i) => {
        let cls = 'gc-diff-ctx'
        if (line.startsWith('+++') || line.startsWith('---')) cls = 'gc-diff-file'
        else if (line.startsWith('@@')) cls = 'gc-diff-hunk'
        else if (line.startsWith('+')) cls = 'gc-diff-add'
        else if (line.startsWith('-')) cls = 'gc-diff-del'
        return (
          <div key={i} className={cls}>
            {line}
          </div>
        )
      })}
    </pre>
  )
}
