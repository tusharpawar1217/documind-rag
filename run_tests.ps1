# Run all tests with coverage

Write-Host "🧪 Running DocuMind RAG System Tests" -ForegroundColor Cyan
Write-Host "====================================" -ForegroundColor Cyan
Write-Host ""

Set-Location backend

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run tests with coverage
Write-Host "Running tests with coverage..." -ForegroundColor Yellow
pytest --cov=app --cov-report=html --cov-report=term-missing -v

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ All tests passed!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📊 Coverage report generated:" -ForegroundColor Cyan
    Write-Host "   Open: htmlcov/index.html" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "❌ Some tests failed" -ForegroundColor Red
    exit 1
}

Set-Location ..
