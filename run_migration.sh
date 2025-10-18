#!/bin/bash
# Script to run database migration for message system

echo "=== Database Migration for Message System ==="
echo ""
echo "This script will:"
echo "1. Check if database exists"
echo "2. If not, start the backend briefly to create it"
echo "3. Run the migration to add message system tables/columns"
echo ""

cd "$(dirname "$0")"

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠ Warning: No virtual environment detected"
    echo "Please activate your virtual environment first:"
    echo "  source venv/bin/activate"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if database exists and has content
if [ -f "data/support_agent.db" ] && [ -s "data/support_agent.db" ]; then
    echo "✓ Database found: data/support_agent.db"
else
    echo "⚠ Database not found or empty"
    echo ""
    echo "Please start the backend server first to create the database:"
    echo "  cd /tmp/TicketingSDT"
    echo "  source venv/bin/activate"
    echo "  uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003"
    echo ""
    echo "Once the server starts successfully (shows 'Application startup complete'),"
    echo "you can stop it (Ctrl+C) and run this migration script again."
    exit 1
fi

# Run migration
echo ""
echo "Running migration..."
python3 migrate_message_system.py

echo ""
echo "=== Migration Complete ==="
echo ""
echo "You can now start your backend server:"
echo "  uvicorn src.api.web_api:app --host 0.0.0.0 --port 8003"
