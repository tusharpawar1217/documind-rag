# DocuMind RAG - Multi-Document Intelligence System

A production-ready RAG (Retrieval-Augmented Generation) system for intelligent document processing and AI-powered question answering.

## 🎯 Features

- **Multi-Format Document Processing**: PDF parsing with text, table, and image extraction
- **Hybrid Search**: Combines semantic search (Gemini embeddings) with keyword search (BM25)
- **AI-Powered Q&A**: Context-aware answers using Gemini 1.5 Pro
- **Vector Database**: Efficient similarity search with Qdrant
- **Modern Frontend**: React + TypeScript with beautiful animations
- **RESTful API**: FastAPI with automatic documentation
- **Docker Ready**: Complete containerized deployment

## 🏗️ Architecture

### Standard RAG Structure

```
backend/
├── config.yaml          # Centralized configuration
├── main.py             # Application entry point
├── requirements.txt    # Python dependencies
│
├── src/                # Standard RAG modules
│   ├── ingestion/      # Document loading (PDF, CSV, etc.)
│   ├── chunking/       # Text chunking strategies
│   ├── embeddings/     # Vector embeddings (Gemini)
│   ├── vectordb/       # Vector database (Qdrant)
│   ├── retrieval/      # Hybrid search
│   ├── prompts/        # Prompt templates
│   ├── llm/            # LLM client (Gemini)
│   ├── api/            # FastAPI routes
│   └── utils/          # Helper functions
│
├── data/               # Document storage
├── logs/               # Application logs
└── tests/              # Test suite

frontend/
├── src/
│   ├── components/     # React components
│   ├── pages/          # Application pages
│   ├── services/       # API integration
│   └── store/          # State management
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Gemini API key

### 1. Clone Repository

```bash
git clone https://github.com/tusharpawar1217/documind-rag.git
cd documind-rag
```

### 2. Configure Environment

```bash
# Create .env file
cp .env.example .env

# Add your Gemini API key
echo "GEMINI_API_KEY=your-key-here" >> .env
```

### 3. Start with Docker

```bash
# Start all services (backend, frontend, Qdrant, Redis)
docker-compose up --build
```

Or manually:

```bash
# Backend
cd backend
pip install -r requirements.txt
python main.py

# Frontend
cd frontend
npm install
npm run dev
```

### 4. Access Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 📚 API Documentation

### Upload Document
```bash
POST /api/v1/documents/upload
Content-Type: multipart/form-data

curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@document.pdf"
```

### Query Documents
```bash
POST /api/v1/search/query
Content-Type: application/json

{
  "query": "What is the main topic?",
  "top_k": 5,
  "hybrid_alpha": 0.5,
  "generate_response": true,
  "temperature": 0.7
}
```

### List Documents
```bash
GET /api/v1/documents
```

### Delete Document
```bash
DELETE /api/v1/documents/{document_id}
```

## 🔧 Configuration

Edit `backend/config.yaml`:

```yaml
# Chunking
chunking:
  chunk_size: 512
  chunk_overlap: 128

# Embeddings
embeddings:
  model: "models/embedding-001"
  dimension: 768

# Retrieval
retrieval:
  top_k: 5
  hybrid_alpha: 0.5

# LLM
llm:
  model: "gemini-1.5-pro-latest"
  temperature: 0.7
  max_tokens: 2048
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# Validate structure
python backend/validate_structure.py
```

## 📊 Tech Stack

### Backend
- **Framework**: FastAPI 0.104+
- **LLM**: Google Gemini 1.5 Pro
- **Embeddings**: Gemini Embedding-001 (768-dim)
- **Vector DB**: Qdrant
- **Cache**: Redis
- **PDF Processing**: PyMuPDF
- **Search**: Hybrid (Semantic + BM25)

### Frontend
- **Framework**: React 18 + TypeScript
- **Build Tool**: Vite
- **Styling**: CSS3 with animations
- **Animations**: Framer Motion
- **HTTP Client**: Axios
- **Routing**: React Router
- **State**: Zustand

## 📁 Project Structure

```
documind-rag/
├── backend/              # Python backend
│   ├── src/             # RAG modules
│   ├── app/             # Legacy code (preserved)
│   ├── data/            # File storage
│   ├── logs/            # Application logs
│   ├── tests/           # Test suite
│   ├── config.yaml      # Configuration
│   ├── main.py          # Entry point
│   └── requirements.txt # Dependencies
│
├── frontend/            # React frontend
│   ├── src/
│   │   ├── components/  # UI components
│   │   ├── pages/       # Pages
│   │   ├── services/    # API client
│   │   └── store/       # State management
│   ├── public/          # Static assets
│   └── package.json     # Dependencies
│
├── docker-compose.yml   # Multi-container setup
├── .env.example         # Environment template
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## 🔐 Security

- Environment-based configuration
- API key authentication ready
- File validation and sanitization
- Rate limiting support
- Encrypted file storage option

## 📈 Performance

- **Chunking**: 500+ chunks/second
- **Embedding**: 32 texts/batch
- **Search**: <100ms average
- **Vector DB**: Qdrant with HNSW indexing
- **Caching**: Redis for frequent queries

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📝 License

MIT License - see LICENSE file

## 👤 Author

**Tushar Pawar**
- GitHub: [@tusharpawar1217](https://github.com/tusharpawar1217)
- Repository: [documind-rag](https://github.com/tusharpawar1217/documind-rag)

## 🙏 Acknowledgments

- Google Gemini AI
- Qdrant Vector Database
- FastAPI Framework
- React Community

## 📞 Support

For issues and questions:
- Open an issue on GitHub
- Check the documentation in `/backend/VALIDATION_REPORT.md`
- Review API documentation at `/docs` endpoint

---

**Built with ❤️ using Python, React, and AI**
