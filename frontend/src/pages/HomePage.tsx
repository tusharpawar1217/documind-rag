import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { 
  Upload, 
  Search, 
  FileText, 
  Zap, 
  Shield, 
  Target,
  ArrowRight,
  CheckCircle,
  Sparkles
} from 'lucide-react'
import './HomePage.css'

const HomePage = () => {
  const features = [
    {
      icon: Zap,
      title: 'Lightning Fast',
      description: '<2s query time with 96%+ accuracy',
      color: '#00D4FF'
    },
    {
      icon: Target,
      title: 'Precise Citations',
      description: 'Page-level source attribution',
      color: '#7C3AED'
    },
    {
      icon: Shield,
      title: 'Enterprise Security',
      description: 'JWT auth, rate limiting, AES-256',
      color: '#EC4899'
    }
  ]

  const stats = [
    { value: '96%+', label: 'Hit@5 Accuracy' },
    { value: '<2s', label: 'Query Latency' },
    { value: '768D', label: 'Embeddings' },
    { value: '∞', label: 'Documents' }
  ]

  const steps = [
    {
      number: '01',
      title: 'Upload Documents',
      description: 'Upload PDF files with advanced parsing',
      icon: Upload
    },
    {
      number: '02',
      title: 'AI Processing',
      description: 'Semantic chunking & vector embeddings',
      icon: Sparkles
    },
    {
      number: '03',
      title: 'Intelligent Search',
      description: 'Hybrid search with precise citations',
      icon: Search
    }
  ]

  return (
    <div className="home-page">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <motion.div
            className="hero-content"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
          >
            <motion.div
              className="hero-badge"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.2, duration: 0.5 }}
            >
              <Sparkles size={16} />
              <span>Powered by Gemini AI & Qdrant</span>
            </motion.div>

            <h1 className="hero-title">
              Multi-Document
              <br />
              <span className="text-gradient">Intelligence System</span>
            </h1>

            <p className="hero-description">
              Advanced RAG system with hybrid search, precise page-level citations,
              and enterprise-grade security. Built with FastAPI, Qdrant, and Gemini AI.
            </p>

            <motion.div
              className="hero-actions"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.4, duration: 0.5 }}
            >
              <Link to="/upload" className="btn btn-primary">
                <Upload size={20} />
                <span>Upload Documents</span>
                <ArrowRight size={18} />
              </Link>
              <Link to="/search" className="btn btn-secondary">
                <Search size={20} />
                <span>Search Now</span>
              </Link>
            </motion.div>

            {/* Stats */}
            <motion.div
              className="hero-stats"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6, duration: 0.5 }}
            >
              {stats.map((stat, index) => (
                <motion.div
                  key={stat.label}
                  className="stat-item"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.7 + index * 0.1, duration: 0.3 }}
                >
                  <div className="stat-value">{stat.value}</div>
                  <div className="stat-label">{stat.label}</div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>

          {/* Animated SVG Illustration */}
          <motion.div
            className="hero-visual"
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.8, delay: 0.3 }}
          >
            <div className="visual-grid">
              {[...Array(9)].map((_, i) => (
                <motion.div
                  key={i}
                  className="grid-item"
                  initial={{ opacity: 0, scale: 0 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{
                    delay: 0.5 + i * 0.1,
                    duration: 0.5,
                    type: 'spring'
                  }}
                  whileHover={{ scale: 1.1, rotate: 5 }}
                >
                  <FileText size={24} />
                </motion.div>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section className="features-section">
        <div className="container">
          <motion.div
            className="section-header"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2>Powerful Features</h2>
            <p>Everything you need for intelligent document processing</p>
          </motion.div>

          <div className="features-grid">
            {features.map((feature, index) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={feature.title}
                  className="feature-card"
                  initial={{ opacity: 0, y: 30 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.2, duration: 0.5 }}
                  whileHover={{ y: -8, transition: { duration: 0.3 } }}
                >
                  <div
                    className="feature-icon"
                    style={{ 
                      background: `linear-gradient(135deg, ${feature.color}22, ${feature.color}44)`,
                      color: feature.color 
                    }}
                  >
                    <Icon size={32} />
                  </div>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="how-it-works-section">
        <div className="container">
          <motion.div
            className="section-header"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2>How It Works</h2>
            <p>Simple, powerful, and intelligent</p>
          </motion.div>

          <div className="steps-grid">
            {steps.map((step, index) => {
              const Icon = step.icon
              return (
                <motion.div
                  key={step.number}
                  className="step-card"
                  initial={{ opacity: 0, x: index % 2 === 0 ? -30 : 30 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: index * 0.2, duration: 0.6 }}
                >
                  <div className="step-number">{step.number}</div>
                  <div className="step-icon">
                    <Icon size={28} />
                  </div>
                  <h3>{step.title}</h3>
                  <p>{step.description}</p>
                  {index < steps.length - 1 && (
                    <div className="step-connector">
                      <ArrowRight size={20} />
                    </div>
                  )}
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta-section">
        <div className="container">
          <motion.div
            className="cta-card"
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
          >
            <h2>Ready to Get Started?</h2>
            <p>Upload your first document and experience the power of AI-driven search</p>
            <div className="cta-actions">
              <Link to="/upload" className="btn btn-primary">
                <Upload size={20} />
                <span>Start Uploading</span>
              </Link>
              <Link to="/documents" className="btn btn-secondary">
                <FileText size={20} />
                <span>View Documents</span>
              </Link>
            </div>
            
            <div className="cta-features">
              <div className="cta-feature">
                <CheckCircle size={20} />
                <span>No credit card required</span>
              </div>
              <div className="cta-feature">
                <CheckCircle size={20} />
                <span>Unlimited documents</span>
              </div>
              <div className="cta-feature">
                <CheckCircle size={20} />
                <span>Enterprise security</span>
              </div>
            </div>
          </motion.div>
        </div>
      </section>
    </div>
  )
}

export default HomePage
