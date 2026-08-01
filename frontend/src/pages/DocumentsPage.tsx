import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Trash2,
  Loader,
  Calendar,
  HardDrive,
  Search,
  RefreshCw,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getDocuments, deleteDocument, getStatistics } from '../services/api'
import './DocumentsPage.css'

interface Document {
  document_id: string
  filename: string
  file_size: number
  upload_date: string
  num_chunks: number
  status: string
}

interface Statistics {
  total_documents: number
  total_chunks: number
  total_size: number
}

const DocumentsPage = () => {
  const [documents, setDocuments] = useState<Document[]>([])
  const [statistics, setStatistics] = useState<Statistics | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const loadDocuments = async () => {
    try {
      const data = await getDocuments()
      setDocuments(data.documents || [])
    } catch (error: any) {
      toast.error(error.message || 'Failed to load documents')
    }
  }

  const loadStatistics = async () => {
    try {
      const data = await getStatistics()
      setStatistics(data)
    } catch (error: any) {
      console.error('Failed to load statistics:', error)
    }
  }

  const loadData = async () => {
    setIsLoading(true)
    await Promise.all([loadDocuments(), loadStatistics()])
    setIsLoading(false)
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleDelete = async (documentId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return
    }

    setDeletingId(documentId)

    try {
      await deleteDocument(documentId)
      toast.success('Document deleted successfully')
      await loadData()
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete document')
    } finally {
      setDeletingId(null)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i]
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="documents-page">
      <div className="container">
        <motion.div
          className="documents-header"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div>
            <h1>Documents</h1>
            <p>Manage your uploaded documents</p>
          </div>
          <button className="btn btn-secondary" onClick={loadData}>
            <RefreshCw size={18} />
            Refresh
          </button>
        </motion.div>

        {/* Statistics */}
        {statistics && (
          <motion.div
            className="statistics-grid"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.4, delay: 0.1 }}
          >
            <div className="stat-card">
              <div className="stat-icon">
                <FileText size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-value">{statistics.total_documents}</div>
                <div className="stat-label">Total Documents</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <HardDrive size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-value">
                  {formatFileSize(statistics.total_size)}
                </div>
                <div className="stat-label">Total Size</div>
              </div>
            </div>

            <div className="stat-card">
              <div className="stat-icon">
                <FileText size={24} />
              </div>
              <div className="stat-content">
                <div className="stat-value">{statistics.total_chunks}</div>
                <div className="stat-label">Total Chunks</div>
              </div>
            </div>
          </motion.div>
        )}

        {/* Search */}
        <motion.div
          className="search-bar"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.2 }}
        >
          <Search className="search-icon" size={20} />
          <input
            type="text"
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
        </motion.div>

        {/* Documents List */}
        {isLoading ? (
          <div className="loading-state">
            <Loader className="spin" size={48} />
            <p>Loading documents...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5 }}
          >
            <FileText size={64} strokeWidth={1} />
            <h3>
              {searchQuery ? 'No documents found' : 'No documents yet'}
            </h3>
            <p>
              {searchQuery
                ? 'Try a different search term'
                : 'Upload your first document to get started'}
            </p>
          </motion.div>
        ) : (
          <motion.div
            className="documents-grid"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <AnimatePresence>
              {filteredDocuments.map((doc, index) => (
                <motion.div
                  key={doc.document_id}
                  className="document-card"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.3, delay: index * 0.05 }}
                  layout
                >
                  <div className="document-icon">
                    <FileText size={32} />
                  </div>

                  <div className="document-info">
                    <h3 className="document-name">{doc.filename}</h3>

                    <div className="document-meta">
                      <div className="meta-item">
                        <HardDrive size={14} />
                        <span>{formatFileSize(doc.file_size)}</span>
                      </div>
                      <div className="meta-item">
                        <Calendar size={14} />
                        <span>{formatDate(doc.upload_date)}</span>
                      </div>
                      <div className="meta-item">
                        <FileText size={14} />
                        <span>{doc.num_chunks} chunks</span>
                      </div>
                    </div>

                    <div className="document-status">
                      <span className={`status-badge ${doc.status}`}>
                        {doc.status}
                      </span>
                    </div>
                  </div>

                  <button
                    className="btn-delete"
                    onClick={() => handleDelete(doc.document_id, doc.filename)}
                    disabled={deletingId === doc.document_id}
                  >
                    {deletingId === doc.document_id ? (
                      <Loader className="spin" size={18} />
                    ) : (
                      <Trash2 size={18} />
                    )}
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default DocumentsPage
