import { ReactNode } from 'react'
import { motion } from 'framer-motion'
import Navbar from './Navbar'
import './Layout.css'

interface LayoutProps {
  children: ReactNode
}

const Layout = ({ children }: LayoutProps) => {
  return (
    <div className="layout">
      <Navbar />
      <motion.main
        className="main-content"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        {children}
      </motion.main>
      <footer className="footer">
        <div className="container footer-content">
          <div className="footer-section">
            <h4 className="text-gradient">DocuMind</h4>
            <p className="footer-text">
              AI-powered document intelligence with precise citations
            </p>
          </div>
          <div className="footer-section">
            <h5>Product</h5>
            <ul className="footer-links">
              <li><a href="/upload">Upload</a></li>
              <li><a href="/search">Search</a></li>
              <li><a href="/documents">Documents</a></li>
            </ul>
          </div>
          <div className="footer-section">
            <h5>Technology</h5>
            <ul className="footer-links">
              <li>FastAPI Backend</li>
              <li>Qdrant Vector DB</li>
              <li>Gemini AI</li>
              <li>React + TypeScript</li>
            </ul>
          </div>
          <div className="footer-section">
            <h5>Stats</h5>
            <ul className="footer-links">
              <li>96%+ Accuracy</li>
              <li>{'<2s'} Query Time</li>
              <li>Hybrid Search</li>
              <li>Page-level Citations</li>
            </ul>
          </div>
        </div>
        <div className="footer-bottom">
          <div className="container">
            <p>© 2026 DocuMind. Built with ❤️ using FastAPI, Qdrant & Gemini AI</p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Layout
