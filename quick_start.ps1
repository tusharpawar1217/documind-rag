# Quick Start Script - Run DocuMind on Localhost

Write-Host "🚀 DocuMind RAG - Quick Start" -ForegroundColor Cyan
Write-Host "=============================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Check .env file
Write-Host "📝 Step 1: Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env file and add your GEMINI_API_KEY" -ForegroundColor Red
    exit 1
}

# Check if API key is set
$envContent = Get-Content ".env" -Raw
if ($envContent -match "your_gemini_api_key_here_REPLACE_THIS") {
    Write-Host "⚠️  WARNING: Please update GEMINI_API_KEY in .env file!" -ForegroundColor Yellow
    Write-Host "Get your key from: https://makersuite.google.com/app/apikey" -ForegroundColor Cyan
    Write-Host ""
    $continue = Read-Host "Continue anyway? (y/n)"
    if ($continue -ne "y") {
        exit 1
    }
}

Write-Host "✅ Environment configuration found" -ForegroundColor Green
Write-Host ""

# Step 2: Check Docker
Write-Host "🐳 Step 2: Checking Docker..." -ForegroundColor Yellow
try {
    docker ps 2>&1 | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
    
    Write-Host "Starting Qdrant and Redis..." -ForegroundColor Cyan
    docker-compose up -d 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    Write-Host "✅ Infrastructure started" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Docker not running - will skip infrastructure" -ForegroundColor Yellow
    Write-Host "Note: You'll need to start Docker Desktop manually" -ForegroundColor Cyan
}
Write-Host ""

# Step 3: Setup Backend
Write-Host "🐍 Step 3: Setting up Python backend..." -ForegroundColor Yellow

cd backend

# Check if venv exists
if (-not (Test-Path "venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
}

# Activate venv
Write-Host "Activating virtual environment..." -ForegroundColor Cyan
.\venv\Scripts\Activate.ps1

# Install dependencies
Write-Host "Installing dependencies (this may take a few minutes)..." -ForegroundColor Cyan
pip install -q -r requirements.txt

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "⚠️  Some dependencies may have failed to install" -ForegroundColor Yellow
}

# Download spaCy model
Write-Host "Downloading spaCy model..." -ForegroundColor Cyan
python -m spacy download en_core_web_sm 2>&1 | Out-Null
Write-Host "✅ spaCy model ready" -ForegroundColor Green

cd ..
Write-Host ""

# Step 4: Start Backend Server
Write-Host "🚀 Step 4: Starting backend server..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Backend API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health Check: http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""

cd backend
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
