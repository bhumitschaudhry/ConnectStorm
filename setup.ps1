# File-Storm Quick Setup Script for Windows
# PowerShell version

Write-Host "⚡ File-Storm Setup Script" -ForegroundColor Cyan
Write-Host "==========================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✓ Python found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed. Please install Python 3.8+ first." -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "✓ Virtual environment already exists" -ForegroundColor Green
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "📦 Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create .env if it doesn't exist
if (-not (Test-Path ".env")) {
    Write-Host "📝 Creating .env file from template..." -ForegroundColor Yellow
    Copy-Item env.example .env
    Write-Host "✓ .env file created - Please edit it with your credentials" -ForegroundColor Green
} else {
    Write-Host "✓ .env file already exists" -ForegroundColor Green
}

# Create directories
Write-Host "📁 Creating directories..." -ForegroundColor Yellow
New-Item -ItemType Directory -Force -Path "templates" | Out-Null
New-Item -ItemType Directory -Force -Path "files" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:TEMP\filestorm_uploads" | Out-Null
New-Item -ItemType Directory -Force -Path "$env:TEMP\filestorm_storage" | Out-Null
Write-Host "✓ Directories created" -ForegroundColor Green

# Check for sample files
if (-not (Test-Path "files\sample1.txt")) {
    Write-Host "⚠ No sample files found in files\ directory" -ForegroundColor Yellow
    Write-Host "  Run the producer after adding some test files" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit .env file with your Redis, PostgreSQL, and S3 credentials"
Write-Host "2. Run: psql `$env:PG_URI -f schema.sql"
Write-Host "3. Start Flask: python app.py"
Write-Host "4. Start Consumer: python consumer.py"
Write-Host "5. Start Producer: python selenium_producer.py"
Write-Host ""
Write-Host "Or visit http://localhost:8080/upload to upload files manually"

