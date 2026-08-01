import { create } from 'zustand'

interface Document {
  document_id: string
  filename: string
  upload_date: string
  file_size: number
  total_pages: number
  chunk_count: number
  metadata?: Record<string, any>
}

interface SearchResult {
  chunk_id: string
  document_id: string
  document_name: string
  page_number: number
  text: string
  score: number
  metadata?: Record<string, any>
}

interface AppState {
  // Documents
  documents: Document[]
  setDocuments: (documents: Document[]) => void
  addDocument: (document: Document) => void
  removeDocument: (documentId: string) => void

  // Search
  searchResults: SearchResult[]
  setSearchResults: (results: SearchResult[]) => void
  searchQuery: string
  setSearchQuery: (query: string) => void

  // UI State
  isLoading: boolean
  setIsLoading: (loading: boolean) => void
  error: string | null
  setError: (error: string | null) => void
}

export const useStore = create<AppState>((set) => ({
  // Documents
  documents: [],
  setDocuments: (documents) => set({ documents }),
  addDocument: (document) =>
    set((state) => ({ documents: [...state.documents, document] })),
  removeDocument: (documentId) =>
    set((state) => ({
      documents: state.documents.filter((doc) => doc.document_id !== documentId),
    })),

  // Search
  searchResults: [],
  setSearchResults: (results) => set({ searchResults: results }),
  searchQuery: '',
  setSearchQuery: (query) => set({ searchQuery: query }),

  // UI State
  isLoading: false,
  setIsLoading: (loading) => set({ isLoading: loading }),
  error: null,
  setError: (error) => set({ error }),
}))

export default useStore
