// A subset of GitHub's linguist language colors.
const LANGUAGE_COLORS: Record<string, string> = {
  JavaScript: '#f1e05a',
  TypeScript: '#3178c6',
  Python: '#3572A5',
  Java: '#b07219',
  Go: '#00ADD8',
  Rust: '#dea584',
  Ruby: '#701516',
  PHP: '#4F5D95',
  'C++': '#f34b7d',
  C: '#555555',
  'C#': '#178600',
  Swift: '#F05138',
  Kotlin: '#A97BFF',
  HTML: '#e34c26',
  CSS: '#563d7c',
  Shell: '#89e051',
  Vue: '#41b883',
  Dart: '#00B4AB',
  Scala: '#c22d40',
  Elixir: '#6e4a7e',
  Lua: '#000080',
  Haskell: '#5e5086',
}

const FALLBACK_COLOR = '#8b949e'

export function getLanguageColor(language: string | null | undefined): string {
  if (!language) return FALLBACK_COLOR
  return LANGUAGE_COLORS[language] ?? FALLBACK_COLOR
}
