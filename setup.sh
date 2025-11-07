#!/bin/bash
# File-Storm Quick Setup Script

set -e

echo "⚡ File-Storm Setup Script"
echo "=========================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.8+ first."
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo "✓ Dependencies installed"

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp env.example .env
    echo "✓ .env file created - Please edit it with your credentials"
else
    echo "✓ .env file already exists"
fi

# Create directories
echo "📁 Creating directories..."
mkdir -p templates
mkdir -p files
mkdir -p /tmp/filestorm_uploads
mkdir -p /tmp/filestorm_storage
echo "✓ Directories created"

# Check for sample files
if [ ! -f "files/sample1.txt" ]; then
    echo "⚠ No sample files found in files/ directory"
    echo "  Run the producer after adding some test files"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env file with your Redis, PostgreSQL, and S3 credentials"
echo "2. Run: psql \$PG_URI -f schema.sql"
echo "3. Start Flask: python app.py"
echo "4. Start Consumer: python consumer.py"
echo "5. Start Producer: python selenium_producer.py"
echo ""
echo "Or visit http://localhost:8080/upload to upload files manually"

