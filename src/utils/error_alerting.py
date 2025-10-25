"""
Error Alerting Module
Sends notifications for critical errors and system issues
"""
import smtplib
import structlog
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from collections import defaultdict
import threading

logger = structlog.get_logger(__name__)


class ErrorAlerting:
    """Manages error alerts and notifications"""

    def __init__(self, alert_email: str, gmail_sender=None, rate_limit_minutes: int = 30):
        """
        Initialize error alerting

        Args:
            alert_email: Email address to send alerts to
            gmail_sender: GmailSender instance for sending alerts
            rate_limit_minutes: Minimum minutes between alerts of same type
        """
        self.alert_email = alert_email
        self.gmail_sender = gmail_sender
        self.rate_limit_minutes = rate_limit_minutes

        # Track last alert time by error type to prevent spam
        self.last_alert_time: Dict[str, datetime] = {}
        self.alert_lock = threading.Lock()

        # Track error counts for threshold-based alerts
        self.error_counts: Dict[str, int] = defaultdict(int)
        self.error_count_reset_time: Dict[str, datetime] = {}

        logger.info("Error alerting initialized", alert_email=alert_email)

    def should_send_alert(self, error_type: str) -> bool:
        """
        Check if enough time has passed to send another alert of this type

        Args:
            error_type: Type of error (e.g., "orchestrator_crash", "api_failure")

        Returns:
            True if alert should be sent
        """
        with self.alert_lock:
            last_time = self.last_alert_time.get(error_type)
            if not last_time:
                return True

            time_since_last = datetime.utcnow() - last_time
            return time_since_last.total_seconds() >= (self.rate_limit_minutes * 60)

    def increment_error_count(self, error_type: str, threshold: int = 5, window_minutes: int = 60) -> bool:
        """
        Increment error count and check if threshold exceeded

        Args:
            error_type: Type of error
            threshold: Number of errors before alerting
            window_minutes: Time window for counting errors

        Returns:
            True if threshold exceeded and alert should be sent
        """
        with self.alert_lock:
            now = datetime.utcnow()

            # Reset count if window expired
            last_reset = self.error_count_reset_time.get(error_type)
            if not last_reset or (now - last_reset).total_seconds() >= (window_minutes * 60):
                self.error_counts[error_type] = 0
                self.error_count_reset_time[error_type] = now

            # Increment and check threshold
            self.error_counts[error_type] += 1

            if self.error_counts[error_type] >= threshold:
                # Reset after alerting
                self.error_counts[error_type] = 0
                self.error_count_reset_time[error_type] = now
                return True

            return False

    def send_alert(self, error_type: str, subject: str, body: str, severity: str = "ERROR") -> bool:
        """
        Send error alert email

        Args:
            error_type: Type of error for rate limiting
            subject: Email subject
            body: Email body
            severity: ERROR, WARNING, or CRITICAL

        Returns:
            True if alert sent successfully
        """
        # Check rate limit
        if not self.should_send_alert(error_type):
            logger.debug(
                "Alert rate limited",
                error_type=error_type,
                rate_limit_minutes=self.rate_limit_minutes
            )
            return False

        try:
            # Format email
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            full_subject = f"[{severity}] {subject}"
            full_body = f"""
AI Support Agent Alert
======================
Time: {timestamp}
Severity: {severity}
Error Type: {error_type}

{body}

---
This is an automated alert from the AI Support Agent orchestrator.
"""

            # Send via Gmail if available
            if self.gmail_sender:
                try:
                    self.gmail_sender.send_email(
                        to=self.alert_email,
                        subject=full_subject,
                        body=full_body
                    )

                    # Update last alert time
                    with self.alert_lock:
                        self.last_alert_time[error_type] = datetime.utcnow()

                    logger.info(
                        "Alert sent successfully",
                        error_type=error_type,
                        severity=severity,
                        to=self.alert_email
                    )
                    return True

                except Exception as e:
                    logger.error("Failed to send alert via Gmail", error=str(e))
                    return False
            else:
                logger.warning("No Gmail sender configured, cannot send alert")
                return False

        except Exception as e:
            logger.error("Failed to send alert", error=str(e), exc_info=True)
            return False

    def alert_orchestrator_crash(self, error_message: str, traceback_str: Optional[str] = None):
        """Alert when orchestrator crashes"""
        body = f"The orchestrator has crashed with the following error:\n\n{error_message}"
        if traceback_str:
            body += f"\n\nTraceback:\n{traceback_str}"

        self.send_alert(
            error_type="orchestrator_crash",
            subject="Orchestrator Crashed",
            body=body,
            severity="CRITICAL"
        )

    def alert_api_failure(self, api_name: str, error_message: str, threshold: int = 5):
        """
        Alert on repeated API failures

        Args:
            api_name: Name of API (e.g., "OpenAI", "TicketingAPI", "Gmail")
            error_message: Error details
            threshold: Number of failures before alerting
        """
        error_type = f"api_failure_{api_name.lower()}"

        # Only alert if threshold exceeded
        if self.increment_error_count(error_type, threshold=threshold, window_minutes=30):
            body = f"The {api_name} API has failed {threshold} times in the last 30 minutes.\n\n"
            body += f"Latest error:\n{error_message}\n\n"
            body += "Please check API credentials and service status."

            self.send_alert(
                error_type=error_type,
                subject=f"{api_name} API Failures",
                body=body,
                severity="ERROR"
            )

    def alert_high_rejection_rate(self, total_messages: int, rejections: int, window_hours: int = 24):
        """
        Alert when rejection rate is unusually high

        Args:
            total_messages: Total messages processed
            rejections: Number of rejections
            window_hours: Time window for calculation
        """
        if total_messages < 10:
            return  # Not enough data

        rejection_rate = rejections / total_messages

        # Alert if rejection rate exceeds 50%
        if rejection_rate > 0.5:
            body = f"High rejection rate detected in the last {window_hours} hours:\n\n"
            body += f"Total messages: {total_messages}\n"
            body += f"Rejections: {rejections}\n"
            body += f"Rejection rate: {rejection_rate:.1%}\n\n"
            body += "This may indicate issues with AI prompt quality or changing requirements."

            self.send_alert(
                error_type="high_rejection_rate",
                subject="High Message Rejection Rate",
                body=body,
                severity="WARNING"
            )

    def alert_stuck_emails(self, count: int):
        """Alert when emails are stuck in retry queue"""
        if count > 0:
            body = f"{count} email(s) are stuck in the retry queue.\n\n"
            body += "These emails have failed processing multiple times and need manual review."

            self.send_alert(
                error_type="stuck_emails",
                subject=f"{count} Emails Stuck in Retry Queue",
                body=body,
                severity="WARNING"
            )

    def alert_gmail_auth_failure(self):
        """Alert on Gmail authentication failure"""
        body = "Gmail authentication has failed.\n\n"
        body += "The orchestrator cannot access Gmail to fetch new emails.\n"
        body += "Please check:\n"
        body += "1. Gmail token is valid (config/gmail_token.json)\n"
        body += "2. Gmail credentials are correct (config/gmail_credentials.json)\n"
        body += "3. OAuth scopes are sufficient"

        self.send_alert(
            error_type="gmail_auth_failure",
            subject="Gmail Authentication Failed",
            body=body,
            severity="CRITICAL"
        )

    def alert_database_error(self, error_message: str):
        """Alert on database errors"""
        body = f"Database error occurred:\n\n{error_message}\n\n"
        body += "This may indicate database corruption or disk space issues."

        self.send_alert(
            error_type="database_error",
            subject="Database Error",
            body=body,
            severity="ERROR"
        )

    def health_check_alert(self, issues: Dict[str, Any]):
        """
        Send health check alert with multiple issues

        Args:
            issues: Dict of issue_type -> details
        """
        if not issues:
            return

        body = "Health check detected the following issues:\n\n"
        for issue_type, details in issues.items():
            body += f"- {issue_type}: {details}\n"

        self.send_alert(
            error_type="health_check",
            subject="Health Check Issues Detected",
            body=body,
            severity="WARNING"
        )
