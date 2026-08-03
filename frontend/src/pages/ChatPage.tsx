import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Trash2, MessageSquare, Loader, Bot, User } from 'lucide-react'
import toast from 'react-hot-toast'
import { queryDocuments, getChatHistory, clearChatHistory } from '../services/api'
import './ChatPage.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
}

const ChatPage = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [sessionId] = useState('default')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadChatHistory()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const loadChatHistory = async () => {
    try {
      const data = await getChatHistory(sessionId, 50)
      if (data.messages && data.messages.length > 0) {
        setMessages(data.messages)
      }
    } catch (error: any) {
      console.error('Failed to load history:', error)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isLoading) return

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsLoading(true)

    try {
      const response = await queryDocuments(
        input,
        5,
        0.5,
        0.7,
        sessionId,
        true
      )

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.response || 'No response generated',
        timestamp: new Date().toISOString()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error: any) {
      toast.error(error.message || 'Failed to get response')
      
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date().toISOString()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleClearHistory = async () => {
    if (!confirm('Clear all chat history?')) return

    try {
      await clearChatHistory(sessionId)
      setMessages([])
      toast.success('Chat history cleared')
    } catch (error: any) {
      toast.error('Failed to clear history')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="chat-page">
      <div className="chat-container">
        {/* Header */}
        <motion.div
          className="chat-header"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="header-content">
            <MessageSquare size={32} />
            <div>
              <h1>Chat with Documents</h1>
              <p>Ask questions and get AI-powered answers</p>
            </div>
          </div>
          <button
            className="btn btn-secondary"
            onClick={handleClearHistory}
            disabled={messages.length === 0}
          >
            <Trash2 size={18} />
            Clear History
          </button>
        </motion.div>

        {/* Messages */}
        <div className="messages-container">
          {messages.length === 0 ? (
            <motion.div
              className="empty-chat"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <Bot size={64} strokeWidth={1} />
              <h3>Start a Conversation</h3>
              <p>Ask me anything about your uploaded documents</p>
            </motion.div>
          ) : (
            <AnimatePresence>
              {messages.map((message, index) => (
                <motion.div
                  key={index}
                  className={`message ${message.role}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="message-icon">
                    {message.role === 'user' ? (
                      <User size={20} />
                    ) : (
                      <Bot size={20} />
                    )}
                  </div>
                  <div className="message-content">
                    <div className="message-text">
                      {message.content.split('\n').map((line, idx) => {
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
                            <div key={idx} className="message-bullet">
                              {parts.length > 0 ? parts : line}
                            </div>
                          );
                        }
                        
                        // Handle numbered lists
                        if (/^\d+\./.test(line.trim())) {
                          return (
                            <div key={idx} className="message-numbered">
                              {parts.length > 0 ? parts : line}
                            </div>
                          );
                        }
                        
                        // Handle separators
                        if (line.trim().startsWith('─') || line.trim() === '---') {
                          return <hr key={idx} className="message-separator" />;
                        }
                        
                        // Handle section headers
                        if (line.includes('📚') || line.includes('📄') || line.includes('💡')) {
                          return (
                            <div key={idx} className="message-meta">
                              {parts.length > 0 ? parts : line}
                            </div>
                          );
                        }
                        
                        // Regular text
                        if (line.trim()) {
                          return (
                            <div key={idx} className="message-line">
                              {parts.length > 0 ? parts : line}
                            </div>
                          );
                        }
                        
                        return <br key={idx} />;
                      })}
                    </div>
                    <div className="message-time">
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          
          {isLoading && (
            <motion.div
              className="message assistant"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <div className="message-icon">
                <Bot size={20} />
              </div>
              <div className="message-content">
                <div className="typing-indicator">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <motion.div
          className="chat-input-container"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="input-wrapper">
            <textarea
              className="chat-input"
              placeholder="Ask a question about your documents..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={isLoading}
              rows={1}
            />
            <button
              className="send-button"
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
            >
              {isLoading ? (
                <Loader className="spin" size={20} />
              ) : (
                <Send size={20} />
              )}
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  )
}

export default ChatPage
