import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Sparkles,
  FileText,
  Clock,
  TrendingUp,
  Filter,
  Loader,
  ExternalLink,
  ChevronDown,
  ChevronUp
} from 'lucide-react'
import toast from 'react-hot-toast'
import { searchDocuments } from '../services/api'
import './SearchPage.css'

interface SearchResult {
  chunk_id: string
  document_id: string
  document_name: string
  page_number: number
  text: string
  score: number
  metadata?: Record<string, any>
}

const SearchPage = () => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searchTime, setSearchTime] = useState(0)
  const [showFilters, setShowFilters] = useState(false)
  const [topK, setTopK] = useState(5)
  const [hybridAlpha, setHybridAlpha] = useState(0.5)

  const handleSearch = async () => {
    if (!query.trim()) {
      toast.error('Please enter a search query')
      return
    }

    setLoading(true)
    const startTime = Date.now()

    try {
      const data = await searchDocuments(query, topK, hybridAlpha)
      const endTime = Date.now()
      setSearchTime((endTime - startTime) / 1000)
      setResults(data.results || [])
      toast.success(`Found ${data.results?.length || 0} results`)
    } catch (error: any) {
      toast.error(error.message || 'Search failed')
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSearch()
    }
  }

  const getScoreColor = (score: number) => {
    if (score >= 0.8) return 'var(--success)'
    if (score >= 0.6) return 'var(--accent-primary)'
    return 'var(--warning)'
  }

  return (
    <div className="search-page">
      <div className="container">
        {/* Search Header */}
        <motion.div
          className="search-header"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1>Search Documents</h1>
          <p>AI-powered hybrid search with precise citations</p>
        </motion.div>

        {/* Search Box */}
        <motion.div
          className="search-box-container"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className="search-box">
            <div className="search-icon">
              <Search size={24} />
            </div>
            <input
              type="text"
              className="search-input"
              placeholder="Ask anything about your documents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
            />
            <button
              className="search-button"
              onClick={handleSearch}
              disabled={loading}
            >
              {loading ? (
                <Loader className="spin" size={20} />
              ) : (
                <>
                  <Sparkles size={20} />
                  <span>Search</span>
                </>
              )}
            </button>
          </div>

          {/* Filters Toggle */}
          <button
            className="filters-toggle"
            onClick={() => setShowFilters(!showFilters)}
          >
            <Filter size={18} />
            <span>Filters</span>
            {showFilters ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
          </button>

          {/* Filters Panel */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                className="filters-panel"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                <div className="filter-group">
                  <label>
                    <span>Results (Top K)</span>
                    <span className="filter-value">{topK}</span>
                  </label>
                  <input
                    type="range"
                    min="1"
                    max="20"
                    value={topK}
                    onChange={(e) => setTopK(Number(e.target.value))}
                    className="slider"
                  />
                </div>

                <div className="filter-group">
                  <label>
                    <span>Hybrid Alpha</span>
                    <span className="filter-value">{hybridAlpha.toFixed(2)}</span>
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={hybridAlpha}
                    onChange={(e) => setHybridAlpha(Number(e.target.value))}
                    className="slider"
                  />
                  <div className="filter-hint">
                    0 = BM25 only, 1 = Vector only, 0.5 = Balanced
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Search Stats */}
        {results.length > 0 && (
          <motion.div
            className="search-stats"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
          >
            <div className="stat-item">
              <FileText size={18} />
              <span>{results.length} Results</span>
            </div>
            <div className="stat-item">
              <Clock size={18} />
              <span>{searchTime.toFixed(2)}s</span>
            </div>
            <div className="stat-item">
              <TrendingUp size={18} />
              <span>Top Score: {(results[0]?.score * 100 || 0).toFixed(1)}%</span>
            </div>
          </motion.div>
        )}

        {/* Results */}
        <div className="results-container">
          <AnimatePresence>
            {loading && (
              <motion.div
                className="loading-state"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <Loader className="spin" size={48} />
                <p>Searching documents...</p>
              </motion.div>
            )}

            {!loading && results.length === 0 && query && (
              <motion.div
                className="empty-state"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <Search size={64} />
                <h3>No results found</h3>
                <p>Try adjusting your search query or filters</p>
              </motion.div>
            )}

            {!loading && results.length === 0 && !query && (
              <motion.div
                className="empty-state"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
              >
                <Sparkles size={64} />
                <h3>Start Searching</h3>
                <p>Enter a query to search across all your documents</p>
                <div className="example-queries">
                  <h4>Example queries:</h4>
                  <div className="query-tags">
                    <button onClick={() => setQuery('What is machine learning?')}>
                      What is machine learning?
                    </button>
                    <button onClick={() => setQuery('Explain neural networks')}>
                      Explain neural networks
                    </button>
                    <button onClick={() => setQuery('Summary of key findings')}>
                      Summary of key findings
                    </button>
                  </div>
                </div>
              </motion.div>
            )}

            {!loading && results.length > 0 && (
              <div className="results-list">
                {results.map((result, index) => (
                  <motion.div
                    key={result.chunk_id}
                    className="result-card"
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: index * 0.1 }}
                    whileHover={{ y: -4, transition: { duration: 0.2 } }}
                  >
                    <div className="result-header">
                      <div className="result-meta">
                        <FileText size={18} />
                        <span className="document-name">{result.document_name}</span>
                        <span className="page-number">Page {result.page_number}</span>
                      </div>
                      <div
                        className="result-score"
                        style={{ color: getScoreColor(result.score) }}
                      >
                        {(result.score * 100).toFixed(1)}%
                      </div>
                    </div>

                    <div className="result-content">
                      <p>{result.text}</p>
                    </div>

                    <div className="result-footer">
                      <div className="result-rank">#{index + 1}</div>
                      <button className="result-action">
                        <span>View Context</span>
                        <ExternalLink size={16} />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  )
}

export default SearchPage
