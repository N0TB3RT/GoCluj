import { Navigate, Route, Routes } from 'react-router-dom'
import EventDetailPage from './EventDetailPage.jsx'
import GoClujApp from './GoClujApp.jsx'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<GoClujApp />} />
      <Route path="/evenimente/:id" element={<EventDetailPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
