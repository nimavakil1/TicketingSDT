# AI Customer Support Agent

An intelligent customer support automation system for dropshipping companies. This agent monitors support emails, analyzes tickets using AI, and handles customer and supplier communications automatically.

## Features

### Core Capabilities
- **Email Monitoring**: Monitors Gmail inbox for new support requests
- **AI-Powered Analysis**: Uses OpenAI, Anthropic, or Gemini to analyze customer inquiries
- **Multi-Language Support**: Automatically detects and responds in customer's language (German, English, French, Spanish, etc.)
- **Ticketing Integration**: Full integration with existing ticketing system API
- **Supplier Management**: Tracks supplier communications and sends automated reminders
- **Phased Deployment**: Supports gradual rollout from shadow mode to full automation

### Deployment Phases
1. **Phase 1 (Shadow Mode)**: AI generates suggestions as internal ticket notes for human review
2. **Phase 2 (Partial Automation)**: AI sends actual emails to customers and suppliers (with confidence threshold)
3. **Phase 3 (Full Integration)**: Complete automation with human oversight for escalations

### Key Features
- **Idempotency**: Each email processed exactly once, prevents duplicates
- **Context Awareness**: Maintains conversation history and ticket state
- **Confidence Scoring**: Escalates uncertain cases to human operators
- **Supplier Reminders**: Automatically follows up if suppliers don't respond within 24 hours
- **Audit Trail**: Comprehensive logging of all AI decisions and actions

## Architecture

```
┌─────────────────┐
│  Gmail Inbox    │
└────────┬────────┘
         │
         v
┌─────────────────────────────────────┐
│   Gmail Monitor                     │
│   - Fetches unprocessed emails      │
│   - Extracts order numbers          │
│   - Tags processed messages         │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│   Ticketing API Client              │
│   - Authenticates with Bearer token │
│   - Retrieves/creates tickets       │
│   - Sends messages                  │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│   AI Engine                         │
│   - Detects language                │
│   - Analyzes intent                 │
│   - Generates responses             │
│   - Calculates confidence           │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│   Action Dispatcher                 │
│   - Phase 1: Posts internal notes   │
│   - Phase 2: Sends actual emails    │
│   - Handles escalations             │
└────────┬────────────────────────────┘
         │
         v
┌─────────────────────────────────────┐
│   Supplier Manager                  │
│   - Tracks supplier messages        │
│   - Sends reminders after 24h       │
│   - Alerts operations team          │
└─────────────────────────────────────┘
```

## Version Information

**Current Version**: 1.0.1

### Recent Updates
- **v1.0.1** (Oct 2, 2025): Fixed Pydantic configuration type conversion for environment variables. See [BUGFIXES.md](BUGFIXES.md) for details.
- **v1.0.0** (Oct 2, 2025): Initial release

## Installation

### Prerequisites
- Python 3.11+
- Gmail account with API access
- Ticketing system API credentials
- OpenAI/Anthropic/Gemini API key

### Setup

1. **Clone and install dependencies**:
```bash
cd ai-support-agent
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure Gmail API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop app)
   - Download credentials and save as `config/gmail_credentials.json`

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your credentials
```

Required settings in `.env`:
```env
# Ticketing API (credentials provided in PDF)
TICKETING_API_USERNAME=TicketingAgent
TICKETING_API_PASSWORD=75U4$d1GN5Ld>q8&vy)|\(82!&3W3ZH

# Gmail
GMAIL_SUPPORT_EMAIL=support@yourcompany.com

# AI Provider (choose one)
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...

# Phase (1=Shadow, 2=Automated, 3=Full)
DEPLOYMENT_PHASE=1

# Operations email for alerts
INTERNAL_ALERT_EMAIL=operations@yourcompany.com
```

4. **Initial run** (authenticates Gmail):
```bash
python main.py
```
First run will open a browser for Gmail OAuth authentication.

## Usage

### Running the Agent

**Direct execution**:
```bash
python main.py
```

**Using Docker**:
```bash
docker-compose up -d
```

**As a systemd service** (Ubuntu/Linux):
```bash
# Edit ai-support-agent.service with correct paths
sudo cp ai-support-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ai-support-agent
sudo systemctl start ai-support-agent

# Check status
sudo systemctl status ai-support-agent

# View logs
sudo journalctl -u ai-support-agent -f
```

### Managing Suppliers

The system needs supplier contact information. You can add suppliers directly to the database:

```python
from src.database.models import init_database, Supplier
from sqlalchemy.orm import sessionmaker

Session = init_database()
session = Session()

# Add a supplier
supplier = Supplier(
    name="Supplier X",
    default_email="contact@supplierx.com",
    contact_fields={
        "returns": "returns@supplierx.com",
        "tracking": "tracking@supplierx.com",
        "general": "info@supplierx.com"
    }
)
session.add(supplier)
session.commit()
```

Alternatively, create a simple admin script or manage via database tool.

### Monitoring

**Logs**:
```bash
tail -f logs/support_agent.log
```

**Database**:
```bash
sqlite3 data/support_agent.db
```

Useful queries:
```sql
-- View processed emails
SELECT * FROM processed_emails ORDER BY processed_at DESC LIMIT 10;

-- View AI decisions
SELECT * FROM ai_decision_logs ORDER BY created_at DESC LIMIT 10;

-- View tickets requiring escalation
SELECT * FROM ticket_states WHERE escalated = 1;

-- View pending supplier messages
SELECT * FROM supplier_messages WHERE response_received = 0;
```

## Configuration

### AI Model Selection

Edit `.env`:
```env
# OpenAI
AI_PROVIDER=openai
AI_MODEL=gpt-4
OPENAI_API_KEY=sk-...

# Anthropic Claude
AI_PROVIDER=anthropic
AI_MODEL=claude-3-opus-20240229
ANTHROPIC_API_KEY=sk-ant-...

# Google Gemini
AI_PROVIDER=gemini
AI_MODEL=gemini-pro
GOOGLE_API_KEY=...
```

### Confidence Threshold

For Phase 2, set the minimum confidence required for automated responses:
```env
CONFIDENCE_THRESHOLD=0.75  # 75% confidence required
```

Lower values = more automation but potentially lower quality.
Higher values = more escalations but higher quality.

### Polling Interval

How often to check for new emails (in seconds):
```env
EMAIL_POLL_INTERVAL_SECONDS=60  # Check every minute
```

### Supplier Reminder Timing

Hours to wait before sending supplier reminder:
```env
SUPPLIER_REMINDER_HOURS=24
```

## Phased Deployment Guide

### Phase 1: Shadow Mode (Recommended Start)

**Purpose**: Evaluate AI performance without risking customer experience.

1. Set `DEPLOYMENT_PHASE=1` in `.env`
2. Start the agent
3. AI posts suggestions as internal ticket notes
4. Human operators review and provide feedback
5. Monitor accuracy in logs/database

**Success Criteria**:
- AI suggestions match human actions >80% of the time
- No major errors or inappropriate responses
- Language detection working correctly

### Phase 2: Partial Automation

**Purpose**: Automate straightforward cases, escalate complex ones.

1. Set `DEPLOYMENT_PHASE=2` in `.env`
2. Configure `CONFIDENCE_THRESHOLD` (start with 0.85)
3. AI will send actual emails when confidence > threshold
4. Low-confidence cases still escalate to humans

**Monitoring**:
- Track customer satisfaction
- Monitor escalation rates
- Review AI decision logs
- Gradually lower threshold if performance is good

### Phase 3: Full Integration

**Purpose**: Complete automation with minimal human intervention.

1. Set `DEPLOYMENT_PHASE=3` in `.env`
2. AI handles all non-escalated tickets
3. Humans focus only on escalated cases
4. Consider building custom UI for operators

## API Reference

### Ticketing System API

The system integrates with the following endpoints:

- `POST /Account/login` - Authentication
- `GET /tickets/GetTicketsByAmazonOrderNumber` - Fetch ticket by order
- `GET /tickets/GetTicketsByTicketNumber` - Fetch by ticket number
- `POST /tickets/UpsertTicket` - Create/update ticket
- `POST /tickets/SendMessageToCustomer/{ticketId}` - Email customer
- `POST /tickets/SendMessageToSupplier/{ticketId}` - Email supplier
- `POST /tickets/SendInternalMessage/{ticketId}` - Internal note

See `Ticketing APIs.pdf` for full documentation.

## Troubleshooting

### Gmail Authentication Issues

```bash
# Remove existing token and re-authenticate
rm config/gmail_token.json
python main.py
```

### AI API Errors

Check API key is valid and has credits:
```bash
# OpenAI
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Database Locked

If running multiple instances accidentally:
```bash
# Check for running processes
ps aux | grep main.py
# Kill if needed
pkill -f main.py
```

### Ticketing API Authentication

Token expires after ~25 minutes. System auto-refreshes, but if issues persist:
```python
# Test authentication manually
from src.api.ticketing_client import TicketingAPIClient
client = TicketingAPIClient()
client._login()
print("Authentication successful")
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Structure

```
ai-support-agent/
├── config/              # Configuration
│   └── settings.py      # Environment settings
├── src/
│   ├── api/            # Ticketing API client
│   ├── email/          # Gmail monitoring
│   ├── ai/             # AI engine and language detection
│   ├── dispatcher/     # Action dispatcher
│   ├── utils/          # Supplier manager
│   ├── database/       # SQLAlchemy models
│   └── orchestrator.py # Main orchestrator
├── data/               # SQLite database
├── logs/               # Application logs
├── main.py             # Entry point
└── requirements.txt    # Dependencies
```

### Adding New Features

1. **New Ticket Type**: Update `AIEngine.TICKET_TYPES` and AI prompts
2. **New Language**: Add to `language_detector.py` mappings
3. **Custom Actions**: Extend `ActionDispatcher._dispatch_phase2()`

## Security Considerations

- **Credentials**: Never commit `.env` or credentials files
- **API Keys**: Use environment variables or secure vault
- **Gmail OAuth**: Token file contains sensitive data, protect it
- **Database**: Contains customer data, ensure proper file permissions
- **Logs**: May contain PII, rotate and secure log files

## Performance

### Resource Usage

- **Memory**: ~200MB baseline, +100MB per AI request
- **CPU**: Low when idle, spikes during AI analysis
- **Network**: Depends on email volume and API calls
- **Database**: Grows with ticket history, plan for growth

### Scaling

For high volume:
- Use PostgreSQL instead of SQLite
- Run multiple instances with queue (e.g., Redis/RabbitMQ)
- Implement caching for frequent API calls
- Consider async/await for concurrent processing

## License

Proprietary - Internal use only

## Support

For issues or questions:
1. Check logs: `logs/support_agent.log`
2. Review database: `data/support_agent.db`
3. Test components individually (see Troubleshooting)

---

**Version**: 1.0.0
**Last Updated**: 2025-10-02
