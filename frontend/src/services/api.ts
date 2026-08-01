import axios, { AxiosProgressEvent } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
})

// Request interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.response?.data?.message ||
      error.message ||
      'An error occurred'
    return Promise.reject(new Error(message))
  }
)

// Health check
export const checkHealth = async () => {
  const response = await api.get('/api/health')
  return response.data
}

// Upload document
export const uploadDocument = async (
  file: File,
  onProgress?: (progress: number) => void
) => {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post('/api/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 300000, // 5 minutes for large uploads
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (onProgress && progressEvent.total) {
        const progress = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        )
        onProgress(progress)
      }
    },
  })

  return response.data
}

// Get all documents
export const getDocuments = async () => {
  const response = await api.get('/api/documents')
  return response.data
}

// Get document by ID
export const getDocument = async (documentId: string) => {
  const response = await api.get(`/api/documents/${documentId}`)
  return response.data
}

// Delete document
export const deleteDocument = async (documentId: string) => {
  const response = await api.delete(`/api/documents/${documentId}`)
  return response.data
}

// Search documents
export const searchDocuments = async (
  query: string,
  topK: number = 5,
  hybridAlpha: number = 0.5
) => {
  const response = await api.post('/api/search', {
    query,
    top_k: topK,
    hybrid_alpha: hybridAlpha,
  })
  return response.data
}

// Query with response generation
export const queryDocuments = async (
  query: string,
  topK: number = 5,
  hybridAlpha: number = 0.5,
  temperature: number = 0.7
) => {
  const response = await api.post('/api/query', {
    query,
    top_k: topK,
    hybrid_alpha: hybridAlpha,
    temperature,
  })
  return response.data
}

// Get document statistics
export const getStatistics = async () => {
  const response = await api.get('/api/statistics')
  return response.data
}

export default api
