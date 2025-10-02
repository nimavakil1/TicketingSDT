#!/bin/bash
# Troubleshooting script for AI Support Agent
# Helps diagnose common issues

echo "============================================"
echo "AI Support Agent - Troubleshooting"
echo "============================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_pass() {
    echo -e "${GREEN}✓${NC} $1"
}

check_fail() {
    echo -e "${RED}✗${NC} $1"
}

check_warn() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    check_pass "Python $PYTHON_VERSION (requires 3.11+)"
else
    check_fail "Python $PYTHON_VERSION (requires 3.11+)"
fi

# Check if virtual environment exists
echo ""
echo "Checking virtual environment..."
if [ -d "venv" ]; then
    check_pass "Virtual environment exists"
else
    check_fail "Virtual environment not found (run: python3.11 -m venv venv)"
fi

# Check .env file
echo ""
echo "Checking configuration..."
if [ -f ".env" ]; then
    check_pass ".env file exists"

    # Check for required variables
    if grep -q "TICKETING_API_PASSWORD" .env; then
        check_pass "TICKETING_API_PASSWORD is set"
    else
        check_fail "TICKETING_API_PASSWORD not found in .env"
    fi

    if grep -q "GMAIL_SUPPORT_EMAIL" .env; then
        check_pass "GMAIL_SUPPORT_EMAIL is set"
    else
        check_fail "GMAIL_SUPPORT_EMAIL not found in .env"
    fi

    if grep -q "OPENAI_API_KEY\|ANTHROPIC_API_KEY\|GOOGLE_API_KEY" .env; then
        check_pass "AI API key is set"
    else
        check_fail "No AI API key found in .env"
    fi
else
    check_fail ".env file not found (run: cp .env.example .env)"
fi

# Check Gmail credentials
echo ""
echo "Checking Gmail credentials..."
if [ -f "config/gmail_credentials.json" ]; then
    check_pass "Gmail OAuth credentials exist"
else
    check_fail "Gmail OAuth credentials not found"
fi

if [ -f "config/gmail_token.json" ]; then
    check_pass "Gmail token exists"
else
    check_warn "Gmail token not found (will be created on first run)"
fi

# Check directories
echo ""
echo "Checking directories..."
for dir in data logs config; do
    if [ -d "$dir" ]; then
        check_pass "$dir/ directory exists"
    else
        check_warn "$dir/ directory missing (will be created)"
        mkdir -p "$dir"
    fi
done

# Check if service is running
echo ""
echo "Checking service status..."
if systemctl is-active --quiet ai-support-agent 2>/dev/null; then
    check_pass "Service is running"

    # Check recent logs
    echo ""
    echo "Recent service logs:"
    echo "-------------------"
    sudo journalctl -u ai-support-agent -n 10 --no-pager
else
    check_warn "Service is not running (or not installed as systemd service)"
fi

# Check database
echo ""
echo "Checking database..."
if [ -f "data/support_agent.db" ]; then
    check_pass "Database file exists"

    # Check database size
    SIZE=$(du -h data/support_agent.db | cut -f1)
    echo "  Database size: $SIZE"

    # Count records
    if command -v sqlite3 &> /dev/null; then
        EMAILS=$(sqlite3 data/support_agent.db "SELECT COUNT(*) FROM processed_emails;" 2>/dev/null || echo "0")
        TICKETS=$(sqlite3 data/support_agent.db "SELECT COUNT(*) FROM ticket_states;" 2>/dev/null || echo "0")
        echo "  Processed emails: $EMAILS"
        echo "  Tickets tracked: $TICKETS"
    fi
else
    check_warn "Database not yet created (will be created on first run)"
fi

# Check logs
echo ""
echo "Checking logs..."
if [ -f "logs/support_agent.log" ]; then
    check_pass "Log file exists"

    SIZE=$(du -h logs/support_agent.log | cut -f1)
    echo "  Log size: $SIZE"

    # Check for recent errors
    ERRORS=$(grep -c "ERROR" logs/support_agent.log 2>/dev/null || echo "0")
    if [ "$ERRORS" -gt 0 ]; then
        check_warn "Found $ERRORS error(s) in logs"
        echo ""
        echo "Recent errors:"
        echo "-------------"
        grep "ERROR" logs/support_agent.log | tail -5
    else
        check_pass "No errors in logs"
    fi
else
    check_warn "Log file not yet created"
fi

# Test configuration loading
echo ""
echo "Testing configuration loading..."
if [ -f "test_config.py" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
        python test_config.py
        deactivate
    else
        python3 test_config.py
    fi
else
    check_warn "test_config.py not found"
fi

# Summary
echo ""
echo "============================================"
echo "Troubleshooting Summary"
echo "============================================"
echo ""
echo "If you see failures above, try these steps:"
echo ""
echo "1. For Python version issues:"
echo "   sudo apt install python3.11 python3.11-venv"
echo ""
echo "2. For missing .env:"
echo "   cp .env.example .env"
echo "   nano .env  # Add your credentials"
echo ""
echo "3. For missing Gmail credentials:"
echo "   # Download from Google Cloud Console"
echo "   # Save as config/gmail_credentials.json"
echo ""
echo "4. For service issues:"
echo "   sudo systemctl restart ai-support-agent"
echo "   sudo journalctl -u ai-support-agent -f"
echo ""
echo "5. For configuration errors:"
echo "   python test_config.py"
echo ""
echo "See README.md and BUGFIXES.md for more help."
echo ""
