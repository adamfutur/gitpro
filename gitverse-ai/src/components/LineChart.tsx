import './LineChart.css'

export interface LineChartPoint {
  label: string
  value: number
}

const VIEW_WIDTH = 600
const VIEW_HEIGHT = 160
const PAD_LEFT = 8
const PAD_RIGHT = 36
const PAD_Y = 16

/** A single-series trend line: 2px stroke, round caps, direct end-label, hover tooltip per point. */
export default function LineChart({
  points,
  min = 0,
  max = 100,
  color = 'var(--accent-fg)',
  valueSuffix = '',
}: {
  points: LineChartPoint[]
  min?: number
  max?: number
  color?: string
  valueSuffix?: string
}) {
  const innerW = VIEW_WIDTH - PAD_LEFT - PAD_RIGHT
  const innerH = VIEW_HEIGHT - PAD_Y * 2
  const n = points.length

  const xFor = (i: number) => PAD_LEFT + (n === 1 ? innerW / 2 : (innerW * i) / (n - 1))
  const yFor = (v: number) => {
    const clamped = Math.max(min, Math.min(max, v))
    return PAD_Y + innerH - ((clamped - min) / (max - min)) * innerH
  }

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xFor(i).toFixed(1)} ${yFor(p.value).toFixed(1)}`)
    .join(' ')

  const last = points[n - 1]

  return (
    <svg className="gc-linechart" viewBox={`0 0 ${VIEW_WIDTH} ${VIEW_HEIGHT}`} width="100%" role="img">
      <line
        className="gc-linechart-baseline"
        x1={PAD_LEFT}
        y1={PAD_Y + innerH}
        x2={VIEW_WIDTH - PAD_RIGHT}
        y2={PAD_Y + innerH}
      />

      <path d={pathD} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />

      {points.map((p, i) => {
        const isLast = i === n - 1
        return (
          <g key={i}>
            <circle cx={xFor(i)} cy={yFor(p.value)} r={isLast ? 4 : 2.5} fill={color} />
            {/* Larger transparent hit target so the tooltip is easy to trigger, not just the tiny dot */}
            <circle cx={xFor(i)} cy={yFor(p.value)} r={10} fill="transparent" tabIndex={0}>
              <title>{`${p.label}: ${p.value}${valueSuffix}`}</title>
            </circle>
          </g>
        )
      })}

      {last && (
        <text x={xFor(n - 1) + 9} y={yFor(last.value) + 4} className="gc-linechart-endlabel" fill={color}>
          {last.value}
          {valueSuffix}
        </text>
      )}
    </svg>
  )
}
