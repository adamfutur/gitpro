import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import { useOutletContext } from 'react-router-dom'
import remarkGfm from 'remark-gfm'
import {
  disableShare,
  enableShare,
  getAnalysisHistory,
  getAnalysisJob,
  getDashboard,
  getShareStatus,
  startAnalysis,
  type AnalysisResult,
  type Anomaly,
  type Kpis,
} from '../../api'
import EmptyState from '../../components/EmptyState'
import HorizontalBarChart, { type BarChartItem } from '../../components/HorizontalBarChart'
import LineChart, { type LineChartPoint } from '../../components/LineChart'
import Spinner from '../../components/Spinner'
import { statusForHighIsBad, statusForHighIsGood } from '../../lib/status'
import type { RepoOutletContext } from '../RepoDetail'
import './AnalysisTab.css'

const JOB_KEY = 'analysis'

export default function AnalysisTab() {
  const { repo, analysisJobs } = useOutletContext<RepoOutletContext>()
  const [checkingExisting, setCheckingExisting] = useState(true)
  const job = analysisJobs.getState(JOB_KEY)

  useEffect(() => {
    // Only do the one-time "is there already an analysis?" check the first time this repo's
    // Analysis tab is visited in this session — if a job is already tracked (running/done/failed
    // from an earlier visit), that state lives in RepoDetail and survives tab switches, so skip it.
    if (job.status !== 'idle') {
      setCheckingExisting(false)
      return
    }
    let cancelled = false
    getDashboard(repo.id)
      .then((data) => {
        if (cancelled || !data) return
        analysisJobs.hydrate(JOB_KEY, {
          repo_id: data.repo_id,
          repo_name: repo.name,
          repo_full_name: repo.full_name,
          analysis: '',
          kpis: data.kpis,
          anomalies: data.anomalies,
          generated_at: data.generated_at,
          status: data.status,
        })
      })
      .finally(() => !cancelled && setCheckingExisting(false))
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [repo.id])

  function runAnalysis() {
    analysisJobs.run(
      JOB_KEY,
      () => startAnalysis(repo.id),
      (jobId) => getAnalysisJob(repo.id, jobId)
    )
  }

  const analyzing = job.status === 'running'
  const result: AnalysisResult | null = job.status === 'completed' ? job.result : null

  if (checkingExisting) {
    return (
      <div className="gc-analysis-loading">
        <Spinner label="Checking for existing analysis..." />
      </div>
    )
  }

  return (
    <div className="gc-analysis">
      <div className="gc-analysis-toolbar">
        {result ? (
          <p className="gc-analysis-generated">
            Last generated {new Date(result.generated_at).toLocaleString()}
          </p>
        ) : (
          <span />
        )}
        <button className="btn btn-primary" onClick={runAnalysis} disabled={analyzing}>
          {analyzing ? 'Analyzing…' : result ? 'Re-run analysis' : 'Run analysis'}
        </button>
      </div>

      {job.status === 'failed' && <p className="gc-analysis-error">{job.error}</p>}

      {analyzing && (
        <div className="card gc-analysis-progress">
          <Spinner label={job.stage ?? 'Starting analysis...'} />
        </div>
      )}

      {!analyzing && !result && (
        <EmptyState
          title="No analysis yet"
          description="Run analysis to get an AI code review, quality KPIs, and anomaly detection for this repository."
        />
      )}

      {!analyzing && result && (
        <>
          <SummaryCard summary={result.kpis.summary} />

          <TrendChart repoId={repo.id} refreshKey={result.generated_at} />

          <ShareToggle repoId={repo.id} />

          <CategoryScoreChart kpis={result.kpis} />

          <div className="gc-kpi-grid">
            <KpiCard title="Quality" metrics={qualityRows(result.kpis)} />
            <KpiCard title="Maintainability" metrics={maintainabilityRows(result.kpis)} />
            <KpiCard title="Productivity" metrics={productivityRows(result.kpis)} />
            <KpiCard title="Security" metrics={securityRows(result.kpis)} />
          </div>

          {result.analysis && (
            <div className="card gc-analysis-writeup">
              <h3>AI code review</h3>
              <div className="gc-markdown">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result.analysis}</ReactMarkdown>
              </div>
            </div>
          )}

          <AnomalyList anomalies={result.anomalies} />
        </>
      )}
    </div>
  )
}

function TrendChart({ repoId, refreshKey }: { repoId: number; refreshKey: string }) {
  const [points, setPoints] = useState<LineChartPoint[] | null>(null)

  useEffect(() => {
    let cancelled = false
    getAnalysisHistory(repoId)
      .then((res) => {
        if (cancelled) return
        setPoints(
          res.history
            .filter((h) => h.overall_health_score != null)
            .map((h) => ({
              label: new Date(h.generated_at).toLocaleDateString(),
              value: h.overall_health_score as number,
            }))
        )
      })
      .catch(() => !cancelled && setPoints([]))
    return () => {
      cancelled = true
    }
    // Re-fetch once a fresh analysis finishes, so a just-completed run's point shows up
  }, [repoId, refreshKey])

  // A trend needs at least two runs to mean anything
  if (!points || points.length < 2) return null

  return (
    <div className="card gc-trend-card">
      <h3>Health score trend</h3>
      <LineChart points={points} min={0} max={100} />
      <p className="gc-trend-caption">{points.length} analysis runs</p>
    </div>
  )
}

function ShareToggle({ repoId }: { repoId: number }) {
  const [enabled, setEnabled] = useState<boolean | null>(null)
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setEnabled(null)
    setError(null)
    getShareStatus(repoId)
      .then((res) => setEnabled(res.enabled))
      .catch((err) => setError(err instanceof Error ? err.message : 'Failed to load share status'))
  }, [repoId])

  const shareUrl = `${window.location.origin}/share/${repoId}`

  async function toggle() {
    setBusy(true)
    setError(null)
    try {
      const res = enabled ? await disableShare(repoId) : await enableShare(repoId)
      setEnabled(res.enabled)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update sharing')
    } finally {
      setBusy(false)
    }
  }

  async function copyLink() {
    await navigator.clipboard.writeText(shareUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="card gc-share-toggle">
      <div className="gc-share-toggle-main">
        <div>
          <h4 className="gc-share-toggle-title">Public shareable card</h4>
          <p className="gc-share-toggle-desc">
            A public, no-login page anyone with the link can view — good for READMEs or
            sharing the result.
          </p>
        </div>
        <button className={`btn ${enabled ? '' : 'btn-primary'}`} onClick={toggle} disabled={enabled === null || busy}>
          {busy ? 'Working…' : enabled ? 'Disable' : 'Enable'}
        </button>
      </div>
      {error && <p className="gc-analysis-error">{error}</p>}
      {enabled && (
        <div className="gc-share-toggle-link">
          <code>{shareUrl}</code>
          <button className="btn" onClick={copyLink}>
            {copied ? 'Copied!' : 'Copy'}
          </button>
        </div>
      )}
    </div>
  )
}

function SummaryCard({ summary }: { summary: Kpis['summary'] }) {
  return (
    <div className="card gc-summary-card">
      <div className={`gc-grade gc-grade-${summary.grade}`}>{summary.grade}</div>
      <div>
        <div className="gc-summary-score">{summary.overall_health_score} / 100</div>
        <div className="gc-summary-label">
          Overall health score · {summary.analyzed_files} files analyzed
        </div>
      </div>
    </div>
  )
}

function CategoryScoreChart({ kpis }: { kpis: Kpis }) {
  const security = kpis.security.risk_score != null ? Math.max(0, 100 - kpis.security.risk_score) : undefined

  const candidates: { key: string; label: string; value: number | undefined; tooltip: string }[] = [
    { key: 'quality', label: 'Quality', value: kpis.quality.quality_score, tooltip: 'Quality score' },
    {
      key: 'maintainability',
      label: 'Maintainability',
      value: kpis.maintainability.maintainability_index,
      tooltip: 'Maintainability index',
    },
    {
      key: 'productivity',
      label: 'Productivity',
      value: kpis.productivity.productivity_score,
      tooltip: 'Productivity score',
    },
    {
      key: 'security',
      label: 'Security',
      value: security,
      tooltip: `Security score: ${security} (100 minus risk score ${kpis.security.risk_score})`,
    },
  ]

  const items: BarChartItem[] = candidates
    .filter((item) => item.value != null)
    .map((item) => ({
      key: item.key,
      label: item.label,
      value: item.value as number,
      tooltip: item.tooltip,
      level: statusForHighIsGood(item.value as number),
      valueLabel: `${Math.round(item.value as number)}`,
    }))

  if (items.length === 0) return null

  return (
    <div className="card gc-chart-card">
      <h3>Category scores</h3>
      <HorizontalBarChart
        items={items}
        max={100}
        legendBands={[
          { level: 'good', caption: '(80+)' },
          { level: 'warning', caption: '(60–79)' },
          { level: 'serious', caption: '(40–59)' },
          { level: 'critical', caption: '(<40)' },
        ]}
      />
    </div>
  )
}

function KpiCard({ title, metrics }: { title: string; metrics: [string, string | number][] }) {
  return (
    <div className="card gc-kpi-card">
      <h4>{title}</h4>
      <dl>
        {metrics.map(([label, value]) => (
          <div className="gc-kpi-row" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}

function AnomalyList({ anomalies }: { anomalies: Anomaly[] }) {
  const chartItems: BarChartItem[] = [...anomalies]
    .sort((a, b) => b.score - a.score)
    .map((a) => ({
      key: a.file,
      label: a.file,
      value: a.score,
      level: statusForHighIsBad(a.score),
      valueLabel: `${a.score}`,
      tooltip: `${a.file}: ${a.score}/100 — ${a.description}`,
    }))

  return (
    <div className="card gc-anomalies">
      <h3>Anomalies {anomalies.length > 0 && `(${anomalies.length})`}</h3>
      {anomalies.length === 0 ? (
        <p className="gc-anomalies-empty">No statistical outliers detected across analyzed files.</p>
      ) : (
        <>
          <HorizontalBarChart
            items={chartItems}
            max={100}
            legendBands={[
              { level: 'critical', caption: '(80+)' },
              { level: 'serious', caption: '(60–79)' },
              { level: 'warning', caption: '(40–59)' },
              { level: 'good', caption: '(<40)' },
            ]}
          />
          <ul className="gc-anomaly-list">
          {anomalies.map((a) => (
            <li key={a.file} className="gc-anomaly-item">
              <div className="gc-anomaly-top">
                <code>{a.file}</code>
                <span className="gc-anomaly-score">{a.score}/100</span>
              </div>
              <div className="gc-anomaly-types">
                {a.types.map((t) => (
                  <span key={t} className="gc-anomaly-type">
                    {t}
                  </span>
                ))}
              </div>
              <p className="gc-anomaly-desc">{a.description}</p>
            </li>
          ))}
          </ul>
        </>
      )}
    </div>
  )
}

function qualityRows(kpis: Kpis): [string, string | number][] {
  const q = kpis.quality
  return [
    ['Quality score', q.quality_score ?? '—'],
    ['Avg. complexity', q.avg_complexity ?? '—'],
    ['Code smell density', q.code_smell_density ?? '—'],
    ['Documentation coverage', q.documentation_coverage != null ? `${q.documentation_coverage}%` : '—'],
    ['Total code smells', q.total_code_smells ?? '—'],
    ['Lines of code', q.total_lines_of_code ?? '—'],
  ]
}

function maintainabilityRows(kpis: Kpis): [string, string | number][] {
  const m = kpis.maintainability
  return [
    ['Maintainability index', m.maintainability_index ?? '—'],
    ['Naming consistency', m.naming_consistency != null ? `${m.naming_consistency}%` : '—'],
    ['Vocabulary richness', m.vocabulary_richness != null ? `${m.vocabulary_richness}%` : '—'],
    ['Technical debt', m.technical_debt_days != null ? `${m.technical_debt_days} days` : '—'],
  ]
}

function productivityRows(kpis: Kpis): [string, string | number][] {
  const p = kpis.productivity
  return [
    ['Productivity score', p.productivity_score ?? '—'],
    ['Recent commits', p.commit_frequency ?? '—'],
    ['PR merge rate', p.pr_merge_rate != null ? `${p.pr_merge_rate}%` : '—'],
    ['Active contributors', p.active_contributors ?? '—'],
  ]
}

function securityRows(kpis: Kpis): [string, string | number][] {
  const s = kpis.security
  return [
    ['Risk score', s.risk_score ?? '—'],
    ['Security issues flagged', s.security_issue_count ?? '—'],
    ['High-complexity files', s.high_complexity_files ?? '—'],
  ]
}
