"""
Gmail Sender Module
Sends emails through Gmail API with attachment support
"""
import os
import base64
import mimetypes
from typing import List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import structlog

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings

logger = structlog.get_logger(__name__)

# Gmail API scopes - need send permission
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
]


class GmailSender:
    """Sends emails through Gmail API"""

    def __init__(self):
        self.service = None
        self._authenticate()

    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2"""
        creds = None
        token_path = settings.gmail_token_path
        credentials_path = settings.gmail_credentials_path

        # Load existing token
        if os.path.exists(token_path):
            try:
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
                logger.info("Loaded existing Gmail credentials for sender")
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
                        f"Gmail credentials file not found at {credentials_path}"
                    )

                logger.info("Starting OAuth2 flow for Gmail authentication")
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
                logger.info("Saved Gmail credentials")

        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail sender authenticated successfully")

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[str]] = None,
        reply_to_message_id: Optional[str] = None,
        thread_id: Optional[str] = None
    ) -> dict:
        """
        Send an email through Gmail API

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            cc: List of CC email addresses
            attachments: List of file paths to attach
            reply_to_message_id: Gmail message ID to reply to (for threading)
            thread_id: Gmail thread ID (for threading)

        Returns:
            dict: Gmail API response with message ID
        """
        try:
            # Create message
            message = MIMEMultipart()
            message['To'] = to
            message['Subject'] = subject

            if cc:
                message['Cc'] = ', '.join(cc)

            # Add threading headers if replying
            if reply_to_message_id:
                message['In-Reply-To'] = reply_to_message_id
                message['References'] = reply_to_message_id

            # Attach body
            message.attach(MIMEText(body, 'plain'))

            # Add attachments
            if attachments:
                for file_path in attachments:
                    if not os.path.exists(file_path):
                        logger.warning("Attachment file not found", file_path=file_path)
                        continue

                    # Guess content type
                    content_type, _ = mimetypes.guess_type(file_path)
                    if content_type is None:
                        content_type = 'application/octet-stream'

                    main_type, sub_type = content_type.split('/', 1)

                    with open(file_path, 'rb') as f:
                        part = MIMEBase(main_type, sub_type)
                        part.set_payload(f.read())

                    encoders.encode_base64(part)
                    filename = os.path.basename(file_path)
                    part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
                    message.attach(part)

                    logger.info("Attached file", filename=filename)

            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')

            # Prepare send request
            send_request = {'raw': raw_message}
            if thread_id:
                send_request['threadId'] = thread_id

            # Send message
            result = self.service.users().messages().send(
                userId='me',
                body=send_request
            ).execute()

            logger.info(
                "Email sent successfully",
                message_id=result['id'],
                to=to,
                subject=subject,
                has_attachments=bool(attachments),
                attachment_count=len(attachments) if attachments else 0
            )

            return result

        except HttpError as e:
            logger.error("Gmail API error", error=str(e))
            raise
        except Exception as e:
            logger.error("Failed to send email", error=str(e))
            raise
