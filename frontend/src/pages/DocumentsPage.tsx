import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  FileText,
  Trash2,
  Download,
  Calendar,
  HardDrive,
  Search,
  Grid,
  List,
  Loader,
  AlertCircle
} from 'lucide-react'
import toast from 'react-hot-toast'
import { getDocuments, deleteDocument } from '../services/api'
import './DocumentsPage.css'

interface Document {
  document_id: string
  filename: string
  upload_date: string
  file_size: number
  total_pages: number
  chunk_count: number
  metadata?: Record<string, any>
}

const DocumentsPage = () => {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [searchQuery, setSearchQuery] = useState('')
  const [deleteLoading, setDeleteLoading] = useState<string | null>(null)

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      const data = await getDocuments()
      setDocuments(data.documents || [])
    } catch (error: any) {
      toast.error(error.message || 'Failed to fetch documents')
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Are you sure you want to delete "${filename}"?`)) {
      return
    }

    setDeleteLoading(docId)
    try {
      await deleteDocument(docId)
      setDocuments(documents.filter((doc) => doc.document_id !== docId))
      toast.success('Document deleted successfully')
    } catch (error: any) {
      toast.error(error.message || 'Failed to delete document')
    } finally {
      setDeleteLoading(null)
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
    })
  }

  const filteredDocuments = documents.filter((doc) =>
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const totalSize = documents.reduce((sum, doc) => sum + doc.file_size, 0)
  const totalPages = documents.reduce((sum, doc) => sum + doc.total_pages, 0)
  const totalChunks = documents.reduce((sum, doc) => sum + doc.chunk_count, 0)

  return (
    <div className="documents-page">
      <div className="container">
        {/* Header */}
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
        </motion.div>

        {/* Stats */}
        <motion.div
          className="documents-stats"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className="stat-card">
            <FileText size={24} />
            <div className="stat-content">
              <div className="stat-value">{documents.length}</div>
              <div className="stat-label">Documents</div>
            </div>
          </div>
          <div className="stat-card">
            <HardDrive size={24} />
            <div className="stat-content">
              <div className="stat-value">{formatFileSize(totalSize)}</div>
              <div className="stat-label">Total Size</div>
            </div>
          </div>
          <div className="stat-card">
            <FileText size={24} />
            <div className="stat-content">
              <div className="stat-value">{totalPages}</div>
              <div className="stat-label">Total Pages</div>
            </div>
          </div>
          <div className="stat-card">
            <Grid size={24} />
            <div className="stat-content">
              <div className="stat-value">{totalChunks}</div>
              <div className="stat-label">Chunks</div>
            </div>
          </div>
        </motion.div>

        {/* Controls */}
        <motion.div
          className="documents-controls"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="search-box">
            <Search size={18} />
            <input
              type="text"
              placeholder="Search documents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="view-toggle">
            <button
              className={viewMode === 'grid' ? 'active' : ''}
              onClick={() => setViewMode('grid')}
            >
              <Grid size={18} />
            </button>
            <button
              className={viewMode === 'list' ? 'active' : ''}
              onClick={() => setViewMode('list')}
            >
              <List size={18} />
            </button>
          </div>
        </motion.div>

        {/* Documents */}
        <div className="documents-container">
          {loading ? (
            <motion.div
              className="loading-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <Loader className="spin" size={48} />
              <p>Loading documents...</p>
            </motion.div>
          ) : filteredDocuments.length === 0 ? (
            <motion.div
              className="empty-state"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <FileText size={64} />
              <h3>
                {searchQuery ? 'No documents found' : 'No documents yet'}
              </h3>
              <p>
                {searchQuery
                  ? 'Try adjusting your search query'
                  : 'Upload your first document to get started'}
              </p>
            </motion.div>
          ) : (
            <motion.div
              className={`documents-${viewMode}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.5 }}
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
                    whileHover={{ y: -4 }}
                  >
                    <div className="document-icon">
                      <FileText size={viewMode === 'grid' ? 32 : 24} />
                    </div>

                    <div className="document-info">
                      <h3 className="document-name">{doc.filename}</h3>

                      <div className="document-meta">
                        <div className="meta-item">
                          <Calendar size={14} />
                          <span>{formatDate(doc.upload_date)}</span>
                        </div>
                        <div className="meta-item">
                          <HardDrive size={14} />
                          <span>{formatFileSize(doc.file_size)}</span>
                        </div>
                        <div className="meta-item">
                          <FileText size={14} />
                          <span>{doc.total_pages} pages</span>
                        </div>
                      </div>

                      <div className="document-stats">
                        <span className="stat-badge">
                          {doc.chunk_count} chunks
                        </span>
                      </div>
                    </div>

                    <div className="document-actions">
                      <button
                        className="btn-icon"
                        onClick={() =>
                          handleDelete(doc.document_id, doc.filename)
                        }
                        disabled={deleteLoading === doc.document_id}
                      >
                        {deleteLoading === doc.document_id ? (
                          <Loader className="spin" size={18} />
                        ) : (
                          <Trash2 size={18} />
                        )}
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </motion.div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DocumentsPage
