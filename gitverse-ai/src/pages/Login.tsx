import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getToken, githubLoginUrl } from '../api'
import GitcatMark from '../components/GitcatMark'
import './Login.css'

const FEATURES = [
  {
    icon: EyeIcon,
    title: 'Automatic PR reviews',
    desc: "Every new pull request gets reviewed the moment it's opened — no one has to remember to ask.",
  },
  {
    icon: SparkleIcon,
    title: 'Auto-fix PRs',
    desc: 'Safe, mechanical issues — hardcoded paths, unsafe deserialization — get fixed in their own PR, ready to review.',
  },
  {
    icon: ShieldIcon,
    title: 'Real status checks',
    desc: 'A pass/fail commit status your branch protection rules can actually require before merging.',
  },
  {
    icon: ChatIcon,
    title: 'Chat with your repo',
    desc: 'Ask questions about any repository and get answers grounded in its actual README, files, and history.',
  },
]

export default function Login() {
  const navigate = useNavigate()

  useEffect(() => {
    if (getToken()) navigate('/repos', { replace: true })
  }, [navigate])

  return (
    <div className="gc-login">
      <div className="gc-login-grid" aria-hidden="true" />
      <div className="gc-login-glow" aria-hidden="true" />

      <div className="gc-login-content">
        <div className="gc-login-topbar gc-fade-up">
          <GitcatMark size={22} />
          <span>gitcat</span>
        </div>

        <section className="gc-login-hero">
          <div className="gc-login-hero-text">
            <div className="gc-login-badge gc-fade-up">
              <span className="gc-login-badge-dot" />
              Powered by Gemini
            </div>
            <h1 className="gc-login-title gc-fade-up" style={{ animationDelay: '40ms' }}>
              Code review that ships <span className="gc-accent-text">with every PR</span>.
            </h1>
            <p className="gc-login-subtitle gc-fade-up" style={{ animationDelay: '80ms' }}>
              gitcat reviews pull requests the moment they're opened, opens its own fix PRs for
              the easy stuff, and gates merges with a real GitHub status check.
            </p>
            <a className="gc-login-btn gc-fade-up" style={{ animationDelay: '120ms' }} href={githubLoginUrl()}>
              <GitHubIcon />
              Continue with GitHub
            </a>
            <p className="gc-login-note gc-fade-up" style={{ animationDelay: '160ms' }}>
              You'll authorize gitcat to read your repositories on your behalf.
            </p>
          </div>

          <div className="gc-mockup gc-fade-up" style={{ animationDelay: '140ms' }}>
            <div className="gc-mockup-bar">
              <span className="gc-mockup-dot" style={{ background: '#ff5f57' }} />
              <span className="gc-mockup-dot" style={{ background: '#febc2e' }} />
              <span className="gc-mockup-dot" style={{ background: '#28c840' }} />
              <span className="gc-mockup-pr">#142</span>
            </div>
            <div className="gc-mockup-title">fix: normalize timestamp parsing across timezones</div>

            <div className="gc-mockup-verdict">
              <CheckIcon />
              <code>gitcat/review</code>
              <span className="gc-mockup-muted">— all checks passed</span>
            </div>

            <p className="gc-mockup-review">
              "Looks solid overall. One suggestion — cache the parsed timezone offset instead
              of recomputing it per row."
            </p>

            <div className="gc-mockup-diff">
              <div className="gc-mockup-diff-add">+ return format_date(dt, tz=user_tz)</div>
              <div className="gc-mockup-diff-del">- return dt.strftime(fmt)</div>
            </div>
          </div>
        </section>

        <section className="gc-login-features">
          {FEATURES.map((f, i) => (
            <div
              key={f.title}
              className="gc-feature-card gc-fade-up"
              style={{ animationDelay: `${260 + i * 40}ms` }}
            >
              <div className="gc-feature-icon">
                <f.icon />
              </div>
              <h3 className="gc-feature-title">{f.title}</h3>
              <p className="gc-feature-desc">{f.desc}</p>
            </div>
          ))}
        </section>
      </div>
    </div>
  )
}

function GitHubIcon() {
  return (
    <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true">
      <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38
        0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53
        .63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95
        0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0
        1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0
        3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01
        8.01 0 0 0 16 8c0-4.42-3.58-8-8-8Z" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor" aria-hidden="true">
      <path d="M13.78 4.22a.75.75 0 0 1 0 1.06l-7.25 7.25a.75.75 0 0 1-1.06 0L2.22 9.28a.75.75 0 0 1
        1.06-1.06L6 10.94l6.72-6.72a.75.75 0 0 1 1.06 0Z" />
    </svg>
  )
}

function EyeIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M1 10s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6Z" stroke="currentColor" strokeWidth="1.4" />
      <circle cx="10" cy="10" r="2.6" fill="currentColor" />
    </svg>
  )
}

function SparkleIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
      <path d="M10 1l1.6 4.4L16 7l-4.4 1.6L10 13l-1.6-4.4L4 7l4.4-1.6L10 1Z" />
      <path d="M16.5 12l.8 2.2 2.2.8-2.2.8-.8 2.2-.8-2.2-2.2-.8 2.2-.8.8-2.2Z" opacity="0.6" />
    </svg>
  )
}

function ShieldIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M10 1.5l7 2.5v5c0 5-3 8-7 9.5-4-1.5-7-4.5-7-9.5v-5l7-2.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
      <path d="M6.5 10.2l2.3 2.3 4.7-4.9" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}

function ChatIcon() {
  return (
    <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
      <path d="M2 4.5A2.5 2.5 0 0 1 4.5 2h11A2.5 2.5 0 0 1 18 4.5v6a2.5 2.5 0 0 1-2.5 2.5H8l-4 3.5v-3.5H4.5A2.5 2.5 0 0 1 2 10.5v-6Z" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  )
}
