const API_URL = import.meta.env.VITE_API_URL as string

const TOKEN_KEY = 'gitpro_token'

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearToken() {
  localStorage.removeItem(TOKEN_KEY)
}

export function githubLoginUrl(): string {
  return `${API_URL}/api/auth/github`
}

class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

async function request(path: string, options: RequestInit = {}) {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(body.error || `Request failed: ${res.status}`, res.status)
  }
  return res.json()
}

/** Like request(), but resolves to null instead of throwing on a 404. */
async function requestOptional(path: string, options: RequestInit = {}) {
  try {
    return await request(path, options)
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) return null
    throw err
  }
}

export interface User {
  id: number
  login: string
  name: string | null
  avatar_url: string
  html_url: string
}

export interface Repo {
  id: number
  name: string
  full_name: string
  description: string | null
  language: string | null
  stars_count: number
  forks_count: number
  open_issues_count: number
  default_branch: string
  private: boolean
  html_url: string
  created_at: string
  updated_at: string
  analysis_status: string
}

export interface QualityKpis {
  quality_score: number
  avg_complexity: number
  code_smell_density: number
  documentation_coverage: number
  total_code_smells: number
  total_lines_of_code: number
}

export interface MaintainabilityKpis {
  maintainability_index: number
  naming_consistency: number
  vocabulary_richness: number
  technical_debt_hours: number
  technical_debt_days: number
}

export interface ProductivityKpis {
  productivity_score: number
  commit_frequency: number
  pr_merge_rate: number
  avg_pr_size: number
  active_contributors: number
}

export interface SecurityKpis {
  security_issue_count: number
  risk_score: number
  high_complexity_files: number
}

export interface KpiSummary {
  overall_health_score: number
  grade: string
  analyzed_files: number
  timestamp?: string
}

export interface Kpis {
  quality: Partial<QualityKpis>
  maintainability: Partial<MaintainabilityKpis>
  productivity: Partial<ProductivityKpis>
  security: Partial<SecurityKpis>
  summary: KpiSummary
}

export interface Anomaly {
  file: string
  score: number
  types: string[]
  description: string
  metrics: {
    complexity: number
    lines: number
    comment_ratio: number
    smells: number
  }
}

export interface AnalysisResult {
  repo_id: number
  repo_name: string
  repo_full_name: string
  analysis: string
  kpis: Kpis
  anomalies: Anomaly[]
  generated_at: string
  status: string
}

export interface DashboardData {
  repo_id: number
  kpis: Kpis
  anomalies: Anomaly[]
  generated_at: string
  status: string
}

export interface AnalysisHistoryPoint {
  generated_at: string
  grade: string
  overall_health_score: number | null
  quality_score: number | null
  maintainability_index: number | null
  productivity_score: number | null
  security_risk_score: number | null
}

export type AnalysisJobStatus = 'pending' | 'running' | 'completed' | 'failed'

export interface AnalysisJob {
  job_id: string
  status: AnalysisJobStatus
  stage: string
  started_at: string
  finished_at: string | null
  result?: AnalysisResult
  error?: string
}

export interface PullRequestSummary {
  number: number
  title: string
  state: string
  user: string
  created_at: string
  updated_at: string
  html_url: string
  draft: boolean
}

export interface PrFileChange {
  filename: string
  status: string
  additions: number
  deletions: number
}

export interface PrVerdict {
  status: 'pass' | 'fail'
  reason: string
}

export interface PrAnalysisResult {
  repo_id: number
  pr_number: number
  title: string
  html_url: string
  author: string
  head_sha: string
  files_changed: number
  additions: number
  deletions: number
  files: PrFileChange[]
  review: string
  verdict: PrVerdict
  generated_at: string
  status: string
}

export interface PrAnalysisJob {
  job_id: string
  status: AnalysisJobStatus
  stage: string
  started_at: string
  finished_at: string | null
  result?: PrAnalysisResult
  error?: string
}

export interface SuggestedFix {
  file: string
  description: string
  diff: string
  new_content: string
}

export interface FixScanResult {
  repo_id: number
  branch: string
  fixes: SuggestedFix[]
}

export interface FixScanJob {
  job_id: string
  status: AnalysisJobStatus
  stage: string
  started_at: string
  finished_at: string | null
  result?: FixScanResult
  error?: string
}

export interface CreatedFixPr {
  number: number
  html_url: string
  title: string
}

export interface DiagramResult {
  repo_id: number
  repo_full_name: string
  diagram: string
  generated_at: string
}

export interface DiagramJob {
  job_id: string
  status: AnalysisJobStatus
  stage: string
  started_at: string
  finished_at: string | null
  result?: DiagramResult
  error?: string
}

export interface PublicCard {
  repo_name: string
  repo_full_name: string
  grade: string
  overall_health_score: number
  analyzed_files: number
  quality_score: number | null
  maintainability_index: number | null
  productivity_score: number | null
  security_risk_score: number | null
  generated_at: string
}

export function getMe(): Promise<User> {
  return request('/api/auth/me')
}

export function listRepos(): Promise<Repo[]> {
  return request('/api/repos')
}

export function getRepo(repoId: number): Promise<Repo> {
  return request(`/api/repos/${repoId}`)
}

export function startAnalysis(repoId: number): Promise<{ job_id: string; status: AnalysisJobStatus }> {
  return request(`/api/repos/${repoId}/analyze`, { method: 'POST' })
}

export function getAnalysisJob(repoId: number, jobId: string): Promise<AnalysisJob> {
  return request(`/api/repos/${repoId}/analyze/jobs/${jobId}`)
}

export function getDashboard(repoId: number): Promise<DashboardData | null> {
  return requestOptional(`/api/dashboard/${repoId}`)
}

export function getAnalysisHistory(repoId: number): Promise<{ repo_id: number; history: AnalysisHistoryPoint[] }> {
  return request(`/api/dashboard/${repoId}/history`)
}

export function listPullRequests(repoId: number): Promise<PullRequestSummary[]> {
  return request(`/api/repos/${repoId}/pulls`)
}

export function startPrAnalysis(
  repoId: number,
  prNumber: number
): Promise<{ job_id: string; status: AnalysisJobStatus }> {
  return request(`/api/repos/${repoId}/pulls/${prNumber}/analyze`, { method: 'POST' })
}

export function getPrAnalysisJob(repoId: number, prNumber: number, jobId: string): Promise<PrAnalysisJob> {
  return request(`/api/repos/${repoId}/pulls/${prNumber}/analyze/jobs/${jobId}`)
}

export function getPrAnalysis(repoId: number, prNumber: number): Promise<PrAnalysisResult | null> {
  return requestOptional(`/api/repos/${repoId}/pulls/${prNumber}/analysis`)
}

export function getAutoReviewStatus(repoId: number): Promise<{ enabled: boolean }> {
  return request(`/api/repos/${repoId}/auto-review`)
}

export function enableAutoReview(repoId: number): Promise<{ enabled: boolean }> {
  return request(`/api/repos/${repoId}/auto-review`, { method: 'POST' })
}

export function disableAutoReview(repoId: number): Promise<{ enabled: boolean }> {
  return request(`/api/repos/${repoId}/auto-review`, { method: 'DELETE' })
}

export function startFixScan(repoId: number): Promise<{ job_id: string; status: AnalysisJobStatus }> {
  return request(`/api/repos/${repoId}/fixes/scan`, { method: 'POST' })
}

export function getFixScanJob(repoId: number, jobId: string): Promise<FixScanJob> {
  return request(`/api/repos/${repoId}/fixes/scan/jobs/${jobId}`)
}

export function applyFixes(repoId: number, branch: string, fixes: SuggestedFix[]): Promise<CreatedFixPr> {
  return request(`/api/repos/${repoId}/fixes/apply`, {
    method: 'POST',
    body: JSON.stringify({ branch, fixes }),
  })
}

export function startDiagram(repoId: number): Promise<{ job_id: string; status: AnalysisJobStatus }> {
  return request(`/api/repos/${repoId}/diagram`, { method: 'POST' })
}

export function getDiagramJob(repoId: number, jobId: string): Promise<DiagramJob> {
  return request(`/api/repos/${repoId}/diagram/jobs/${jobId}`)
}

export function getShareStatus(repoId: number): Promise<{ enabled: boolean }> {
  return request(`/api/repos/${repoId}/share`)
}

export function enableShare(repoId: number): Promise<{ enabled: boolean }> {
  return request(`/api/repos/${repoId}/share`, { method: 'POST' })
}

export function disableShare(repoId: number): Promise<{ enabled: boolean }> {
  return request(`/api/repos/${repoId}/share`, { method: 'DELETE' })
}

/** Hits a public, unauthenticated endpoint — works whether or not the visitor is logged
 * into gitcat at all, same as the backend route it calls. */
export function getPublicCard(repoId: number): Promise<PublicCard> {
  return request(`/api/public/repos/${repoId}/card`)
}

export function createChatSession(repoId: number, title: string) {
  return request('/api/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ repo_id: repoId, title }),
  }) as Promise<{ session_id: number }>
}

export function sendChatMessage(sessionId: number, message: string) {
  return request('/api/chat/message', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, message }),
  }) as Promise<{ response: string }>
}
