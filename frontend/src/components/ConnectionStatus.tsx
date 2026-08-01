import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Wifi, WifiOff, AlertCircle } from 'lucide-react'
import { checkHealth } from '../services/api'
import './ConnectionStatus.css'

const ConnectionStatus = () => {
  const [isConnected, setIsConnected] = useState<boolean | null>(null)
  const [isChecking, setIsChecking] = useState(true)

  const checkConnection = async () => {
    try {
      await checkHealth()
      setIsConnected(true)
      setIsChecking(false)
    } catch (error) {
      setIsConnected(false)
      setIsChecking(false)
    }
  }

  useEffect(() => {
    checkConnection()
    
    // Check connection every 10 seconds
    const interval = setInterval(checkConnection, 10000)
    
    return () => clearInterval(interval)
  }, [])

  if (isChecking) {
    return (
      <motion.div
        className="connection-status checking"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Wifi size={16} className="spin" />
        <span>Connecting to backend...</span>
      </motion.div>
    )
  }

  if (isConnected === false) {
    return (
      <motion.div
        className="connection-status offline"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <WifiOff size={16} />
        <span>Backend server offline</span>
        <button 
          className="btn-retry" 
          onClick={checkConnection}
        >
          Retry
        </button>
      </motion.div>
    )
  }

  return null // Don't show anything if connected
}

export default ConnectionStatus
