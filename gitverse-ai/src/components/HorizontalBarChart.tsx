import { STATUS_LABEL, STATUS_VAR, type StatusLevel } from '../lib/status'
import './HorizontalBarChart.css'

export interface BarChartItem {
  key: string
  label: string
  value: number
  level: StatusLevel
  valueLabel: string
  tooltip?: string
}

export interface LegendBand {
  level: StatusLevel
  caption: string
}

export default function HorizontalBarChart({
  items,
  max,
  legendBands,
}: {
  items: BarChartItem[]
  max: number
  legendBands: LegendBand[]
}) {
  return (
    <div className="gc-barchart">
      <div className="gc-barchart-rows" role="list">
        {items.map((item) => {
          const pct = Math.max(0, Math.min(100, (item.value / max) * 100))
          return (
            <div
              key={item.key}
              className="gc-barchart-row"
              role="listitem"
              tabIndex={0}
              title={item.tooltip ?? `${item.label}: ${item.valueLabel}`}
            >
              <span className="gc-barchart-label">{item.label}</span>
              <span className="gc-barchart-track">
                <span
                  className="gc-barchart-fill"
                  style={{ width: `${pct}%`, background: STATUS_VAR[item.level] }}
                />
              </span>
              <span className="gc-barchart-value">{item.valueLabel}</span>
            </div>
          )
        })}
      </div>

      <div className="gc-barchart-legend">
        {legendBands.map((band) => (
          <span key={band.level} className="gc-barchart-legend-item">
            <span className="gc-barchart-swatch" style={{ background: STATUS_VAR[band.level] }} />
            {STATUS_LABEL[band.level]} {band.caption}
          </span>
        ))}
      </div>
    </div>
  )
}
