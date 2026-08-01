# Running DocuMind RAG Locally

## 🚀 Quick Start (Recommended)

The easiest way to run the application is using Docker:

### Prerequisites
- Docker Desktop installed and running
- Git

### Steps

1. **Start the application**:
   ```powershell
   .\start.ps1
   ```

   That's it! The script will:
   - Check Docker is running
   - Build all services (first time only, ~5-10 minutes)
   - Start backend API, Qdrant, and Redis
   - Open API documentation in your browser

2. **Access the application**:
   - API Docs: http://localhost:8000/docs
   - Backend API: http://localhost:8000
   - Health Check: http://localhost:8000/api/health
   - Qdrant Dashboard: http://localhost:6333/dashboard

3. **Stop the application**:
   ```powershell
   docker-compose down
   ```

---

## 📋 Manual Docker Setup

If you prefer manual control:

```powershell
# Build and start all services
docker-compose up --build -d

# View logs
docker-compose logs -f

# View backend logs only
docker-compose logs -f backend

# Stop all services
docker-compose down

# Restart a service
docker-compose restart backend
```

---

## 🐍 Native Python Setup (Advanced)

If you want to run without Docker:

### Prerequisites
- **Python 3.11 or 3.12** (3.14 has compatibility issues)
- Docker Desktop (for Qdrant and Redis)
- Tesseract OCR
- Poppler (for PDF processing)

### Steps

1. **Start infrastructure**:
   ```powershell
   # Start only Qdrant and Redis
   docker-compose up qdrant redis -d
   ```

2. **Setup Python environment**:
   ```powershell
   cd backend
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   ```

3. **Update .env file**:
   ```
   QDRANT_HOST=localhost
   REDIS_HOST=localhost
   ```

4. **Start backend**:
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

---

## 🔑 Configuration

All configuration is in the `.env` file:

```env
# API Keys (REQUIRED)
GEMINI_API_KEY=your_key_here

# Infrastructure
QDRANT_HOST=qdrant  # or localhost if running natively
REDIS_HOST=redis    # or localhost if running natively

# Application Settings
MAX_FILE_SIZE_MB=50
SIMILARITY_THRESHOLD=0.75
TOP_K_SEARCH=20
RERANK_TOP_N=5

# Security
JWT_SECRET_KEY=your_secret_key_here
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_UPLOADS_PER_HOUR=10
RATE_LIMIT_QUERIES_PER_HOUR=100
```

---

## 🧪 Testing the API

### 1. Health Check
```powershell
curl http://localhost:8000/api/health
```

### 2. Upload a PDF
```powershell
curl -X POST "http://localhost:8000/api/v1/documents/upload" `
  -H "accept: application/json" `
  -H "Content-Type: multipart/form-data" `
  -F "file=@path/to/your/document.pdf"
```

### 3. Query Documents
```powershell
curl -X POST "http://localhost:8000/api/v1/search/query" `
  -H "accept: application/json" `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"your search query\",\"top_k\":5}'
```

### 4. Use Interactive API Docs
Visit http://localhost:8000/docs for Swagger UI with all endpoints

---

## 🔍 Troubleshooting

### Docker not running
```
Error: Docker is not running!
```
**Solution**: Start Docker Desktop and wait for it to fully start

### Port already in use
```
Error: Bind for 0.0.0.0:8000 failed: port is already allocated
```
**Solution**: Stop the conflicting service or change ports in docker-compose.yml

### Build takes too long
**Solution**: First build takes 5-10 minutes to download dependencies. Subsequent builds are cached and much faster.

### Import errors or module not found
```
ModuleNotFoundError: No module named 'spacy'
```
**Solution**:
- Docker: Rebuild the container: `docker-compose up --build`
- Native: Reinstall dependencies: `pip install -r requirements.txt`

### Qdrant connection refused
```
Error: Connection refused
```
**Solution**: Make sure Qdrant container is running: `docker ps`

### GEMINI_API_KEY not set
**Solution**: Add your API key to `.env` file

---

## 📊 Monitoring

### View Container Status
```powershell
docker-compose ps
```

### View Logs
```powershell
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f qdrant
docker-compose logs -f redis
```

### Check Resource Usage
```powershell
docker stats
```

---

## 🛠️ Development

### Hot Reload
Backend automatically reloads when you change code files:
- Edit files in `backend/app/`
- Save the file
- Backend restarts automatically

### Debugging
Add breakpoints or print statements in your code and view them in logs:
```powershell
docker-compose logs -f backend | Select-String "DEBUG"
```

### Running Tests
```powershell
cd backend
.\venv\Scripts\Activate.ps1
pytest
```

---

## 📁 Project Structure

```
documind-rag/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Configuration & security
│   │   ├── models/        # Data models
│   │   ├── services/      # Business logic
│   │   └── utils/         # Utilities
│   ├── tests/             # Unit & integration tests
│   ├── Dockerfile         # Backend container
│   └── requirements.txt   # Python dependencies
├── frontend/              # React frontend (to be implemented)
├── docker-compose.yml     # Container orchestration
├── .env                   # Environment variables
└── start.ps1              # Quick start script
```

---

## 🔗 Useful Links

- **GitHub Repository**: https://github.com/tusharpawar1217/documind-rag
- **API Documentation**: http://localhost:8000/docs
- **Qdrant Dashboard**: http://localhost:6333/dashboard
- **Project Documentation**: See other *.md files in the project

---

## 💡 Tips

1. **First Run**: Be patient during first Docker build (~5-10 min)
2. **Port Conflicts**: Make sure ports 8000, 6333, 6379 are available
3. **Performance**: Docker Desktop needs at least 4GB RAM allocated
4. **Development**: Use hot reload for faster development
5. **Production**: Review security settings in `.env` before deploying

---

## 📝 Next Steps

- Review `API_DOCUMENTATION.md` for detailed API usage
- Check `DEPLOYMENT.md` for production deployment
- Read `PROJECT_SUMMARY.md` for architecture overview
- See `WORKFLOW.md` for development workflow

---

**Built with ❤️ using FastAPI, Qdrant, Gemini AI**
