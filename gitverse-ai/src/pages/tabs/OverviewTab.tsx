import { useOutletContext } from 'react-router-dom'
import { formatRelativeTime } from '../../lib/time'
import type { RepoOutletContext } from '../RepoDetail'
import './OverviewTab.css'

export default function OverviewTab() {
  const { repo } = useOutletContext<RepoOutletContext>()

  const rows: [string, string][] = [
    ['Full name', repo.full_name],
    ['Visibility', repo.private ? 'Private' : 'Public'],
    ['Default branch', repo.default_branch],
    ['Created', formatRelativeTime(repo.created_at)],
    ['Last updated', formatRelativeTime(repo.updated_at)],
  ]

  return (
    <div className="card gc-overview">
      <h3 className="gc-overview-title">Repository details</h3>
      <dl className="gc-overview-list">
        {rows.map(([label, value]) => (
          <div className="gc-overview-row" key={label}>
            <dt>{label}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
      <p className="gc-overview-hint">
        Head to the <strong>Analysis</strong> tab for an AI-generated code quality report, or
        <strong> Chat</strong> to ask questions about this repository.
      </p>
    </div>
  )
}
