"""
Gmail Monitor Module
Monitors Gmail inbox for new support emails and processes them
"""
import os
import base64
import re
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import structlog

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings

logger = structlog.get_logger(__name__)

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.labels'
]


class GmailMonitor:
    """Monitors Gmail inbox for new support emails"""

    def __init__(self):
        self.service = None
        self.processed_label_id = None
        self.start_after_epoch: Optional[int] = self._parse_start_at(settings.gmail_start_at)
        self._authenticate()
        self._ensure_processed_label()

    def _parse_start_at(self, value: Optional[str]) -> Optional[int]:
        """Parse start-at setting into epoch seconds for Gmail query.

        Accepts either an ISO8601 datetime (e.g. 2025-10-03T08:00:00+00:00)
        or a string of digits representing epoch seconds.
        Returns None if parsing fails or value is falsy.
        """
        if not value:
            return None
        try:
            v = str(value).strip()
            if v.isdigit():
                return int(v)
            # Normalize trailing Z to +00:00 and parse
            if v.endswith("Z"):
                v = v[:-1] + "+00:00"
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception as e:
            logger.warning("Invalid gmail_start_at; ignoring", value=str(value), error=str(e))
            return None

    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2"""
        creds = None
        token_path = settings.gmail_token_path
        credentials_path = settings.gmail_credentials_path

        # Load existing token
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info("Loaded existing Gmail credentials")
            except Exception as e:
                logger.warning("Failed to load existing credentials", error=str(e))

        # Refresh or obtain new credentials
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    logger.info("Refreshing Gmail credentials")
                    creds.refresh(Request())
                except Exception as e:
                    logger.error("Failed to refresh credentials", error=str(e))
                    creds = None

            if not creds:
                if not os.path.exists(credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {credentials_path}. "
                        "Please download OAuth2 credentials from Google Cloud Console."
                    )

                logger.info("Starting OAuth2 flow for Gmail authentication")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
            logger.info("Saved Gmail credentials")

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail API client initialized")

    def _ensure_processed_label(self) -> None:
        """Ensure the processed label exists, create if it doesn't"""
        try:
            # List existing labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            # Look for our processed label
            for label in labels:
                if label['name'] == settings.gmail_processed_label:
                    self.processed_label_id = label['id']
                    logger.info(
                        "Found existing processed label",
                        label_id=self.processed_label_id
                    )
                    return

            # Create the label if it doesn't exist
            logger.info("Creating processed label", label_name=settings.gmail_processed_label)
            label_object = {
                'name': settings.gmail_processed_label,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            self.processed_label_id = created_label['id']
            logger.info("Created processed label", label_id=self.processed_label_id)

        except HttpError as e:
            logger.error("Failed to ensure processed label exists", error=str(e))
            raise

    def get_unprocessed_messages(self, max_results: Optional[int] = None, lookback_minutes: int = 10) -> List[Dict]:
        """
        Fetch messages from the inbox within the lookback window.

        Instead of relying on labels, we query based on time (last X minutes).
        The orchestrator will check the database to determine if each email
        has been successfully processed.

        Args:
            max_results: Maximum number of messages to fetch
            lookback_minutes: How many minutes back to search (default: 10)

        Returns:
            List of message dictionaries with full content
        """
        try:
            # Calculate time threshold - look back X minutes from now
            from datetime import datetime, timedelta, timezone
            lookback_time = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
            lookback_epoch = int(lookback_time.timestamp())

            # Use the configured start_after_epoch as a hard minimum if set
            if self.start_after_epoch and lookback_epoch < self.start_after_epoch:
                lookback_epoch = self.start_after_epoch

            # Build query: all messages in inbox from the last X minutes
            # Note: We intentionally don't filter by label here
            query_parts = [
                'in:inbox',
                f'after:{lookback_epoch}'
            ]
            query = " ".join(query_parts)

            logger.info("Fetching messages from lookback window",
                       query=query,
                       lookback_minutes=lookback_minutes)

            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=(max_results or settings.gmail_max_results)
            ).execute()

            messages = results.get('messages', [])

            if not messages:
                logger.debug("No messages found in lookback window")
                return []

            logger.info("Found messages in lookback window", count=len(messages))

            # Fetch full message details
            full_messages = []
            for msg in messages:
                try:
                    full_msg = self._get_message_details(msg['id'])
                    if full_msg:
                        full_messages.append(full_msg)
                except Exception as e:
                    logger.error(
                        "Failed to fetch message details",
                        message_id=msg['id'],
                        error=str(e)
                    )
                    continue

            return full_messages

        except HttpError as e:
            logger.error("Failed to fetch messages", error=str(e))
            raise

    def _get_message_details(self, message_id: str) -> Optional[Dict]:
        """
        Get full details of a specific message

        Args:
            message_id: Gmail message ID

        Returns:
            Dictionary with message details
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            # Extract headers
            headers = message['payload']['headers']
            subject = self._get_header(headers, 'Subject')
            from_address = self._get_header(headers, 'From')
            to_address = self._get_header(headers, 'To')
            date_str = self._get_header(headers, 'Date')
            message_id_header = self._get_header(headers, 'Message-ID')

            # Parse date
            try:
                date = parsedate_to_datetime(date_str) if date_str else datetime.now()
            except Exception:
                date = datetime.now()

            # Extract body
            body = self._extract_body(message['payload'])

            # Extract thread ID
            thread_id = message.get('threadId')

            # Get snippet (preview)
            snippet = message.get('snippet', '')

            # Extract and download attachments
            attachments = []
            attachment_texts = []
            try:
                from src.email.attachment_handler import AttachmentHandler
                from src.email.text_extractor import TextExtractor

                attachment_handler = AttachmentHandler()
                text_extractor = TextExtractor()

                # Download attachments
                attachment_files = attachment_handler.download_all_attachments(
                    self.service,
                    message_id,
                    message['payload'],
                    subfolder=message_id  # Organize by message ID
                )
                attachments = attachment_files

                # Extract text from attachments
                for file_path in attachment_files:
                    if attachment_handler.is_text_extractable(file_path):
                        text = text_extractor.extract_text(file_path)
                        if text:
                            attachment_texts.append({
                                'filename': os.path.basename(file_path),
                                'text': text
                            })

                logger.info("Processed attachments",
                           message_id=message_id,
                           attachment_count=len(attachments),
                           extracted_text_count=len(attachment_texts))

            except Exception as e:
                logger.warning("Failed to process attachments",
                             message_id=message_id,
                             error=str(e))

            result = {
                'id': message_id,
                'thread_id': thread_id,
                'message_id_header': message_id_header,
                'subject': subject,
                'from': from_address,
                'to': to_address,
                'date': date,
                'body': body,
                'snippet': snippet,
                'label_ids': message.get('labelIds', []),
                'attachments': attachments,
                'attachment_texts': attachment_texts
            }

            logger.debug(
                "Extracted message details",
                message_id=message_id,
                subject=subject,
                from_addr=from_address,
                has_attachments=len(attachments) > 0
            )

            return result

        except HttpError as e:
            logger.error("Failed to get message details", message_id=message_id, error=str(e))
            return None

    def _get_header(self, headers: List[Dict], name: str) -> Optional[str]:
        """Extract a specific header value from headers list"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None

    def _extract_body(self, payload: Dict) -> str:
        """
        Extract email body from message payload
        Handles both plain text and HTML, multipart messages
        """
        body = ""

        if 'body' in payload and 'data' in payload['body']:
            # Simple message with body directly in payload
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')

        elif 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        # Use HTML if plain text not available
                        html_body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                        # Simple HTML stripping (for production, use html2text or beautifulsoup)
                        body = re.sub('<[^<]+?>', '', html_body)
                elif 'parts' in part:
                    # Nested parts
                    body = self._extract_body(part)
                    if body:
                        break

        return body.strip()

    def mark_as_processed(self, message_id: str) -> bool:
        """
        Mark a message as processed by adding the processed label

        Args:
            message_id: Gmail message ID

        Returns:
            True if successful, False otherwise
        """
        # Skip marking for manual imports
        if message_id == 'manual_import':
            logger.debug("Skipping Gmail marking for manual import")
            return True

        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [self.processed_label_id]}
            ).execute()

            logger.info("Marked message as processed", message_id=message_id)
            return True

        except HttpError as e:
            logger.error(
                "Failed to mark message as processed",
                message_id=message_id,
                error=str(e)
            )
            return False

    def extract_order_number(self, text: str) -> Optional[str]:
        """
        Extract Amazon order number from email text

        Amazon order numbers typically follow patterns like:
        - 123-1234567-1234567 (standard format)
        - Order #123-1234567-1234567
        - Order ID: 123-1234567-1234567

        Args:
            text: Email subject or body text

        Returns:
            Order number if found, None otherwise
        """
        # Amazon order number pattern
        patterns = [
            r'\b(\d{3}-\d{7}-\d{7})\b',  # Standard format
            r'Order\s*#?\s*[:=]?\s*(\d{3}-\d{7}-\d{7})',  # With "Order" prefix
            r'order\s+number\s*[:=]?\s*(\d{3}-\d{7}-\d{7})',  # With "order number"
            r'Bestellung\s*[:=]?\s*(\d{3}-\d{7}-\d{7})',  # German
            r'Commande\s*[:=]?\s*(\d{3}-\d{7}-\d{7})',  # French
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                order_number = match.group(1)
                logger.debug("Extracted order number", order_number=order_number)
                return order_number

        return None

    def extract_ticket_number(self, text: str) -> Optional[str]:
        """
        Extract ticket number from email text

        Ticket numbers follow the pattern: DE25006528 (country code + digits)

        Args:
            text: Email subject or body text

        Returns:
            Ticket number if found, None otherwise
        """
        patterns = [
            r'\b([A-Z]{2}\d{8})\b',  # Standard format
            r'Ticket\s*#?\s*[:=]?\s*([A-Z]{2}\d{8})',  # With "Ticket" prefix
            r'ticket\s+number\s*[:=]?\s*([A-Z]{2}\d{8})',  # With "ticket number"
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                ticket_number = match.group(1)
                logger.debug("Extracted ticket number", ticket_number=ticket_number)
                return ticket_number

        return None

    def extract_purchase_order_number(self, text: str) -> Optional[str]:
        """
        Extract purchase order number from email text.

        Common pattern observed: 'D' followed by 9 digits (e.g., D425123006).
        Also handle variants with prefixes like 'PO' or separators.

        Args:
            text: Email subject or body text

        Returns:
            Purchase order number if found, None otherwise
        """
        patterns = [
            r"\b(D\d{9})\b",                 # Plain D#########
            r"PO\s*[:#-]?\s*(D\d{9})",       # With 'PO' prefix
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                po = match.group(1).upper()
                logger.debug("Extracted purchase order", purchase_order=po)
                return po

        return None

    def parse_sender_info(self, from_field: str) -> Tuple[str, str]:
        """
        Parse sender name and email from 'From' header

        Args:
            from_field: From header value (e.g., "John Doe <john@example.com>")

        Returns:
            Tuple of (name, email)
        """
        # Pattern: "Name" <email@domain.com> or just email@domain.com
        match = re.match(r'^"?([^"<]+)"?\s*<([^>]+)>$', from_field)
        if match:
            name = match.group(1).strip()
            email = match.group(2).strip()
            return name, email

        # Just an email address
        match = re.match(r'^([^<>\s]+@[^<>\s]+)$', from_field)
        if match:
            email = match.group(1).strip()
            return email, email

        # Fallback
        return from_field, from_field
