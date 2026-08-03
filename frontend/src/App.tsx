import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import Layout from './components/Layout/Layout'
import ConnectionStatus from './components/ConnectionStatus'
import HomePage from './pages/HomePage'
import UploadPage from './pages/UploadPage'
import SearchPage from './pages/SearchPage'
import DocumentsPage from './pages/DocumentsPage'
import ChatPage from './pages/ChatPage'

function App() {
  return (
    <Router>
      <div className="grid-background" />
      <ConnectionStatus />
      <Layout>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/search" element={<SearchPage />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
        </Routes>
      </Layout>
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          style: {
            background: '#1A2140',
            color: '#FFFFFF',
            border: '1px solid #2D3B5E',
            boxShadow: '0 4px 16px rgba(0, 0, 0, 0.4)',
          },
          success: {
            iconTheme: {
              primary: '#10B981',
              secondary: '#FFFFFF',
            },
          },
          error: {
            iconTheme: {
              primary: '#EF4444',
              secondary: '#FFFFFF',
            },
          },
        }}
      />
    </Router>
  )
}

export default App
