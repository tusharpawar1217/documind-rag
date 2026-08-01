# DocuMind RAG System - Deployment Guide

## Prerequisites

### Required Software
- **Python 3.11+** - Backend runtime
- **Node.js 18+** - Frontend build tools
- **Docker & Docker Compose** - Infrastructure services
- **Git** - Version control

### Required API Keys
- **Google Gemini API Key** - For embeddings, vision, and text generation
  - Obtain from: https://makersuite.google.com/app/apikey
  - Required quotas:
    - Embeddings: 1500 requests/minute
    - Text generation: 60 requests/minute
    - Vision API: 60 requests/minute

## Quick Start (Development)

### 1. Clone Repository
```bash
git clone <repository-url>
cd "new rag"
```

### 2. Set Up Environment Variables
```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Gemini API key
# GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Start Infrastructure Services
```bash
# Start Qdrant and Redis using Docker Compose
docker-compose up -d

# Verify services are running
docker-compose ps
```

### 4. Set Up Backend

#### Install Python Dependencies
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm
```

#### Run Backend Server
```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python -m app.main
```

Backend will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 5. Set Up Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:5173

## Production Deployment

### Backend Deployment

#### Option 1: Docker Container
```bash
# Create Dockerfile for backend
cd backend

# Build image
docker build -t documind-backend .

# Run container
docker run -d \
  --name documind-backend \
  -p 8000:8000 \
  --env-file ../.env \
  --network documind-network \
  documind-backend
```

#### Option 2: Traditional Server
```bash
# Install dependencies in production
pip install -r requirements.txt --no-dev

# Run with Gunicorn (production WSGI server)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### Frontend Deployment

#### Build for Production
```bash
cd frontend

# Build optimized bundle
npm run build

# Output will be in dist/ directory
```

#### Serve Static Files
Options:
1. **Nginx** - Recommended
2. **Apache**
3. **Netlify/Vercel** - For static hosting
4. **AWS S3 + CloudFront** - For CDN

Example Nginx configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/documind/frontend/dist;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Configuration

### Required Environment Variables

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key

# Qdrant Configuration
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=documind

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379

# Application Settings
MAX_FILE_SIZE_MB=50
SIMILARITY_THRESHOLD=0.75
MAX_CHUNK_SIZE=512
TOP_K_SEARCH=20
RERANK_TOP_N=5

# Security
JWT_SECRET_KEY=<generate_a_secure_random_key>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_UPLOADS_PER_HOUR=10
RATE_LIMIT_QUERIES_PER_HOUR=100

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/app.log
```

### Generate Secure JWT Secret
```bash
# Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# OpenSSL
openssl rand -base64 32
```

## Infrastructure Services

### Qdrant Vector Database

**Development:**
```bash
docker-compose up -d qdrant
```

**Production:** Use Qdrant Cloud or self-hosted cluster
- URL: https://cloud.qdrant.io/
- Configure `QDRANT_HOST` and `QDRANT_API_KEY`

### Redis Cache (Optional)

**Development:**
```bash
docker-compose up -d redis
```

**Production:** Use managed Redis service
- AWS ElastiCache
- Azure Cache for Redis
- Redis Cloud

## Monitoring and Observability

### Log Files
- Application logs: `./logs/app.log`
- Format: JSON for structured logging
- Rotation: Implement with `logrotate` or similar

### Metrics to Monitor
1. **Query Latency**
   - Target: < 2 seconds
   - Percentiles: p50, p95, p99

2. **Document Processing Time**
   - Target: < 30 seconds for 10 pages

3. **Hit@5 Accuracy**
   - Target: >= 96%

4. **API Error Rate**
   - Target: < 5%

5. **Qdrant Performance**
   - Query time: < 100ms
   - Index size growth

### Health Checks
```bash
# Backend health
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "services": {
    "qdrant": "up",
    "gemini": "up"
  }
}
```

## Performance Tuning

### Backend Optimization
1. **Worker Processes**: Set to number of CPU cores
   ```bash
   gunicorn --workers $(nproc)
   ```

2. **Qdrant Connection Pool**: Increase for high concurrency
   ```bash
   QDRANT_POOL_SIZE=20
   ```

3. **Batch Embedding Size**: Adjust based on API limits
   ```bash
   EMBEDDING_BATCH_SIZE=32
   ```

### Database Optimization
1. **Qdrant HNSW Parameters**
   - `ef_construct=128` - Build quality
   - `m=16` - Graph connectivity

2. **Redis Memory**
   - Set `maxmemory` policy
   - Use LRU eviction

## Security Checklist

- [ ] Change default JWT secret key
- [ ] Enable HTTPS/TLS in production
- [ ] Configure CORS appropriately (not allow_origins=["*"])
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Regular security updates
- [ ] Rotate API keys every 90 days
- [ ] Enable audit logging
- [ ] Use secrets manager for credentials
- [ ] Implement backup strategy

## Backup and Recovery

### Qdrant Backup
```bash
# Create snapshot
curl -X POST http://localhost:6333/collections/documind/snapshots

# Download snapshot
curl http://localhost:6333/collections/documind/snapshots/{snapshot_name} -o backup.snapshot
```

### Document Storage Backup
```bash
# Backup uploaded files
tar -czf documents_backup_$(date +%Y%m%d).tar.gz data/uploads/
```

### Database Restore
```bash
# Restore Qdrant snapshot
curl -X PUT http://localhost:6333/collections/documind/snapshots/upload \
  -H 'Content-Type: multipart/form-data' \
  -F 'snapshot=@backup.snapshot'
```

## Troubleshooting

### Common Issues

#### 1. Qdrant Connection Failed
```bash
# Check if Qdrant is running
docker-compose ps qdrant

# Check logs
docker-compose logs qdrant

# Restart service
docker-compose restart qdrant
```

#### 2. Gemini API Rate Limits
- Implement exponential backoff (already included)
- Check API quota in Google Cloud Console
- Reduce `EMBEDDING_BATCH_SIZE`

#### 3. Out of Memory
- Reduce worker processes
- Increase Docker memory limits
- Optimize chunk sizes

#### 4. Slow Query Performance
- Check Qdrant index status
- Monitor embedding generation time
- Review reranker performance
- Check network latency

### Debug Mode
```bash
# Enable debug logging
LOG_LEVEL=DEBUG uvicorn app.main:app --reload
```

## Scaling

### Horizontal Scaling
1. Deploy multiple backend instances behind load balancer
2. Use shared Qdrant cluster
3. Redis for distributed caching
4. Stateless API design (already implemented)

### Vertical Scaling
- Increase CPU for faster embedding generation
- More RAM for larger batch processing
- SSD storage for Qdrant performance

## Testing

### Run Unit Tests
```bash
cd backend
pytest
```

### Run with Coverage
```bash
pytest --cov=app --cov-report=html
```

### Integration Tests
```bash
pytest tests/integration/
```

## Support

For issues and questions:
- Check logs in `./logs/app.log`
- Review API documentation at `/docs`
- Consult design docs in `.kiro/specs/`

## License

[Your License Here]
