# DocuMind RAG - Complete Startup Script

Write-Host "🚀 DocuMind RAG - Starting Application" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "🐳 Checking Docker..." -ForegroundColor Yellow
try {
    docker ps 2>&1 | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running!" -ForegroundColor Red
    Write-Host "Please start Docker Desktop first" -ForegroundColor Yellow
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit 1
}

Write-Host ""

# Check if .env file exists
Write-Host "📝 Checking environment configuration..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "❌ .env file not found!" -ForegroundColor Red
    Write-Host "Please create .env file with your GEMINI_API_KEY" -ForegroundColor Yellow
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit 1
}
Write-Host "✅ Environment configuration found" -ForegroundColor Green
Write-Host ""

# Build and start all services
Write-Host "🔨 Building and starting services..." -ForegroundColor Yellow
Write-Host "This may take a few minutes on first run..." -ForegroundColor Cyan
Write-Host ""

docker-compose up --build -d

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "📊 Service Status:" -ForegroundColor Cyan
    Write-Host ""
    
    # Wait a bit for services to start
    Start-Sleep -Seconds 3
    
    docker-compose ps
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "🌐 Access Points:" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Backend API:     http://localhost:8000" -ForegroundColor White
    Write-Host "  API Docs:        http://localhost:8000/docs" -ForegroundColor White
    Write-Host "  Health Check:    http://localhost:8000/api/health" -ForegroundColor White
    Write-Host "  Qdrant:          http://localhost:6333/dashboard" -ForegroundColor White
    Write-Host "  Redis:           localhost:6379" -ForegroundColor White
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Useful Commands:" -ForegroundColor Cyan
    Write-Host "  View logs:       docker-compose logs -f" -ForegroundColor White
    Write-Host "  Stop services:   docker-compose down" -ForegroundColor White
    Write-Host "  Restart:         docker-compose restart" -ForegroundColor White
    Write-Host "  Backend logs:    docker-compose logs -f backend" -ForegroundColor White
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "🎉 DocuMind RAG is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Opening API documentation in browser..." -ForegroundColor Cyan
    Start-Sleep -Seconds 2
    Start-Process "http://localhost:8000/docs"
    
} else {
    Write-Host ""
    Write-Host "❌ Failed to start services" -ForegroundColor Red
    Write-Host "Check the error messages above" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
    exit 1
}
