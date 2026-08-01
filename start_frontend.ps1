# Quick start script for frontend

Write-Host "⚛️  Starting DocuMind Frontend..." -ForegroundColor Cyan
Write-Host ""

Set-Location frontend

if (-not (Test-Path "node_modules")) {
    Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
    npm install
}

Write-Host "✅ Starting development server..." -ForegroundColor Green
Write-Host ""
Write-Host "📍 Frontend: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""

npm run dev
