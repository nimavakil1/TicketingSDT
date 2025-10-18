# Message Retry Scheduler

## Overview

The Message Retry Scheduler is a background service that automatically retries failed message deliveries. It runs as part of the FastAPI application and executes retry attempts every 15 minutes.

## Features

- **Automatic Retry**: Failed messages are retried up to 10 times
- **Exponential Backoff**: Wait time increases with each retry attempt
- **Human Escalation**: After 10 failed attempts, messages are escalated for manual review
- **Thread-Safe**: Runs in a background daemon thread
- **Configurable**: Retry interval and max attempts can be adjusted

## How It Works

### Retry Logic

1. Every 15 minutes, the scheduler queries the database for messages with:
   - `status = 'failed'`
   - `retry_count < 10`

2. For each failed message:
   - Check if enough time has passed since last attempt
   - Attempt to resend via `MessageService.retry_failed_message()`
   - Increment retry counter
   - Log success or failure

3. If message reaches 10 failed attempts:
   - Mark for human escalation
   - Update error message
   - Log escalation event

### Timing

- **Retry Interval**: 15 minutes between retry job runs
- **Wait Time**: Minimum wait increases with each retry:
  - 1st retry: 15 minutes after failure
  - 2nd retry: 30 minutes after creation
  - 3rd retry: 45 minutes after creation
  - etc.

## Architecture

```
FastAPI App Startup
       ↓
  start_scheduler()
       ↓
MessageRetryScheduler
       ↓
  Background Thread
       ↓
   Schedule Loop (runs every minute)
       ↓
  Retry Job (runs every 15 min)
       ↓
  Query Failed Messages
       ↓
  Call MessageService.retry_failed_message()
       ↓
  Update Status & Retry Count
       ↓
  Escalate if Max Retries Reached
```

## Usage

### Automatic Start

The scheduler starts automatically when the FastAPI application launches:

```python
# In src/api/web_api.py
@app.on_event("startup")
async def startup_event():
    ticketing_client = TicketingAPIClient(...)
    start_scheduler(ticketing_client)
```

### Manual Control

```python
from src.scheduler.message_retry_scheduler import (
    start_scheduler,
    stop_scheduler,
    get_scheduler
)

# Start scheduler
ticketing_client = TicketingAPIClient(...)
start_scheduler(ticketing_client)

# Get status
scheduler = get_scheduler()
status = scheduler.get_status()
# Returns: {
#   'running': True,
#   'retry_interval_minutes': 15,
#   'max_retries': 10,
#   'next_run': datetime(...)
# }

# Stop scheduler
stop_scheduler()
```

## API Endpoints

### Get Scheduler Status

```http
GET /api/messages/scheduler/status
Authorization: Bearer <token>
```

**Response:**
```json
{
  "running": true,
  "retry_interval_minutes": 15,
  "max_retries": 10,
  "next_run": "2025-10-18T10:15:00Z"
}
```

## Configuration

Edit `src/scheduler/message_retry_scheduler.py`:

```python
class MessageRetryScheduler:
    def __init__(self, ticketing_client):
        self.retry_interval_minutes = 15  # Change retry frequency
        self.max_retries = 10             # Change max attempts
```

## Logging

The scheduler logs all activities:

```python
logger.info("Message retry scheduler started")
logger.info("Starting failed message retry job")
logger.info(f"Found {len(failed_messages)} failed messages to retry")
logger.info(f"Message {message.id} sent successfully on retry")
logger.warning(f"Message {message.id} reached max retries")
logger.error(f"Error retrying message {message.id}: {e}")
```

View logs:
```bash
tail -f logs/app.log | grep "retry"
```

## Error Handling

### Common Errors

1. **Ticketing API unavailable**
   - Scheduler continues running
   - Retry count increments
   - Message status remains 'failed'

2. **Database connection lost**
   - Scheduler logs error
   - Waits for next scheduled run
   - Transaction rolls back

3. **Invalid message data**
   - Message skipped
   - Error logged
   - Continues with next message

### Escalation

When a message reaches max retries:

```python
message.status = 'failed'
message.last_error = (
    f"Max retries ({self.max_retries}) exceeded. "
    f"Manual intervention required."
)
```

Admins can:
1. View failed message in UI at `/messages`
2. Edit message content if needed
3. Manually retry via "Retry" button
4. Or reject the message with reason

## Monitoring

### Check Scheduler Health

```bash
# API health check
curl http://localhost:8003/api/messages/scheduler/status

# Check logs
tail -100 logs/app.log | grep "scheduler"

# Count failed messages
sqlite3 ticketing_agent.db \
  "SELECT COUNT(*) FROM pending_messages WHERE status='failed'"

# Find messages near max retries
sqlite3 ticketing_agent.db \
  "SELECT id, retry_count, last_error
   FROM pending_messages
   WHERE status='failed' AND retry_count >= 8"
```

### Metrics

The scheduler logs metrics that can be parsed:

```
METRIC: message_escalated ticket_id=12345 message_type=supplier retry_count=10
```

## Performance

- **Memory**: ~10 MB (background thread)
- **CPU**: Negligible (runs every 15 min)
- **Database Impact**: One query every 15 minutes + updates per failed message

## Testing

### Manual Test

```python
from src.database.models import PendingMessage, get_session
from src.scheduler.message_retry_scheduler import MessageRetryScheduler
from src.api.ticketing_client import TicketingAPIClient

# Create test failed message
session = next(get_session())
message = PendingMessage(
    ticket_id=1,
    message_type='customer',
    status='failed',
    retry_count=0,
    subject='Test',
    body='Test message'
)
session.add(message)
session.commit()

# Start scheduler
ticketing_client = TicketingAPIClient(...)
scheduler = MessageRetryScheduler(ticketing_client)
scheduler.start()

# Wait and check
import time
time.sleep(60)
session.refresh(message)
print(f"Retry count: {message.retry_count}")
print(f"Status: {message.status}")

# Cleanup
scheduler.stop()
```

## Troubleshooting

### Scheduler Not Starting

**Problem**: Scheduler doesn't start on app launch

**Solution**:
```bash
# Check logs
tail -100 logs/app.log | grep "scheduler"

# Verify ticketing client config
python3 -c "from config.settings import settings; print(settings.ticketing_api_base_url)"
```

### Messages Not Retrying

**Problem**: Failed messages remain in queue

**Solutions**:
1. Check scheduler is running: `GET /api/messages/scheduler/status`
2. Verify message is eligible: `retry_count < 10` and `status = 'failed'`
3. Check logs for errors during retry attempts
4. Verify ticketing API is accessible

### High Retry Count

**Problem**: Messages failing repeatedly

**Root Causes**:
- Ticketing API down/unreachable
- Invalid authentication credentials
- Malformed message data
- Network issues

**Investigation**:
```bash
# Check last errors
sqlite3 ticketing_agent.db \
  "SELECT id, retry_count, last_error
   FROM pending_messages
   WHERE status='failed'
   ORDER BY retry_count DESC
   LIMIT 10"
```

## Future Enhancements

- [ ] Exponential backoff instead of fixed 15-min intervals
- [ ] Configurable retry schedule per message type
- [ ] Email/Slack notifications for escalations
- [ ] Retry statistics dashboard
- [ ] Pause/resume scheduler via API
- [ ] Custom retry strategies (immediate retry for transient errors)
