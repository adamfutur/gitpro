import type { PrRiskRadar } from '../api'
import './RiskRadar.css'

export default function RiskRadar({ data }: { data: PrRiskRadar }) {
  const label = data.level === 'high' ? 'High attention' : data.level === 'medium' ? 'Review carefully' : 'Lower attention'
  const copySummary = () => {
    const lines = [
      'gitcat PR Risk Radar',
      `Review-priority score: ${data.score}/100 (${label})`,
      data.method,
      ...data.files.map(f => `- ${f.path} (${f.score}/100): ${f.reasons.join(', ')}`),
      'Review checklist:',
      ...data.review_checklist.map(t => `- ${t}`),
      `AI review coverage: ${data.coverage.files_selected_for_ai}/${data.coverage.changed_files} changed files selected; ${data.coverage.files_with_patches} patches available; ${data.coverage.files_with_truncated_patches} truncated.`,
    ]
    void navigator.clipboard.writeText(lines.join('\n')).catch(() => {})
  }

  return (
    <section className="card gc-radar" aria-label="PR Risk Radar">
      <div className="gc-radar-top">
        <div>
          <span className="gc-radar-eyebrow">CHANGE INTELLIGENCE</span>
          <h3>PR Risk Radar</h3>
          <p className="gc-radar-muted">Explainable review priorities before you merge.</p>
        </div>
        <div className={`gc-radar-score is-${data.level}`} aria-label={`Review priority ${data.score} out of 100`}>
          <strong>{data.score}</strong><span>/100</span>
        </div>
      </div>
      <div className="gc-radar-status">
        <strong>{label}</strong>
        <span>{data.method}</span>
      </div>
      {!data.coverage.complete && (
        <div className="gc-radar-warning" role="status">
          <strong>AI review coverage is incomplete.</strong> Selected {data.coverage.files_selected_for_ai} of {data.coverage.changed_files} changed files; {data.coverage.files_with_patches} have available patches, and {data.coverage.files_with_truncated_patches} were truncated.
          {data.coverage.files_not_selected > 0 && ` ${data.coverage.files_not_selected} files were outside the AI review limit.`}
        </div>
      )}
      <h4>Files to inspect first</h4>
      {data.files.length === 0 ? <p className="gc-radar-muted">No changed files found.</p> : (
        <div className="gc-radar-files">
          {data.files.map(file => (
            <div className="gc-radar-file" key={file.path}>
              <div className="gc-radar-file-title">
                <code title={file.path}>{file.path}</code>
                <span className={`gc-radar-pill is-${file.level}`}>{file.score}/100</span>
              </div>
              <div className="gc-radar-bar" aria-hidden="true">
                <div className={`is-${file.level}`} style={{ width: `${file.score}%` }} />
              </div>
              <span className="gc-radar-muted">{file.reasons.join(' · ')} · {file.changes} changed lines</span>
            </div>
          ))}
        </div>
      )}
      <div className="gc-radar-bottom">
        <div>
          <h4>Before you merge</h4>
          <ul>{data.review_checklist.map((tip, index) => <li key={index}>{tip}</li>)}</ul>
        </div>
        <button type="button" className="btn" onClick={copySummary}>Copy report</button>
      </div>
    </section>
  )
}
