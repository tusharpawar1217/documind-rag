import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useDropzone } from 'react-dropzone'
import {
  Upload,
  File,
  X,
  CheckCircle,
  AlertCircle,
  Loader,
  FileText,
  Download
} from 'lucide-react'
import toast from 'react-hot-toast'
import { uploadDocument } from '../services/api'
import './UploadPage.css'

interface UploadFile {
  file: File
  id: string
  status: 'pending' | 'uploading' | 'success' | 'error'
  progress: number
  error?: string
}

const UploadPage = () => {
  const [files, setFiles] = useState<UploadFile[]>([])

  const onDrop = (acceptedFiles: File[]) => {
    const newFiles: UploadFile[] = acceptedFiles.map((file) => ({
      file,
      id: Math.random().toString(36).substr(2, 9),
      status: 'pending',
      progress: 0,
    }))
    setFiles((prev) => [...prev, ...newFiles])
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  })

  const handleUpload = async (uploadFile: UploadFile) => {
    setFiles((prev) =>
      prev.map((f) =>
        f.id === uploadFile.id
          ? { ...f, status: 'uploading', progress: 0 }
          : f
      )
    )

    try {
      await uploadDocument(uploadFile.file, (progress) => {
        setFiles((prev) =>
          prev.map((f) =>
            f.id === uploadFile.id ? { ...f, progress } : f
          )
        )
      })

      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: 'success', progress: 100 }
            : f
        )
      )
      toast.success(`${uploadFile.file.name} uploaded successfully!`)
    } catch (error: any) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === uploadFile.id
            ? { ...f, status: 'error', error: error.message }
            : f
        )
      )
      toast.error(`Failed to upload ${uploadFile.file.name}`)
    }
  }

  const handleUploadAll = () => {
    files
      .filter((f) => f.status === 'pending')
      .forEach((f) => handleUpload(f))
  }

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id))
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const pendingCount = files.filter((f) => f.status === 'pending').length
  const uploadingCount = files.filter((f) => f.status === 'uploading').length
  const successCount = files.filter((f) => f.status === 'success').length

  return (
    <div className="upload-page">
      <div className="container">
        <motion.div
          className="upload-header"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1>Upload Documents</h1>
          <p>Upload PDF files to process with AI-powered intelligence</p>
        </motion.div>

        {/* Upload Stats */}
        {files.length > 0 && (
          <motion.div
            className="upload-stats"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <div className="stat-item">
              <FileText size={20} />
              <span>{files.length} Total</span>
            </div>
            <div className="stat-item">
              <Loader size={20} />
              <span>{uploadingCount} Uploading</span>
            </div>
            <div className="stat-item">
              <CheckCircle size={20} />
              <span>{successCount} Success</span>
            </div>
          </motion.div>
        )}

        {/* Dropzone */}
        <motion.div
          className="dropzone-container"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div
            {...getRootProps()}
            className={`dropzone ${isDragActive ? 'active' : ''}`}
          >
            <input {...getInputProps()} />
            <motion.div
              className="dropzone-content"
              animate={isDragActive ? { scale: 1.05 } : { scale: 1 }}
              transition={{ duration: 0.3 }}
            >
              <motion.div
                className="dropzone-icon"
                animate={
                  isDragActive
                    ? { y: [-5, 5, -5], transition: { repeat: Infinity, duration: 1 } }
                    : { y: 0 }
                }
              >
                <Upload size={48} />
              </motion.div>
              <h3>
                {isDragActive
                  ? 'Drop files here'
                  : 'Drag & drop PDF files here'}
              </h3>
              <p>or click to browse</p>
              <div className="dropzone-info">
                <span>• Max file size: 50MB</span>
                <span>• Supported: PDF only</span>
              </div>
            </motion.div>
          </div>
        </motion.div>

        {/* Files List */}
        {files.length > 0 && (
          <motion.div
            className="files-section"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <div className="files-header">
              <h2>Files ({files.length})</h2>
              {pendingCount > 0 && (
                <button className="btn btn-primary" onClick={handleUploadAll}>
                  <Upload size={18} />
                  Upload All ({pendingCount})
                </button>
              )}
            </div>

            <div className="files-list">
              <AnimatePresence>
                {files.map((uploadFile) => (
                  <motion.div
                    key={uploadFile.id}
                    className={`file-item ${uploadFile.status}`}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 20 }}
                    transition={{ duration: 0.3 }}
                  >
                    <div className="file-icon">
                      <File size={24} />
                    </div>

                    <div className="file-info">
                      <div className="file-name">{uploadFile.file.name}</div>
                      <div className="file-meta">
                        <span>{formatFileSize(uploadFile.file.size)}</span>
                        {uploadFile.status === 'error' && (
                          <span className="error-text">
                            • {uploadFile.error || 'Upload failed'}
                          </span>
                        )}
                      </div>

                      {uploadFile.status === 'uploading' && (
                        <div className="progress-bar">
                          <motion.div
                            className="progress-fill"
                            initial={{ width: 0 }}
                            animate={{ width: `${uploadFile.progress}%` }}
                            transition={{ duration: 0.3 }}
                          />
                        </div>
                      )}
                    </div>

                    <div className="file-status">
                      {uploadFile.status === 'pending' && (
                        <button
                          className="btn-icon"
                          onClick={() => handleUpload(uploadFile)}
                        >
                          <Upload size={18} />
                        </button>
                      )}
                      {uploadFile.status === 'uploading' && (
                        <Loader className="spin" size={20} />
                      )}
                      {uploadFile.status === 'success' && (
                        <CheckCircle size={20} className="success-icon" />
                      )}
                      {uploadFile.status === 'error' && (
                        <AlertCircle size={20} className="error-icon" />
                      )}
                    </div>

                    <button
                      className="btn-icon remove-btn"
                      onClick={() => removeFile(uploadFile.id)}
                    >
                      <X size={18} />
                    </button>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          </motion.div>
        )}

        {/* Features */}
        <motion.div
          className="upload-features"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className="feature-item">
            <CheckCircle size={20} />
            <div>
              <h4>Automatic Processing</h4>
              <p>AI-powered text extraction and chunking</p>
            </div>
          </div>
          <div className="feature-item">
            <CheckCircle size={20} />
            <div>
              <h4>Vector Embeddings</h4>
              <p>768-dimensional semantic embeddings</p>
            </div>
          </div>
          <div className="feature-item">
            <CheckCircle size={20} />
            <div>
              <h4>Instant Search</h4>
              <p>Query your documents immediately</p>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default UploadPage
