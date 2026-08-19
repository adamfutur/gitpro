import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import AuthCallback from './pages/AuthCallback'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import RepoDetail from './pages/RepoDetail'
import ShareCard from './pages/ShareCard'
import AnalysisTab from './pages/tabs/AnalysisTab'
import ChatTab from './pages/tabs/ChatTab'
import DiagramTab from './pages/tabs/DiagramTab'
import FixesTab from './pages/tabs/FixesTab'
import OverviewTab from './pages/tabs/OverviewTab'
import PrReviewTab from './pages/tabs/PrReviewTab'
import PullsTab from './pages/tabs/PullsTab'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Login />} />
      <Route path="/auth/callback" element={<AuthCallback />} />
      <Route path="/share/:repoId" element={<ShareCard />} />

      <Route element={<AppLayout />}>
        <Route path="/repos" element={<Dashboard />} />
        <Route path="/repos/:repoId" element={<RepoDetail />}>
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OverviewTab />} />
          <Route path="analysis" element={<AnalysisTab />} />
          <Route path="pulls" element={<PullsTab />} />
          <Route path="pulls/:prNumber" element={<PrReviewTab />} />
          <Route path="fixes" element={<FixesTab />} />
          <Route path="diagram" element={<DiagramTab />} />
          <Route path="chat" element={<ChatTab />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
