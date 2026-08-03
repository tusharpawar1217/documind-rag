import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Search,
  Loader,
  FileText,
  Sparkles,
  Settings,
  ChevronDown,
  ChevronUp,
} from 'lucide-react'
import toast from 'react-hot-toast'
import { queryDocuments } from '../services/api'
import './SearchPage.css'

interface SearchResult {
  chunk_id: string
  document_id: string
  document_name: string
  text: string
  score: number
  page_number?: number
}

interface QueryResponse {
  query: string
  results: SearchResult[]
  response?: string
  total_results: number
}

const SearchPage = () => {
  const [query, setQuery] = useState('')
  const [isSearching, setIsSearching] = useState(false)
  const [results, setResults] = useState<QueryResponse | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  
  // Search settings
  const [topK, setTopK] = useState(5)
  const [hybridAlpha, setHybridAlpha] = useState(0.5)
  const [temperature, setTemperature] = useState(0.7)

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!query.trim()) {
      toast.error('Please enter a search query')
      return
    }

    setIsSearching(true)
    
    try {
      const data = await queryDocuments(query, topK, hybridAlpha, temperature)
      setResults(data)
      
      if (data.results.length === 0) {
        toast('No results found', { icon: '🔍' })
      }
    } catch (error: any) {
      toast.error(error.message || 'Search failed')
      setResults(null)
    } finally {
      setIsSearching(false)
    }
  }

  return (
    <div className="search-page">
      <div className="container">
        <motion.div
          className="search-header"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <h1>Search Documents</h1>
          <p>Ask questions and get AI-powered answers from your documents</p>
        </motion.div>

        {/* Search Form */}
        <motion.form
          className="search-form"
          onSubmit={handleSearch}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          <div className="search-input-wrapper">
            <Search className="search-icon" size={20} />
            <input
              type="text"
              placeholder="Ask a question about your documents..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="search-input"
              disabled={isSearching}
            />
            {isSearching && <Loader className="spin loading-icon" size={20} />}
          </div>

          <div className="search-actions">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setShowSettings(!showSettings)}
            >
              <Settings size={18} />
              Settings
              {showSettings ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={isSearching || !query.trim()}
            >
              {isSearching ? (
                <>
                  <Loader className="spin" size={18} />
                  Searching...
                </>
              ) : (
                <>
                  <Sparkles size={18} />
                  Search
                </>
              )}
            </button>
          </div>
        </motion.form>

        {/* Settings Panel */}
        <AnimatePresence>
          {showSettings && (
            <motion.div
              className="settings-panel"
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="setting-item">
                <label>
                  <span>Results Count</span>
                  <span className="setting-value">{topK}</span>
                </label>
                <input
                  type="range"
                  min="1"
                  max="10"
                  value={topK}
                  onChange={(e) => setTopK(Number(e.target.value))}
                  className="slider"
                />
                <div className="slider-labels">
                  <span>1</span>
                  <span>10</span>
                </div>
              </div>

              <div className="setting-item">
                <label>
                  <span>Hybrid Search Weight</span>
                  <span className="setting-value">{hybridAlpha.toFixed(2)}</span>
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
                <div className="slider-labels">
                  <span>Keyword</span>
                  <span>Semantic</span>
                </div>
              </div>

              <div className="setting-item">
                <label>
                  <span>Response Creativity</span>
                  <span className="setting-value">{temperature.toFixed(1)}</span>
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={temperature}
                  onChange={(e) => setTemperature(Number(e.target.value))}
                  className="slider"
                />
                <div className="slider-labels">
                  <span>Precise</span>
                  <span>Creative</span>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Results */}
        <AnimatePresence mode="wait">
          {results && (
            <motion.div
              className="results-section"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.5 }}
            >
              {/* AI Response */}
              {results.response && (
                <motion.div
                  className="ai-response"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.4, delay: 0.1 }}
                >
                  <div className="response-header">
                    <Sparkles size={20} />
                    <h3>AI Response</h3>
                  </div>
                  <div className="response-content">
                    {results.response.split('\n').map((line, idx) => {
                      // Handle bold text
                      const boldRegex = /\*\*(.*?)\*\*/g;
                      const parts = [];
                      let lastIndex = 0;
                      let match;
                      
                      while ((match = boldRegex.exec(line)) !== null) {
                        if (match.index > lastIndex) {
                          parts.push(line.substring(lastIndex, match.index));
                        }
                        parts.push(<strong key={`bold-${idx}-${match.index}`}>{match[1]}</strong>);
                        lastIndex = match.index + match[0].length;
                      }
                      
                      if (lastIndex < line.length) {
                        parts.push(line.substring(lastIndex));
                      }
                      
                      // Handle bullet points
                      if (line.trim().startsWith('•') || line.trim().startsWith('-')) {
                        return (
                          <div key={idx} className="response-bullet">
                            {parts.length > 0 ? parts : line}
                          </div>
                        );
                      }
                      
                      // Handle numbered lists
                      if (/^\d+\./.test(line.trim())) {
                        return (
                          <div key={idx} className="response-numbered">
                            {parts.length > 0 ? parts : line}
                          </div>
                        );
                      }
                      
                      // Handle separators
                      if (line.trim().startsWith('─') || line.trim() === '---') {
                        return <hr key={idx} className="response-separator" />;
                      }
                      
                      // Handle section headers (lines with emoji or special formatting)
                      if (line.includes('📚') || line.includes('📄') || line.includes('💡')) {
                        return (
                          <div key={idx} className="response-meta">
                            {parts.length > 0 ? parts : line}
                          </div>
                        );
                      }
                      
                      // Regular paragraph
                      if (line.trim()) {
                        return (
                          <p key={idx} className="response-paragraph">
                            {parts.length > 0 ? parts : line}
                          </p>
                        );
                      }
                      
                      // Empty line
                      return <br key={idx} />;
                    })}
                  </div>
                </motion.div>
              )}

              {/* Source Documents */}
              {results.results.length > 0 && (
                <div className="sources-section">
                  <div className="sources-header">
                    <FileText size={20} />
                    <h3>Source Documents ({results.results.length})</h3>
                  </div>

                  <div className="sources-list">
                    {results.results.map((result, index) => (
                      <motion.div
                        key={result.chunk_id}
                        className="source-item"
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.3, delay: index * 0.1 }}
                      >
                        <div className="source-header">
                          <div className="source-meta">
                            <span className="source-rank">#{index + 1}</span>
                            <span className="source-name">{result.document_name}</span>
                            {result.page_number && (
                              <span className="source-page">Page {result.page_number}</span>
                            )}
                          </div>
                          <div className="source-score">
                            <span className="score-label">Relevance</span>
                            <span className="score-value">
                              {(result.score * 100).toFixed(0)}%
                            </span>
                          </div>
                        </div>
                        <div className="source-text">{result.text}</div>
                      </motion.div>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty State */}
        {!results && !isSearching && (
          <motion.div
            className="empty-state"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            <Search size={64} strokeWidth={1} />
            <h3>Start Searching</h3>
            <p>Enter a question to search through your uploaded documents</p>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default SearchPage
