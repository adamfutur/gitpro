export type StatusLevel = 'good' | 'warning' | 'serious' | 'critical'

export const STATUS_VAR: Record<StatusLevel, string> = {
  good: 'var(--status-good)',
  warning: 'var(--status-warning)',
  serious: 'var(--status-serious)',
  critical: 'var(--status-critical)',
}

export const STATUS_LABEL: Record<StatusLevel, string> = {
  good: 'Good',
  warning: 'Fair',
  serious: 'Serious',
  critical: 'Critical',
}

/** For scores where higher is better (quality, maintainability, productivity, security). */
export function statusForHighIsGood(score: number): StatusLevel {
  if (score >= 80) return 'good'
  if (score >= 60) return 'warning'
  if (score >= 40) return 'serious'
  return 'critical'
}

/** For scores where higher is worse (anomaly severity). */
export function statusForHighIsBad(score: number): StatusLevel {
  if (score >= 80) return 'critical'
  if (score >= 60) return 'serious'
  if (score >= 40) return 'warning'
  return 'good'
}
