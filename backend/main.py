"""
DocuMind RAG - Main Entry Point

This is the entry point for the DocuMind RAG system.
It initializes the FastAPI application and starts the server.
"""

import uvicorn
from src.api.routes import app
from src.utils.helpers import load_config, setup_logging

# Load configuration
config = load_config()

# Setup logging
setup_logging(config['app']['log_level'])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config['app']['host'],
        port=config['app']['port'],
        reload=config['app']['environment'] == 'development',
        log_level=config['app']['log_level'].lower()
    )
