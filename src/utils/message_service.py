"""
Message Service Module
Handles creation, management, and sending of pending messages
"""
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
import structlog

from src.database.models import PendingMessage, TicketState, AIDecisionLog, MessageTemplate, ProcessedEmail
from src.utils.message_formatter import MessageFormatter
from src.utils.cc_manager import CCManager
from src.api.ticketing_client import TicketingAPIClient
from config.settings import settings

logger = structlog.get_logger(__name__)


class MessageService:
    """Service for managing pending messages and sending approved messages"""

    def __init__(self, db_session: Session, ticketing_client: TicketingAPIClient):
        self.db = db_session
        self.ticketing_client = ticketing_client
        self.formatter = MessageFormatter()
        self.cc_manager = CCManager()

    def create_pending_message(
        self,
        ticket_state: TicketState,
        message_type: str,
        message_body: str,
        ticket_data: Dict[str, Any],
        ai_decision_id: Optional[int] = None,
        confidence_score: Optional[float] = None,
        custom_subject: Optional[str] = None
    ) -> PendingMessage:
        """
        Create a pending message for human approval

        Args:
            ticket_state: TicketState object
            message_type: 'supplier', 'customer', or 'internal'
            message_body: AI-generated message content
            ticket_data: Full ticket data from API
            ai_decision_id: Associated AI decision ID
            confidence_score: AI confidence score (0-1)
            custom_subject: Optional custom subject line

        Returns:
            Created PendingMessage object
        """
        # Format message based on type
        if message_type == "supplier":
            subject, body = self.formatter.format_supplier_message(
                message_body=message_body,
                ticket_data=self._enrich_ticket_data(ticket_state, ticket_data),
                subject=custom_subject
            )
            # Try multiple sources for supplier email
            recipient_email = (
                ticket_state.supplier_email or
                self._get_supplier_email(ticket_data) or
                self._lookup_supplier_email_from_db(ticket_state.supplier_name)
            )

            # Update ticket_state with the found email for future use
            if recipient_email and not ticket_state.supplier_email:
                ticket_state.supplier_email = recipient_email
                self.db.commit()
                logger.info("Updated ticket with supplier email",
                           ticket_number=ticket_state.ticket_number,
                           supplier_email=recipient_email)

        elif message_type == "customer":
            subject, body = self.formatter.format_customer_message(
                message_body=message_body,
                ticket_data=self._enrich_ticket_data(ticket_state, ticket_data),
                language=ticket_state.customer_language or 'de-DE',
                subject=custom_subject
            )
            recipient_email = ticket_state.customer_email

        elif message_type == "internal":
            subject = f"AI Agent Note - Ticket {ticket_state.ticket_number}"
            body = self.formatter.format_internal_note(
                note_content=message_body,
                ticket_number=ticket_state.ticket_number
            )
            recipient_email = None

        else:
            raise ValueError(f"Invalid message type: {message_type}")

        # Get CC suggestions
        cc_addresses = self.cc_manager.suggest_cc_addresses(
            message_type=message_type,
            ticket_data=self._enrich_ticket_data(ticket_state, ticket_data),
            escalated=ticket_state.escalated
        )

        # Get attachments (images from ticket)
        attachments = self._get_attachments_for_message(ticket_data, message_type)

        # Create pending message
        pending_message = PendingMessage(
            ticket_id=ticket_state.id,
            message_type=message_type,
            recipient_email=recipient_email,
            cc_emails=cc_addresses,
            subject=subject,
            body=body,
            attachments=attachments,
            confidence_score=confidence_score,
            ai_decision_id=ai_decision_id,
            status='pending'
        )

        self.db.add(pending_message)
        self.db.commit()

        logger.info(
            "Created pending message",
            ticket_number=ticket_state.ticket_number,
            message_type=message_type,
            confidence_score=confidence_score,
            pending_message_id=pending_message.id
        )

        return pending_message

    def send_pending_message(
        self,
        pending_message_id: int,
        reviewed_by_user_id: int,
        updated_body: Optional[str] = None,
        updated_subject: Optional[str] = None,
        updated_cc: Optional[List[str]] = None,
        updated_attachments: Optional[List[str]] = None
    ) -> bool:
        """
        Send an approved pending message

        Args:
            pending_message_id: ID of pending message
            reviewed_by_user_id: User ID who approved
            updated_body: Optional updated body text
            updated_subject: Optional updated subject
            updated_cc: Optional updated CC list
            updated_attachments: Optional updated attachments

        Returns:
            True if sent successfully, False otherwise
        """
        pending_message = self.db.query(PendingMessage).get(pending_message_id)
        if not pending_message:
            logger.error("Pending message not found", pending_message_id=pending_message_id)
            return False

        if pending_message.status != 'pending':
            logger.warning(
                "Cannot send message - not in pending status",
                pending_message_id=pending_message_id,
                status=pending_message.status
            )
            return False

        # Update with human edits if provided
        if updated_body:
            pending_message.body = updated_body
        if updated_subject:
            pending_message.subject = updated_subject
        if updated_cc is not None:
            pending_message.cc_emails = updated_cc
        if updated_attachments is not None:
            pending_message.attachments = updated_attachments

        # Get ticket state
        ticket_state = pending_message.ticket

        # If this is a supplier message and email is missing or invalid, try to look it up
        if pending_message.message_type == "supplier":
            # Check if email is missing or invalid (placeholder, no @, etc.)
            email = pending_message.recipient_email
            if not email or '@' not in email or 'SUPPLIER_EMAIL_HERE' in email or 'example.com' in email:
                logger.warning("Supplier message has missing/invalid recipient email, attempting lookup",
                              pending_message_id=pending_message_id,
                              ticket_number=ticket_state.ticket_number,
                              current_email=email)

                supplier_email = self._lookup_supplier_email_from_db(ticket_state.supplier_name)
                if supplier_email:
                    pending_message.recipient_email = supplier_email
                    ticket_state.supplier_email = supplier_email
                    self.db.commit()
                    logger.info("Updated pending message with supplier email",
                               pending_message_id=pending_message_id,
                               supplier_email=supplier_email)
                else:
                    logger.error("Failed to find supplier email",
                                pending_message_id=pending_message_id,
                                supplier_name=ticket_state.supplier_name)
                    return False

        # Convert relative attachment paths to absolute paths
        absolute_attachments = None
        if pending_message.attachments:
            from pathlib import Path
            base_dir = Path(settings.attachments_dir if hasattr(settings, 'attachments_dir') else 'attachments')
            absolute_attachments = []
            for rel_path in pending_message.attachments:
                abs_path = str(base_dir / rel_path)
                absolute_attachments.append(abs_path)
                logger.debug("Converted attachment path", relative=rel_path, absolute=abs_path)

        try:
            # Send message via ticketing API
            if pending_message.message_type == "supplier":
                result = self.ticketing_client.send_message_to_supplier(
                    ticket_number=ticket_state.ticket_number,
                    message=pending_message.body,
                    ticket_status_id=ticket_state.ticket_status_id,
                    owner_id=ticket_state.owner_id,
                    email_address=pending_message.recipient_email,
                    cc_email_address=",".join(pending_message.cc_emails) if pending_message.cc_emails else None,
                    attachments=absolute_attachments,
                    db_session=self.db
                )

                # Save supplier message to database for message history
                if result.get('succeeded'):
                    import uuid
                    from datetime import timezone

                    recent_email = self.db.query(ProcessedEmail).filter(
                        ProcessedEmail.ticket_id == ticket_state.id
                    ).order_by(ProcessedEmail.processed_at.desc()).first()

                    supplier_msg = ProcessedEmail(
                        gmail_message_id=result.get('gmail_message_id', f"supplier_{ticket_state.ticket_number}_{uuid.uuid4().hex[:8]}"),
                        gmail_thread_id=result.get('gmail_thread_id') or (recent_email.gmail_thread_id if recent_email else None),
                        ticket_id=ticket_state.id,
                        order_number=ticket_state.order_number,
                        subject=pending_message.subject or f"To supplier - Ticket {ticket_state.ticket_number}",
                        from_address=settings.gmail_support_email,
                        message_body=pending_message.body,
                        success=True,
                        processed_at=datetime.now(timezone.utc)
                    )
                    self.db.add(supplier_msg)

            elif pending_message.message_type == "customer":
                result = self.ticketing_client.send_message_to_customer(
                    ticket_number=ticket_state.ticket_number,
                    message=pending_message.body,
                    ticket_status_id=ticket_state.ticket_status_id,
                    owner_id=ticket_state.owner_id,
                    email_address=pending_message.recipient_email,
                    cc_email_address=",".join(pending_message.cc_emails) if pending_message.cc_emails else None,
                    attachments=absolute_attachments,
                    db_session=self.db
                )

                # Save customer message to database for message history
                if result.get('succeeded'):
                    import uuid
                    from datetime import timezone

                    recent_email = self.db.query(ProcessedEmail).filter(
                        ProcessedEmail.ticket_id == ticket_state.id
                    ).order_by(ProcessedEmail.processed_at.desc()).first()

                    customer_msg = ProcessedEmail(
                        gmail_message_id=result.get('gmail_message_id', f"customer_{ticket_state.ticket_number}_{uuid.uuid4().hex[:8]}"),
                        gmail_thread_id=result.get('gmail_thread_id') or (recent_email.gmail_thread_id if recent_email else None),
                        ticket_id=ticket_state.id,
                        order_number=ticket_state.order_number,
                        subject=pending_message.subject or f"To customer - Ticket {ticket_state.ticket_number}",
                        from_address=settings.gmail_support_email,
                        message_body=pending_message.body,
                        success=True,
                        processed_at=datetime.now(timezone.utc)
                    )
                    self.db.add(customer_msg)

            elif pending_message.message_type == "internal":
                result = self.ticketing_client.send_internal_message(
                    ticket_number=ticket_state.ticket_number,
                    message=pending_message.body,
                    ticket_status_id=ticket_state.ticket_status_id,
                    owner_id=ticket_state.owner_id,
                    attachments=absolute_attachments
                )

                # Save internal message to database for message history
                if result.get('succeeded'):
                    import uuid
                    from datetime import timezone
                    internal_msg_id = f"internal_{ticket_state.ticket_number}_{uuid.uuid4().hex[:8]}"

                    recent_email = self.db.query(ProcessedEmail).filter(
                        ProcessedEmail.ticket_id == ticket_state.id
                    ).order_by(ProcessedEmail.processed_at.desc()).first()

                    internal_note = ProcessedEmail(
                        gmail_message_id=internal_msg_id,
                        gmail_thread_id=recent_email.gmail_thread_id if recent_email else None,
                        ticket_id=ticket_state.id,
                        order_number=ticket_state.order_number,
                        subject=pending_message.subject or "Internal note",
                        from_address="Internal",
                        message_body=pending_message.body,
                        success=True,
                        processed_at=datetime.now(timezone.utc)
                    )
                    self.db.add(internal_note)

            # Check if successful
            if result.get('succeeded'):
                pending_message.status = 'sent'
                pending_message.sent_at = datetime.utcnow()
                pending_message.reviewed_at = datetime.utcnow()
                pending_message.reviewed_by = reviewed_by_user_id
                self.db.commit()

                logger.info(
                    "Sent pending message successfully",
                    pending_message_id=pending_message_id,
                    ticket_number=ticket_state.ticket_number,
                    message_type=pending_message.message_type
                )
                return True
            else:
                # API call succeeded but message not sent
                error_msg = "; ".join(result.get('messages', ['Unknown error']))
                pending_message.status = 'failed'
                pending_message.last_error = error_msg
                pending_message.retry_count += 1
                self.db.commit()

                logger.error(
                    "Failed to send message - API returned failure",
                    pending_message_id=pending_message_id,
                    error=error_msg
                )
                return False

        except Exception as e:
            # Exception during send
            pending_message.status = 'failed'
            pending_message.last_error = str(e)
            pending_message.retry_count += 1
            self.db.commit()

            logger.error(
                "Exception while sending pending message",
                pending_message_id=pending_message_id,
                error=str(e),
                exc_info=True
            )
            return False

    def reject_pending_message(
        self,
        pending_message_id: int,
        reviewed_by_user_id: int,
        rejection_reason: Optional[str] = None
    ) -> bool:
        """
        Reject a pending message

        Args:
            pending_message_id: ID of pending message
            reviewed_by_user_id: User ID who rejected
            rejection_reason: Optional reason for rejection

        Returns:
            True if rejected successfully
        """
        pending_message = self.db.query(PendingMessage).get(pending_message_id)
        if not pending_message:
            logger.error("Pending message not found", pending_message_id=pending_message_id)
            return False

        pending_message.status = 'rejected'
        pending_message.reviewed_at = datetime.utcnow()
        pending_message.reviewed_by = reviewed_by_user_id
        if rejection_reason:
            pending_message.last_error = f"Rejected: {rejection_reason}"

        self.db.commit()

        logger.info(
            "Rejected pending message",
            pending_message_id=pending_message_id,
            reason=rejection_reason
        )

        return True

    def retry_failed_message(self, pending_message_id: int) -> bool:
        """
        Retry sending a failed message

        Args:
            pending_message_id: ID of pending message

        Returns:
            True if retry successful
        """
        pending_message = self.db.query(PendingMessage).get(pending_message_id)
        if not pending_message:
            return False

        if pending_message.status != 'failed':
            logger.warning(
                "Cannot retry message - not in failed status",
                pending_message_id=pending_message_id,
                status=pending_message.status
            )
            return False

        # Check retry limit (10 attempts)
        if pending_message.retry_count >= 10:
            logger.warning(
                "Message exceeded retry limit",
                pending_message_id=pending_message_id,
                retry_count=pending_message.retry_count
            )
            return False

        # Reset to pending and try again
        pending_message.status = 'pending'
        self.db.commit()

        logger.info("Retrying failed message", pending_message_id=pending_message_id)

        # Note: Actual retry sending would be triggered by a background job
        # For now, just mark as pending for manual retry
        return True

    def _enrich_ticket_data(
        self,
        ticket_state: TicketState,
        ticket_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enrich ticket data with state information"""
        enriched = ticket_data.copy()
        enriched['ticket_number'] = ticket_state.ticket_number
        enriched['customer_name'] = ticket_state.customer_name
        enriched['customer_email'] = ticket_state.customer_email
        enriched['supplier_name'] = ticket_state.supplier_name
        enriched['supplier_email'] = ticket_state.supplier_email
        enriched['order_number'] = ticket_state.order_number
        enriched['purchase_order_number'] = ticket_state.purchase_order_number
        enriched['supplier_ticket_references'] = ticket_state.supplier_ticket_references
        enriched['escalated'] = ticket_state.escalated

        return enriched

    def _get_supplier_email(self, ticket_data: Dict[str, Any]) -> Optional[str]:
        """Extract supplier email from ticket data"""
        # Try to get from purchase orders
        sales_order = ticket_data.get('salesOrder', {})
        purchase_orders = sales_order.get('purchaseOrders', [])

        if purchase_orders and len(purchase_orders) > 0:
            return purchase_orders[0].get('supplierEmail')

        return None

    def _get_attachments_for_message(
        self,
        ticket_data: Dict[str, Any],
        message_type: str
    ) -> List[str]:
        """
        Get relevant attachments for message type

        Args:
            ticket_data: Ticket data
            message_type: Type of message

        Returns:
            List of attachment file paths
        """
        attachments = []

        if message_type == "supplier":
            # Include customer damage photos for supplier
            gmail_attachments = ticket_data.get('attachments', [])
            for att_path in gmail_attachments:
                # Check if it's an image
                if att_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp')):
                    attachments.append(att_path)

        # For customer messages, typically don't include attachments unless specifically needed
        # For internal notes, include relevant documents

        return attachments

    def parse_confidence_score(self, ai_response: str) -> Optional[float]:
        """
        Parse confidence score from AI response

        Args:
            ai_response: Full AI response text

        Returns:
            Confidence score (0-1) or None
        """
        # Look for CONFIDENCE_SCORE: XX%
        match = re.search(r'CONFIDENCE_SCORE:\s*(\d+)%', ai_response, re.IGNORECASE)
        if match:
            score = int(match.group(1))
            return score / 100.0

        return None

    def _lookup_supplier_email_from_db(self, supplier_name: Optional[str]) -> Optional[str]:
        """
        Look up supplier email from suppliers table by name

        Args:
            supplier_name: Name of supplier

        Returns:
            Supplier email if found, None otherwise
        """
        if not supplier_name:
            return None

        try:
            from src.database.models import Supplier

            # Try exact match first
            supplier = self.db.query(Supplier).filter(
                Supplier.name == supplier_name
            ).first()

            if supplier:
                logger.info("Found supplier email from database",
                           supplier_name=supplier_name,
                           email=supplier.default_email)
                return supplier.default_email

            # Try partial match (for names like "2. Lyreco Deutschland GmbH")
            supplier = self.db.query(Supplier).filter(
                Supplier.name.contains(supplier_name.split('. ', 1)[-1] if '. ' in supplier_name else supplier_name)
            ).first()

            if supplier:
                logger.info("Found supplier email from database (partial match)",
                           supplier_name=supplier_name,
                           matched_name=supplier.name,
                           email=supplier.default_email)
                return supplier.default_email

            logger.warning("Supplier not found in database",
                          supplier_name=supplier_name)
            return None

        except Exception as e:
            logger.error("Failed to lookup supplier email",
                        supplier_name=supplier_name,
                        error=str(e))
            return None
