# Quick start script for backend

Write-Host "🚀 Starting DocuMind Backend..." -ForegroundColor Cyan
Write-Host ""

# Check if infrastructure is running
$qdrantRunning = docker ps | Select-String "documind-qdrant"
$redisRunning = docker ps | Select-String "documind-redis"

if (-not $qdrantRunning -or -not $redisRunning) {
    Write-Host "⚠️  Infrastructure not running. Starting..." -ForegroundColor Yellow
    docker-compose up -d
    Start-Sleep -Seconds 3
}

Set-Location backend

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
} else {
    Write-Host "❌ Virtual environment not found. Run setup.ps1 first." -ForegroundColor Red
    exit 1
}

# Check if .env exists
if (-not (Test-Path "../.env")) {
    Write-Host "❌ .env file not found. Please create it and add GEMINI_API_KEY" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Starting FastAPI server..." -ForegroundColor Green
Write-Host ""
Write-Host "📍 API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
