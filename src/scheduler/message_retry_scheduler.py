"""
Background scheduler for retrying failed messages
Runs every 15 minutes to retry messages that failed to send
"""

import logging
import schedule
import time
import threading
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from src.database.models import PendingMessage, get_session
from src.utils.message_service import MessageService
from src.api.ticketing_client import TicketingAPIClient
from config.settings import settings

logger = logging.getLogger(__name__)


class MessageRetryScheduler:
    """Scheduler for retrying failed message deliveries"""

    def __init__(self, ticketing_client: TicketingAPIClient):
        """
        Initialize the retry scheduler

        Args:
            ticketing_client: Client for sending messages via ticketing API
        """
        self.ticketing_client = ticketing_client
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.retry_interval_minutes = 15
        self.max_retries = 10
        logger.info("MessageRetryScheduler initialized")

    def start(self):
        """Start the background scheduler"""
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True

        # Schedule the retry job to run every 15 minutes
        schedule.every(self.retry_interval_minutes).minutes.do(self._retry_failed_messages)

        # Run once immediately on startup
        self._retry_failed_messages()

        # Start background thread
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()

        logger.info(f"Message retry scheduler started (interval: {self.retry_interval_minutes} min)")

    def stop(self):
        """Stop the background scheduler"""
        self.running = False
        schedule.clear()

        if self.thread:
            self.thread.join(timeout=5)

        logger.info("Message retry scheduler stopped")

    def _run_scheduler(self):
        """Run the scheduler loop in background thread"""
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}", exc_info=True)
                time.sleep(60)

    def _retry_failed_messages(self):
        """Retry all failed messages that haven't exceeded max retries"""
        logger.info("Starting failed message retry job")

        session = next(get_session())
        try:
            # Find failed messages eligible for retry
            failed_messages = session.query(PendingMessage).filter(
                PendingMessage.status == 'failed',
                PendingMessage.retry_count < self.max_retries
            ).all()

            if not failed_messages:
                logger.info("No failed messages to retry")
                return

            logger.info(f"Found {len(failed_messages)} failed messages to retry")

            message_service = MessageService(session, self.ticketing_client)
            retry_count = 0
            success_count = 0
            escalation_count = 0

            for message in failed_messages:
                try:
                    # Check if enough time has passed since last attempt (15 minutes)
                    if message.created_at:
                        time_since_creation = datetime.utcnow() - message.created_at
                        min_wait = timedelta(minutes=self.retry_interval_minutes * message.retry_count)

                        if time_since_creation < min_wait:
                            logger.debug(
                                f"Message {message.id} not ready for retry yet "
                                f"(waited {time_since_creation}, need {min_wait})"
                            )
                            continue

                    # Attempt retry
                    logger.info(
                        f"Retrying message {message.id} (attempt {message.retry_count + 1}/{self.max_retries})"
                    )

                    success = message_service.retry_failed_message(message.id)
                    retry_count += 1

                    if success:
                        success_count += 1
                        logger.info(f"Message {message.id} sent successfully on retry")
                    else:
                        # Check if max retries reached
                        message.refresh_from_db = session.query(PendingMessage).get(message.id)
                        if message.refresh_from_db and message.refresh_from_db.retry_count >= self.max_retries:
                            escalation_count += 1
                            logger.warning(
                                f"Message {message.id} reached max retries ({self.max_retries}), "
                                f"needs human intervention"
                            )
                            self._escalate_to_human(session, message)

                except Exception as e:
                    logger.error(f"Error retrying message {message.id}: {e}", exc_info=True)
                    continue

            # Commit all changes
            session.commit()

            logger.info(
                f"Retry job completed: {retry_count} attempted, "
                f"{success_count} successful, {escalation_count} escalated"
            )

        except Exception as e:
            session.rollback()
            logger.error(f"Failed message retry job failed: {e}", exc_info=True)
        finally:
            session.close()

    def _escalate_to_human(self, session: Session, message: PendingMessage):
        """
        Escalate a message to human review after max retries exceeded

        Args:
            session: Database session
            message: Message that failed max retries
        """
        try:
            # Mark message for human review
            message.status = 'failed'
            message.last_error = (
                f"Max retries ({self.max_retries}) exceeded. "
                f"Manual intervention required. "
                f"Last error: {message.last_error or 'Unknown error'}"
            )

            # TODO: Send notification to admins
            # - Could create an internal note on the ticket
            # - Could send email to support team
            # - Could create a high-priority notification in the dashboard

            logger.warning(
                f"Message {message.id} escalated to human review after "
                f"{message.retry_count} failed attempts"
            )

            # Log escalation metrics
            if hasattr(settings, 'metrics_enabled') and settings.metrics_enabled:
                logger.info(
                    f"METRIC: message_escalated ticket_id={message.ticket_id} "
                    f"message_type={message.message_type} retry_count={message.retry_count}"
                )

        except Exception as e:
            logger.error(f"Error escalating message {message.id}: {e}", exc_info=True)

    def get_status(self) -> dict:
        """
        Get current scheduler status

        Returns:
            Dictionary with scheduler status information
        """
        return {
            'running': self.running,
            'retry_interval_minutes': self.retry_interval_minutes,
            'max_retries': self.max_retries,
            'next_run': schedule.next_run() if schedule.jobs else None
        }


# Global scheduler instance
_scheduler_instance: Optional[MessageRetryScheduler] = None


def get_scheduler(ticketing_client: Optional[TicketingAPIClient] = None) -> MessageRetryScheduler:
    """
    Get or create the global scheduler instance

    Args:
        ticketing_client: Ticketing client (required on first call)

    Returns:
        MessageRetryScheduler instance
    """
    global _scheduler_instance

    if _scheduler_instance is None:
        if ticketing_client is None:
            raise ValueError("ticketing_client required to initialize scheduler")
        _scheduler_instance = MessageRetryScheduler(ticketing_client)

    return _scheduler_instance


def start_scheduler(ticketing_client: TicketingAPIClient):
    """
    Start the global message retry scheduler

    Args:
        ticketing_client: Ticketing client for sending messages
    """
    scheduler = get_scheduler(ticketing_client)
    scheduler.start()


def stop_scheduler():
    """Stop the global message retry scheduler"""
    global _scheduler_instance

    if _scheduler_instance:
        _scheduler_instance.stop()
        _scheduler_instance = None
