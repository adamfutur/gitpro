import { useMemo, useState } from 'react'
import type { ChangeImpactGraph } from '../api'
import './ChangeImpactGraph.css'

const COLS = 4
const W = 900
const CELL_W = 220
const CELL_H = 96
const OFFSET_X = 28
const OFFSET_Y = 24

export default function ChangeImpactGraphView({ graph }: { graph: ChangeImpactGraph }) {
  const [selected, setSelected] = useState<string | null>(null)
  const current = graph.nodes.find(n => n.id === selected) ?? graph.nodes.find(n => n.changed) ?? graph.nodes[0]
  const positions = useMemo(() => new Map(graph.nodes.map((node, index) => [
    node.id,
    { x: OFFSET_X + (index % COLS) * CELL_W, y: OFFSET_Y + Math.floor(index / COLS) * CELL_H },
  ])), [graph.nodes])
  const height = Math.max(120, Math.ceil(graph.nodes.length / COLS) * CELL_H + 20)
  const incoming = current ? graph.edges.filter(edge => edge.to === current.id).map(edge => edge.from) : []
  const outgoing = current ? graph.edges.filter(edge => edge.from === current.id).map(edge => edge.to) : []

  return (
    <section className="card gc-impact">
      <div className="gc-impact-heading">
        <div>
          <span className="gc-impact-eyebrow">STATIC DEPENDENCY INTELLIGENCE</span>
          <h3>Change Impact Graph</h3>
          <p>Trace direct imports and identify which sampled files depend on changed code.</p>
        </div>
        <div className="gc-impact-metrics">
          <strong>{graph.nodes.length}</strong><span>files mapped</span>
          <strong>{graph.edges.length}</strong><span>connections</span>
        </div>
      </div>
      <p className="gc-impact-note">{graph.note}</p>
      {graph.partial && (
        <p className="gc-impact-warning" role="status">
          Partial coverage: {graph.changed_files_in_sample} of {graph.changed_files} changed files were found in the {graph.sampled_source_files}-file source sample. Unmapped impact is unknown.
        </p>
      )}
      {graph.nodes.length === 0 ? (
        <p className="gc-impact-empty">No static import relationships could be mapped from the available source sample.</p>
      ) : (
        <>
          <div className="gc-impact-legend">
            <span><i className="gc-impact-dot changed" /> Changed file</span>
            <span><i className="gc-impact-dot nearby" /> Connected file</span>
            <span>Arrows point toward imported dependencies</span>
          </div>
          <div className="gc-impact-canvas" aria-label="File import network">
            <svg viewBox={`0 0 ${W} ${height}`} role="img" aria-label="Static import connections between inspected source files">
              <defs>
                <marker id="gc-impact-arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
                  <path d="M0 0 L8 4 L0 8 Z" fill="var(--fg-subtle)" />
                </marker>
              </defs>
              {graph.edges.map((edge, i) => {
                const a = positions.get(edge.from)
                const b = positions.get(edge.to)
                if (!a || !b) return null
                return <line key={i} x1={a.x + 78} y1={a.y + 26} x2={b.x + 78} y2={b.y + 26}
                  stroke="var(--fg-subtle)" strokeOpacity=".5" strokeWidth="1.8" markerEnd="url(#gc-impact-arrow)" />
              })}
              {graph.nodes.map(node => {
                const p = positions.get(node.id)
                if (!p) return null
                const active = current?.id === node.id
                const label = node.id.length > 25 ? '…' + node.id.slice(-24) : node.id
                return (
                  <g key={node.id} onClick={() => setSelected(node.id)}
                    onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelected(node.id) } }}
                    role="button" tabIndex={0} aria-label={`Inspect ${node.id}`} className="gc-impact-node"
                    transform={`translate(${p.x} ${p.y})`}>
                    <title>{node.id}</title>
                    <rect width="158" height="52" rx="9"
                      fill={node.changed ? 'var(--attention-subtle)' : 'var(--accent-subtle)'}
                      stroke={active ? 'var(--accent-fg)' : node.changed ? 'var(--attention-fg)' : 'var(--border-default)'}
                      strokeWidth={active ? 2.5 : 1.1} />
                    <text x="10" y="22" fontSize="11" fontWeight="600" fill="var(--fg-default)">{label}</text>
                    <text x="10" y="39" fontSize="10" fill="var(--fg-muted)">{node.changed ? 'Changed' : 'Connected'} · {node.direct_dependents} inbound</text>
                  </g>
                )
              })}
            </svg>
          </div>
          {current && (
            <div className="gc-impact-inspector">
              <h4>Selected: <code>{current.id}</code></h4>
              <p><strong>Imported by:</strong> {incoming.length ? incoming.join(', ') : 'No direct dependents found in sample'}</p>
              <p><strong>Imports:</strong> {outgoing.length ? outgoing.join(', ') : 'No local imports found in sample'}</p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
