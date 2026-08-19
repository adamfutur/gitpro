import './Spinner.css'

export default function Spinner({ label }: { label?: string }) {
  return (
    <div className="gc-spinner-wrap" role="status" aria-live="polite">
      <span className="gc-spinner" />
      {label && <span className="gc-spinner-label">{label}</span>}
    </div>
  )
}
