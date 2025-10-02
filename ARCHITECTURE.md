# AI Support Agent - Architecture Documentation

## System Overview

The AI Customer Support Agent is a comprehensive automation system designed for dropshipping companies to handle customer and supplier communications intelligently.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         External Systems                         │
├─────────────────────────────────────────────────────────────────┤
│  Gmail API        Ticketing API       AI Provider (OpenAI/etc)  │
└─────┬───────────────────┬───────────────────────┬───────────────┘
      │                   │                       │
      v                   v                       v
┌─────────────────────────────────────────────────────────────────┐
│                      AI Support Agent Core                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Main Orchestrator (src/orchestrator.py)                 │  │
│  │  - Coordinates all components                            │  │
│  │  - Manages processing workflow                           │  │
│  │  - Handles error recovery                                │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ Email Module │  │  API Client  │  │   AI Engine          │ │
│  │              │  │              │  │                      │ │
│  │ - Gmail API  │  │ - Auth       │  │ - Language Detect   │ │
│  │ - Parse      │  │ - Tickets    │  │ - Intent Analysis   │ │
│  │ - Extract    │  │ - Messages   │  │ - Response Gen      │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  Dispatcher  │  │   Database   │  │  Supplier Manager    │ │
│  │              │  │              │  │                      │ │
│  │ - Phase 1/2  │  │ - State      │  │ - Tracking          │ │
│  │ - Actions    │  │ - History    │  │ - Reminders         │ │
│  │ - Escalation │  │ - Audit      │  │ - Alerts            │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              v
                    ┌──────────────────┐
                    │  SQLite Database │
                    │  - Tickets       │
                    │  - Emails        │
                    │  - Suppliers     │
                    │  - AI Logs       │
                    └──────────────────┘
```

## Component Details

### 1. Gmail Monitor (`src/email/gmail_monitor.py`)

**Responsibilities:**
- Authenticates with Gmail API using OAuth2
- Polls inbox for unprocessed messages
- Extracts email content (subject, body, sender)
- Identifies order numbers and ticket numbers
- Marks processed emails with label
- Prevents duplicate processing

**Key Methods:**
- `get_unprocessed_messages()` - Fetches new emails
- `extract_order_number()` - Parses order IDs
- `mark_as_processed()` - Labels emails
- `_extract_body()` - Handles multipart emails

**Technologies:**
- Google OAuth2
- Gmail API v1
- Email parsing (base64 decoding, HTML stripping)

### 2. Ticketing API Client (`src/api/ticketing_client.py`)

**Responsibilities:**
- Authenticates with ticketing system (Bearer token)
- Retrieves tickets by order/ticket/PO number
- Creates/updates tickets (UpsertTicket)
- Sends messages to customers
- Sends messages to suppliers
- Posts internal notes
- Handles token refresh (25-minute expiry)

**Key Methods:**
- `_login()` - Authentication with retry logic
- `get_ticket_by_amazon_order_number()` - Ticket lookup
- `send_message_to_customer()` - Customer emails
- `send_message_to_supplier()` - Supplier emails
- `send_internal_message()` - Internal notes
- `upsert_ticket()` - Create/update tickets

**Technologies:**
- REST API with JWT authentication
- Multipart form data for attachments
- Exponential backoff retry logic

### 3. AI Engine (`src/ai/ai_engine.py`)

**Responsibilities:**
- Analyzes customer emails for intent
- Detects language (de-DE, en-US, fr-FR, etc.)
- Generates appropriate responses
- Calculates confidence scores
- Determines escalation needs
- Supports multiple AI providers

**Key Methods:**
- `analyze_email()` - Main analysis function
- `_build_analysis_prompt()` - Constructs context
- `_parse_ai_response()` - Parses JSON output
- `generate_custom_response()` - For specific scenarios

**AI Providers:**
- OpenAI (GPT-4, GPT-3.5-turbo)
- Anthropic (Claude 3 Opus, Sonnet, Haiku)
- Google (Gemini Pro)

**Output Format:**
```json
{
  "intent": "tracking_inquiry",
  "ticket_type_id": 2,
  "confidence": 0.85,
  "requires_escalation": false,
  "customer_response": "Email text in customer's language",
  "supplier_action": {
    "action": "request_tracking",
    "message": "Email to supplier"
  },
  "summary": "Customer asking about delivery status"
}
```

### 4. Language Detector (`src/ai/language_detector.py`)

**Responsibilities:**
- Detects text language using langdetect
- Maps to culture codes (de-DE, en-US, etc.)
- Provides fallback to English

**Supported Languages:**
- German (de-DE)
- English (en-US)
- French (fr-FR)
- Spanish (es-ES)
- Italian (it-IT)
- Dutch (nl-NL)
- Polish (pl-PL)
- Portuguese (pt-PT)

### 5. Action Dispatcher (`src/dispatcher/action_dispatcher.py`)

**Responsibilities:**
- Executes actions based on AI analysis
- Adapts behavior for deployment phases
- Handles escalations
- Logs AI decisions
- Updates ticket states

**Phase Behaviors:**
- **Phase 1 (Shadow)**: Posts internal notes with suggestions
- **Phase 2 (Automated)**: Sends actual emails, checks confidence
- **Phase 3 (Full)**: Complete automation

**Key Methods:**
- `dispatch()` - Main entry point
- `_dispatch_phase1()` - Shadow mode
- `_dispatch_phase2()` - Automated mode
- `_handle_escalation()` - Escalation workflow

### 6. Supplier Manager (`src/utils/supplier_manager.py`)

**Responsibilities:**
- Manages supplier contact information
- Tracks supplier message timings
- Sends automated reminders after 24h
- Alerts operations team
- Marks responses received

**Key Methods:**
- `get_or_create_supplier()` - Supplier management
- `record_supplier_message()` - Track outgoing
- `check_and_send_reminders()` - Automated follow-up
- `mark_supplier_response_received()` - Update status

**Reminder Workflow:**
1. Message sent to supplier → recorded with timestamp
2. After 24h (configurable) → reminder email sent
3. Internal alert posted to ticket
4. Operations team notified to call supplier

### 7. Database (`src/database/models.py`)

**Schema:**

**ProcessedEmail**
- Tracks processed Gmail messages
- Prevents duplicate processing
- Links to tickets

**TicketState**
- Maintains ticket context
- Stores conversation summary
- Tracks escalation status
- Current state/action

**Supplier**
- Supplier contact information
- Flexible contact fields (JSON)
- Default email + purpose-specific

**SupplierMessage**
- Tracks supplier communications
- Response timing
- Reminder status

**AIDecisionLog**
- Audit trail of AI decisions
- Confidence scores
- Human feedback (Phase 1)

### 8. Main Orchestrator (`src/orchestrator.py`)

**Responsibilities:**
- Coordinates entire workflow
- Main processing loop
- Error handling and recovery
- Manages database transactions
- Integrates all components

**Processing Workflow:**
```
1. Poll Gmail for new emails
2. For each email:
   a. Check if already processed (idempotency)
   b. Extract order number
   c. Get/create ticket via API
   d. Build context from ticket history
   e. AI analysis
   f. Update ticket state in DB
   g. Dispatch action (based on phase)
   h. Handle supplier communication
   i. Mark email as processed
   j. Label in Gmail
3. Check supplier reminders
4. Sleep until next poll
```

**Key Methods:**
- `run_forever()` - Main loop
- `process_new_emails()` - Email processing
- `_process_single_email()` - Single email workflow
- `check_supplier_reminders()` - Reminder check

## Data Flow

### Example: Customer Sends Tracking Inquiry

```
1. Customer sends email: "Wo ist meine Bestellung 123-4567890-1234567?"

2. Gmail Monitor:
   - Fetches email
   - Extracts: subject, body, sender, date
   - Identifies order number: 123-4567890-1234567

3. Orchestrator:
   - Checks ProcessedEmail table (not found)
   - Calls Ticketing API to get ticket

4. Ticketing API Client:
   - GET /tickets/GetTicketsByAmazonOrderNumber?amazonOrderNumber=123-4567890-1234567
   - Returns ticket data with history

5. AI Engine:
   - Language Detector: German (de-DE)
   - Builds prompt with ticket context
   - Calls OpenAI/Anthropic/Gemini
   - Receives analysis:
     * Intent: tracking_inquiry
     * Confidence: 0.88
     * Customer response: German text with tracking info
     * Supplier action: request_tracking if not available

6. Orchestrator:
   - Updates TicketState in database
   - Creates AIDecisionLog entry

7. Action Dispatcher:
   - Phase 1: Posts internal note with suggestion
   - Phase 2: Sends actual email to customer
             Sends email to supplier if needed

8. Supplier Manager (if supplier contacted):
   - Records SupplierMessage with timestamp
   - Will check in 24h for response

9. Orchestrator:
   - Creates ProcessedEmail entry
   - Marks Gmail message with label
   - Commits transaction

10. Customer receives response in German
```

## Security Considerations

### Credentials Management
- `.env` file for configuration (never committed)
- OAuth tokens stored locally
- API keys in environment variables
- File permissions: 600 for sensitive files

### Data Protection
- Customer PII in database
- Email content stored
- Audit trail maintained
- GDPR considerations for EU customers

### API Security
- Bearer token authentication
- Automatic token refresh
- HTTPS for all communications
- Rate limiting respected

## Scalability

### Current Design (Single Instance)
- SQLite database
- Polling-based email check
- Synchronous processing
- Suitable for: 10-100 emails/day

### Scaling Options

**Medium Scale (100-1000 emails/day):**
- Switch to PostgreSQL
- Increase poll frequency
- Add database indexing
- Use connection pooling

**Large Scale (1000+ emails/day):**
- Message queue (RabbitMQ/Redis)
- Multiple worker instances
- Async/await processing
- Distributed database
- Load balancer
- Caching layer (Redis)

## Error Handling

### Retry Logic
- Exponential backoff for API calls
- 3 retries for transient failures
- Logged errors with context

### Failure Modes

**Gmail API Failure:**
- Logs error
- Continues to next poll
- Emails remain unprocessed

**Ticketing API Failure:**
- Retries with backoff
- Email not marked as processed
- Will retry next cycle

**AI API Failure:**
- Falls back to escalation
- Posts internal note
- Human takes over

**Database Failure:**
- Transaction rollback
- Email not marked processed
- Will retry next cycle

## Monitoring and Observability

### Logging
- Structured logging (JSON format)
- Log levels: DEBUG, INFO, WARNING, ERROR
- Rotation: 7 days retention
- Locations: logs/support_agent.log

### Metrics to Track
- Emails processed per hour
- AI confidence scores (average)
- Escalation rate
- Supplier response times
- API latencies
- Error rates

### Database Queries for Monitoring
```sql
-- Escalation rate
SELECT
  COUNT(CASE WHEN escalated = 1 THEN 1 END) * 100.0 / COUNT(*) as escalation_rate
FROM ticket_states
WHERE created_at > datetime('now', '-7 days');

-- Average confidence
SELECT AVG(confidence_score)
FROM ai_decision_logs
WHERE created_at > datetime('now', '-7 days');

-- Pending supplier responses
SELECT COUNT(*)
FROM supplier_messages
WHERE response_received = 0
  AND sent_at < datetime('now', '-24 hours');
```

## Testing Strategy

### Unit Tests
- Component isolation
- Mock external APIs
- Test edge cases

### Integration Tests
- End-to-end workflow
- Database transactions
- API interactions

### Manual Testing
- Phase 1 validation
- Language detection accuracy
- Response quality review

## Future Enhancements

### Phase 3+ Features
- Web UI for operators
- Advanced analytics dashboard
- Machine learning feedback loop
- Automatic ticket classification training
- Customer sentiment analysis
- Predictive issue detection

### Technical Improvements
- Webhook-based email processing (vs polling)
- Async architecture
- GraphQL API for frontend
- Real-time notifications (WebSockets)
- Advanced caching strategies

## Dependencies

### Python Packages
- **requests**: HTTP API calls
- **google-auth**: Gmail authentication
- **google-api-python-client**: Gmail API
- **openai/anthropic**: AI providers
- **sqlalchemy**: Database ORM
- **langdetect**: Language detection
- **tenacity**: Retry logic
- **structlog**: Structured logging
- **pydantic**: Configuration validation

### External Services
- Gmail API (email monitoring)
- Ticketing API (ticket management)
- OpenAI/Anthropic/Gemini (AI analysis)

## Deployment Options

1. **Ubuntu VPS** (Recommended)
   - SystemD service
   - Direct Python execution
   - Easy debugging

2. **Docker**
   - Containerized deployment
   - Docker Compose
   - Easy replication

3. **Cloud Services**
   - AWS EC2 / Lambda
   - Google Cloud Run
   - Azure Container Instances

## Performance Characteristics

### Response Times
- Email detection: <1s
- Ticket API lookup: 1-2s
- AI analysis: 3-10s (depends on provider)
- Action dispatch: 1-2s
- Total per email: 5-15s

### Resource Usage
- RAM: 200-400MB
- CPU: Low (idle), High during AI calls
- Disk: Minimal (database growth ~1MB/1000 tickets)
- Network: ~100KB per email processed

## Conclusion

The AI Support Agent is a modular, extensible system designed for reliability and gradual deployment. Its phased approach allows for validation and refinement before full automation, ensuring customer satisfaction while reducing operational costs.
