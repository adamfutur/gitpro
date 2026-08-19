/**
 * The gitcat mark: a geometric cat face with a git-commit-node accent on one ear.
 * Eyes are cut out using `bg` (the color directly behind the mark), not currentColor,
 * so they stay crisp against any surface — pass the actual surface color when it's not
 * the default card background (e.g. the dark header).
 */
export default function GitcatMark({ size = 24, bg = 'var(--canvas-default)' }: { size?: number; bg?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <polygon points="8,15 14,15 5,3" fill="currentColor" />
      <polygon points="24,15 18,15 27,3" fill="currentColor" />
      <rect x="6" y="13" width="20" height="15" rx="6.5" fill="currentColor" />
      <ellipse cx="12.2" cy="21" rx="1.8" ry="2.2" fill={bg} />
      <ellipse cx="19.8" cy="21" rx="1.8" ry="2.2" fill={bg} />
      <circle cx="27" cy="3.2" r="2" fill="#3fb950" />
    </svg>
  )
}
