import { useEffect, useRef, useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import { getDiagramJob, startDiagram } from '../../api'
import EmptyState from '../../components/EmptyState'
import Spinner from '../../components/Spinner'
import type { RepoOutletContext } from '../RepoDetail'
import './DiagramTab.css'

const JOB_KEY = 'diagram'

export default function DiagramTab() {
  const { repo, diagramJobs } = useOutletContext<RepoOutletContext>()
  const job = diagramJobs.getState(JOB_KEY)
  const generating = job.status === 'running'
  const result = job.status === 'completed' ? job.result : null

  const [showSource, setShowSource] = useState(false)

  function runGenerate() {
    diagramJobs.run(
      JOB_KEY,
      () => startDiagram(repo.id),
      (jobId) => getDiagramJob(repo.id, jobId)
    )
  }

  return (
    <div className="gc-diagram">
      <div className="card gc-diagram-intro">
        <div>
          <h3 className="gc-diagram-title">Architecture diagram</h3>
          <p className="gc-diagram-desc">
            Generates a live architecture diagram straight from the code — main components,
            how they connect — no docs required.
          </p>
        </div>
        <button className="btn btn-primary" onClick={runGenerate} disabled={generating}>
          {generating ? 'Generating…' : result ? 'Regenerate' : 'Generate diagram'}
        </button>
      </div>

      {job.status === 'failed' && <p className="gc-diagram-error">{job.error}</p>}

      {generating && (
        <div className="card gc-diagram-progress">
          <Spinner label={job.stage ?? 'Starting...'} />
        </div>
      )}

      {!generating && !result && (
        <EmptyState
          title="No diagram yet"
          description="Generate one to see this repository's architecture visualized."
        />
      )}

      {!generating && result && (
        <div className="card gc-diagram-card">
          <div className="gc-diagram-toolbar">
            <span className="gc-diagram-generated">
              Generated {new Date(result.generated_at).toLocaleString()}
            </span>
            <button className="btn" onClick={() => setShowSource((s) => !s)}>
              {showSource ? 'View diagram' : 'View source'}
            </button>
          </div>

          {result.diagram ? (
            showSource ? (
              <pre className="gc-diagram-source">{result.diagram}</pre>
            ) : (
              <MermaidRender source={result.diagram} />
            )
          ) : (
            <EmptyState
              title="Couldn't generate a diagram"
              description="Gemini didn't return a usable diagram for this repository. Try again — larger or more unusual repo layouts sometimes need a second pass."
            />
          )}
        </div>
      )}
    </div>
  )
}

function MermaidRender({ source }: { source: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setError(null)

    async function render() {
      try {
        const { default: mermaid } = await import('mermaid')
        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
        mermaid.initialize({ startOnLoad: false, theme: prefersDark ? 'dark' : 'default', securityLevel: 'strict' })

        const id = `gc-mermaid-${Date.now()}`
        const { svg } = await mermaid.render(id, source)
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Failed to render diagram')
      }
    }

    render()
    return () => {
      cancelled = true
    }
  }, [source])

  if (error) {
    return (
      <EmptyState
        title="Couldn't render this diagram"
        description="The generated Mermaid syntax wasn't valid. Try regenerating, or view the raw source above."
      />
    )
  }

  return <div className="gc-diagram-render" ref={containerRef} />
}
