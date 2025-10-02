# Changelog

All notable changes to the AI Customer Support Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 2025-10-02

### Fixed
- **Configuration Loading**: Fixed Pydantic validation error when loading environment variables
  - Changed `deployment_phase` from `Literal[1, 2, 3]` to `int` with custom validation
  - Added `@field_validator` for automatic type conversion of integers from env vars
  - Added `@field_validator` for automatic type conversion of floats from env vars
  - Updated validator syntax from deprecated `@validator` to new `@field_validator` (Pydantic 2.x)
  - Relaxed AI provider validation to allow configuration loading during setup

### Added
- `test_config.py` - Configuration validation test script
- `troubleshoot.sh` - Comprehensive troubleshooting helper script
- `BUGFIXES.md` - Detailed documentation of bug fixes
- `DEPLOYMENT_UPDATE.md` - Server update instructions
- `UPDATE_SUMMARY.txt` - Quick reference for the update
- `CHANGELOG.md` - This file

### Changed
- `config/settings.py` - Updated Pydantic validators for better type handling
- `.env.example` - Added clarifying comment about numeric values
- `README.md` - Added version information section
- `INDEX.md` - Updated with new files and version info

### Technical Details
- **Issue**: Environment variables loaded as strings, Pydantic expected specific types
- **Root Cause**: `python-dotenv` loads all values as strings, Pydantic 2.x `Literal` types are strict
- **Solution**: Custom validators that convert strings to appropriate types before validation
- **Impact**: No changes needed to existing `.env` files, fully backward compatible

## [1.0.0] - 2025-10-02

### Added
- Initial release of AI Customer Support Agent
- Email monitoring via Gmail API with OAuth2 authentication
- Ticketing system integration with full API support
- AI-powered email analysis (OpenAI, Anthropic, Gemini support)
- Multi-language support (8+ languages with automatic detection)
- Phased deployment system (Shadow → Partial → Full automation)
- Supplier management with automated 24-hour reminders
- SQLite database for state management and audit trail
- Comprehensive error handling and retry logic
- Idempotent email processing (no duplicates)
- Confidence-based escalation workflow
- Complete documentation suite:
  - README.md - Complete user guide
  - GETTING_STARTED.md - Quick start guide
  - SETUP_GUIDE.md - Production deployment guide
  - ARCHITECTURE.md - Technical architecture
  - PROJECT_SUMMARY.md - Project overview
  - INDEX.md - Documentation hub
- Deployment configurations:
  - Docker support (Dockerfile, docker-compose.yml)
  - SystemD service file
  - Direct Python execution
- Utility scripts:
  - `main.py` - Application entry point
  - `manage_suppliers.py` - Supplier management CLI
  - `quickstart.sh` - Setup automation
  - `verify_setup.py` - Setup verification
- Test suite with basic coverage
- Production-ready logging with structlog
- Security best practices (environment variables, no hardcoded secrets)

### Core Features
- **Email Processing**
  - Gmail API integration
  - Automatic polling (configurable)
  - Order number extraction
  - Thread tracking
  - Label-based processed tracking

- **AI Analysis**
  - Intent detection (tracking, returns, complaints, etc.)
  - Confidence scoring
  - Response generation in customer's language
  - Context-aware with ticket history

- **Ticketing Integration**
  - Bearer token authentication with auto-refresh
  - Ticket lookup (by order/ticket/PO number)
  - Ticket creation/update (UpsertTicket)
  - Customer messaging
  - Supplier messaging
  - Internal notes

- **Supplier Management**
  - Contact information storage (flexible JSON fields)
  - Message tracking with timestamps
  - Automated 24-hour reminders
  - Response tracking
  - Internal alerts to operations

- **Database**
  - ProcessedEmail - Idempotency tracking
  - TicketState - Conversation context
  - Supplier - Contact information
  - SupplierMessage - Communication tracking
  - AIDecisionLog - Audit trail with confidence scores

- **Reliability**
  - Comprehensive error handling
  - Exponential backoff retry logic
  - Transaction management
  - Loop prevention
  - Graceful degradation

### Supported Languages
- German (de-DE)
- English (en-US)
- French (fr-FR)
- Spanish (es-ES)
- Italian (it-IT)
- Dutch (nl-NL)
- Polish (pl-PL)
- Portuguese (pt-PT)

### Requirements
- Python 3.11+
- Gmail account with API access
- Ticketing system API credentials
- AI provider API key (OpenAI/Anthropic/Gemini)
- Ubuntu 20.04+ (for production deployment)

### Known Issues
- Gmail OAuth requires browser access for initial authentication
- SQLite not recommended for high-volume production (use PostgreSQL)
- First-time setup requires manual Gmail credential download

---

## Legend

- **Added**: New features
- **Changed**: Changes in existing functionality
- **Deprecated**: Soon-to-be removed features
- **Removed**: Removed features
- **Fixed**: Bug fixes
- **Security**: Vulnerability fixes

---

**Current Version**: 1.0.1
**Release Date**: October 2, 2025
**Status**: Production Ready
