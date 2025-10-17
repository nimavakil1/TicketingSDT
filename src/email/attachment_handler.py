"""
Attachment Handler
Manages downloading, storing, and processing email attachments from Gmail
"""
import os
import base64
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import structlog
import mimetypes

logger = structlog.get_logger(__name__)


class AttachmentHandler:
    """Handle email attachments - download, store, and extract text"""

    def __init__(self, storage_dir: str = "attachments"):
        """
        Initialize attachment handler

        Args:
            storage_dir: Directory to store downloaded attachments
        """
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Attachment handler initialized", storage_dir=str(self.storage_dir))

    def extract_attachments(self, gmail_service, message_id: str, payload: Dict) -> List[Dict]:
        """
        Extract attachments from Gmail message payload

        Args:
            gmail_service: Gmail API service object
            message_id: Gmail message ID
            payload: Message payload from Gmail API

        Returns:
            List of attachment info dictionaries
        """
        attachments = []

        def process_part(part: Dict):
            """Recursively process message parts"""
            filename = part.get('filename', '')
            mime_type = part.get('mimeType', '')

            # Check if this part has an attachment
            if filename and part.get('body', {}).get('attachmentId'):
                attachment_id = part['body']['attachmentId']
                size = part['body'].get('size', 0)

                attachments.append({
                    'filename': filename,
                    'mime_type': mime_type,
                    'attachment_id': attachment_id,
                    'size': size,
                    'message_id': message_id
                })
                logger.debug("Found attachment", filename=filename, mime_type=mime_type, size=size)

            # Process nested parts (multipart messages)
            if 'parts' in part:
                for subpart in part['parts']:
                    process_part(subpart)

        # Start processing from root payload
        if 'parts' in payload:
            for part in payload['parts']:
                process_part(part)
        else:
            # Single part message - check if it's an attachment
            process_part(payload)

        logger.info("Extracted attachments from message",
                   message_id=message_id,
                   attachment_count=len(attachments))
        return attachments

    def download_attachment(
        self,
        gmail_service,
        message_id: str,
        attachment_id: str,
        filename: str,
        subfolder: Optional[str] = None
    ) -> Optional[str]:
        """
        Download an attachment from Gmail and save to disk

        Args:
            gmail_service: Gmail API service object
            message_id: Gmail message ID
            attachment_id: Attachment ID from Gmail
            filename: Original filename
            subfolder: Optional subfolder (e.g., ticket number)

        Returns:
            Path to downloaded file, or None if failed
        """
        try:
            # Create subfolder if specified
            save_dir = self.storage_dir
            if subfolder:
                save_dir = self.storage_dir / subfolder
                save_dir.mkdir(parents=True, exist_ok=True)

            # Get attachment data from Gmail
            attachment = gmail_service.users().messages().attachments().get(
                userId='me',
                messageId=message_id,
                id=attachment_id
            ).execute()

            file_data = base64.urlsafe_b64decode(attachment['data'])

            # Save to file
            file_path = save_dir / filename
            with open(file_path, 'wb') as f:
                f.write(file_data)

            logger.info("Downloaded attachment",
                       filename=filename,
                       file_path=str(file_path),
                       size=len(file_data))
            return str(file_path)

        except Exception as e:
            logger.error("Failed to download attachment",
                        message_id=message_id,
                        attachment_id=attachment_id,
                        filename=filename,
                        error=str(e))
            return None

    def download_all_attachments(
        self,
        gmail_service,
        message_id: str,
        payload: Dict,
        subfolder: Optional[str] = None
    ) -> List[str]:
        """
        Extract and download all attachments from a message

        Args:
            gmail_service: Gmail API service object
            message_id: Gmail message ID
            payload: Message payload
            subfolder: Optional subfolder for organizing files

        Returns:
            List of paths to downloaded files
        """
        attachments = self.extract_attachments(gmail_service, message_id, payload)
        downloaded_files = []

        for attachment in attachments:
            file_path = self.download_attachment(
                gmail_service,
                message_id,
                attachment['attachment_id'],
                attachment['filename'],
                subfolder
            )
            if file_path:
                downloaded_files.append(file_path)

        logger.info("Downloaded all attachments",
                   message_id=message_id,
                   total_count=len(attachments),
                   downloaded_count=len(downloaded_files))
        return downloaded_files

    def is_text_extractable(self, file_path: str) -> bool:
        """
        Check if text can be extracted from this file type

        Args:
            file_path: Path to file

        Returns:
            True if text extraction is supported
        """
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            return False

        extractable_types = [
            'application/pdf',
            'image/jpeg',
            'image/jpg',
            'image/png',
            'image/tiff',
            'image/bmp',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',  # docx
            'application/msword',  # doc
            'text/plain'
        ]

        return mime_type in extractable_types

    def cleanup_old_attachments(self, days: int = 7) -> int:
        """
        Clean up attachments older than specified days

        Args:
            days: Delete files older than this many days

        Returns:
            Number of files deleted
        """
        import time
        deleted_count = 0
        cutoff_time = time.time() - (days * 86400)

        try:
            for root, dirs, files in os.walk(self.storage_dir):
                for file in files:
                    file_path = Path(root) / file
                    if file_path.stat().st_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            deleted_count += 1
                        except Exception as e:
                            logger.warning("Failed to delete old attachment",
                                         file_path=str(file_path),
                                         error=str(e))

            logger.info("Cleaned up old attachments", deleted_count=deleted_count, days=days)
            return deleted_count

        except Exception as e:
            logger.error("Failed to cleanup old attachments", error=str(e))
            return 0
