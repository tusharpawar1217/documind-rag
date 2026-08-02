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
    if (error.code === 'ECONNREFUSED' || error.code === 'ERR_NETWORK') {
      return Promise.reject(new Error('Backend server is not running. Please start the backend first.'))
    }
    
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

  const response = await api.post('/api/v1/documents/upload', formData, {
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
  const response = await api.get('/api/v1/documents')
  return response.data
}

// Get document by ID
export const getDocument = async (documentId: string) => {
  const response = await api.get(`/api/v1/documents/${documentId}`)
  return response.data
}

// Delete document
export const deleteDocument = async (documentId: string) => {
  const response = await api.delete(`/api/v1/documents/${documentId}`)
  return response.data
}

// Search documents
export const searchDocuments = async (
  query: string,
  topK: number = 5,
  hybridAlpha: number = 0.5
) => {
  const response = await api.post('/api/v1/search/query', {
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
  temperature: number = 0.7,
  sessionId: string = 'default',
  useChatHistory: boolean = true
) => {
  const response = await api.post('/api/v1/search/query', {
    query,
    top_k: topK,
    hybrid_alpha: hybridAlpha,
    generate_response: true,
    temperature,
    session_id: sessionId,
    use_chat_history: useChatHistory
  })
  return response.data
}

// Get chat history
export const getChatHistory = async (sessionId: string = 'default', limit: number = 20) => {
  const response = await api.get('/api/v1/chat/history', {
    params: { session_id: sessionId, limit }
  })
  return response.data
}

// Clear chat history
export const clearChatHistory = async (sessionId: string = 'default') => {
  const response = await api.delete('/api/v1/chat/history', {
    params: { session_id: sessionId }
  })
  return response.data
}

// Get document statistics
export const getStatistics = async () => {
  const response = await api.get('/api/v1/documents/stats')
  return response.data
}

export default api
