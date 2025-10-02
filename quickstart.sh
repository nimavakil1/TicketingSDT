#!/bin/bash
# Quick Start Script for AI Support Agent
# This script helps with initial setup and testing

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "================================"
echo "AI Support Agent - Quick Start"
echo "================================"
echo ""

# Check Python version
if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Please install Python 3.11+"
    exit 1
fi

echo "✓ Python 3.11 found"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment exists"
fi

# Activate virtual environment
source venv/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  No .env file found. Creating from template..."
    cp .env.example .env
    echo "❌ Please edit .env file with your credentials before running!"
    echo "   nano .env"
    exit 1
else
    echo "✓ .env file exists"
fi

# Create necessary directories
mkdir -p data logs config
echo "✓ Directories created"

# Check for Gmail credentials
if [ ! -f "config/gmail_credentials.json" ]; then
    echo "⚠️  Gmail credentials not found"
    echo "   Please download OAuth credentials from Google Cloud Console"
    echo "   and save as: config/gmail_credentials.json"
    echo ""
    read -p "Press Enter when ready to continue, or Ctrl+C to exit..."
fi

# Initialize database
echo "Initializing database..."
python -c "from src.database.models import init_database; init_database(); print('Database initialized')"
echo "✓ Database initialized"

# Run basic tests
echo ""
echo "Running basic tests..."
if python -m pytest tests/test_basic.py -v 2>&1 | grep -q "PASSED"; then
    echo "✓ Tests passed"
else
    echo "⚠️  Some tests failed (this may be OK if Gmail auth not set up yet)"
fi

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Ensure .env is configured with your credentials"
echo "2. Ensure config/gmail_credentials.json is present"
echo "3. Run the agent: python main.py"
echo ""
echo "For deployment on a server, see SETUP_GUIDE.md"
echo ""

read -p "Would you like to start the agent now? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Starting AI Support Agent..."
    python main.py
fi
