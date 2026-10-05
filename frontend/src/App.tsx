import { Routes, Route } from 'react-router-dom'
import Layout from './components/layout/Layout'
import DashboardPage from './pages/DashboardPage'
import DataUploadPage from './pages/DataUploadPage'
import InvestigationsPage from './pages/InvestigationsPage'
import InvestigationDetailPage from './pages/InvestigationDetailPage'
import MechanismDetailPage from './pages/MechanismDetailPage'
import TimelinePage from './pages/TimelinePage'
import GraphPage from './pages/GraphPage'
import EvaluationPage from './pages/EvaluationPage'
import SettingsPage from './pages/SettingsPage'
import EvidenceExplorerPage from './pages/EvidenceExplorerPage'

export default function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/upload" element={<DataUploadPage />} />
        <Route path="/investigations" element={<InvestigationsPage />} />
        <Route path="/investigations/:id" element={<InvestigationDetailPage />} />
        <Route path="/investigations/:id/timeline" element={<TimelinePage />} />
        <Route path="/investigations/:id/graph" element={<GraphPage />} />
        <Route path="/mechanisms/:id" element={<MechanismDetailPage />} />
        <Route path="/mechanisms/:id/evidence" element={<EvidenceExplorerPage />} />
        <Route path="/evaluation" element={<EvaluationPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}
