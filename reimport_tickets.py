#!/usr/bin/env python3
"""
One-time script to re-import tickets from the last 48 hours
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

import structlog
from config.settings import settings
from src.orchestrator import SupportAgentOrchestrator
from src.email.gmail_monitor import GmailMonitor

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer()
    ],
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger(__name__)

def main():
    """Re-import tickets from last 48 hours"""

    # Calculate 48 hours in minutes
    LOOKBACK_HOURS = 48
    lookback_minutes = LOOKBACK_HOURS * 60

    logger.info("=" * 60)
    logger.info(f"Re-importing tickets from last {LOOKBACK_HOURS} hours")
    logger.info("=" * 60)

    try:
        # Initialize Gmail monitor
        gmail_monitor = GmailMonitor()

        # Fetch messages from last 48 hours
        logger.info(f"Fetching Gmail messages from last {LOOKBACK_HOURS} hours...")
        messages = gmail_monitor.get_unprocessed_messages(
            max_results=100,  # Adjust if you expect more
            lookback_minutes=lookback_minutes
        )

        logger.info(f"Found {len(messages)} messages to process")

        if not messages:
            logger.info("No messages found. Exiting.")
            return

        # Initialize orchestrator
        orchestrator = SupportAgentOrchestrator()

        # Process each message
        processed_count = 0
        failed_count = 0

        for i, message in enumerate(messages, 1):
            # Skip None messages
            if message is None:
                failed_count += 1
                logger.warning(f"✗ Skipping None message {i}/{len(messages)}")
                continue

            gmail_id = message.get('id', 'unknown')
            subject = message.get('subject', '(no subject)')
            if subject:
                subject = subject[:50]

            logger.info(
                f"Processing message {i}/{len(messages)}",
                gmail_id=gmail_id,
                subject=subject
            )

            try:
                # Process the email using the internal method
                success = orchestrator._process_single_email(message)
                if success:
                    processed_count += 1
                    logger.info(f"✓ Successfully processed message {i}/{len(messages)}")
                else:
                    failed_count += 1
                    logger.warning(f"✗ Failed to process message {i}/{len(messages)}")
            except Exception as e:
                failed_count += 1
                logger.error(
                    f"✗ Error processing message {i}/{len(messages)}",
                    error=str(e),
                    exc_info=True
                )

        # Summary
        logger.info("=" * 60)
        logger.info("Re-import complete!")
        logger.info(f"Total messages: {len(messages)}")
        logger.info(f"Successfully processed: {processed_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info("=" * 60)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Fatal error during re-import", error=str(e), exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    main()
