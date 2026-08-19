import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { getPublicCard, type PublicCard } from '../api'
import GitcatMark from '../components/GitcatMark'
import './ShareCard.css'

export default function ShareCard() {
  const { repoId } = useParams<{ repoId: string }>()
  const [card, setCard] = useState<PublicCard | null>(null)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    if (!repoId) return
    getPublicCard(Number(repoId))
      .then(setCard)
      .catch(() => setNotFound(true))
  }, [repoId])

  return (
    <div className="gc-share-page">
      <div className="gc-login-grid" aria-hidden="true" />
      <div className="gc-login-glow" aria-hidden="true" />

      <div className="gc-share-content">
        <Link to="/" className="gc-share-brand">
          <GitcatMark size={22} />
          <span>gitcat</span>
        </Link>

        {notFound && (
          <div className="gc-share-card gc-share-notfound">
            <h1>This card isn't public</h1>
            <p>The owner hasn't shared this repository's analysis, or hasn't run one yet.</p>
          </div>
        )}

        {!notFound && !card && <div className="gc-share-loading">Loading…</div>}

        {card && (
          <div className="gc-share-card">
            <div className="gc-share-header">
              <span className="gc-share-repo">{card.repo_full_name}</span>
              <span className={`gc-share-grade gc-grade-${card.grade}`}>{card.grade}</span>
            </div>

            <div className="gc-share-score">
              <span className="gc-share-score-value">{card.overall_health_score}</span>
              <span className="gc-share-score-max">/100</span>
            </div>
            <p className="gc-share-score-label">Overall health score · {card.analyzed_files} files analyzed</p>

            <div className="gc-share-stats">
              <ShareStat label="Quality" value={card.quality_score} />
              <ShareStat label="Maintainability" value={card.maintainability_index} />
              <ShareStat label="Productivity" value={card.productivity_score} />
              <ShareStat label="Security risk" value={card.security_risk_score} />
            </div>

            <div className="gc-share-footer">
              <span>Analyzed by gitcat · {new Date(card.generated_at).toLocaleDateString()}</span>
              <Link to="/" className="btn btn-primary">
                Analyze your repo
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function ShareStat({ label, value }: { label: string; value: number | null }) {
  return (
    <div className="gc-share-stat">
      <div className="gc-share-stat-value">{value ?? '—'}</div>
      <div className="gc-share-stat-label">{label}</div>
    </div>
  )
}
