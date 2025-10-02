"""
Supplier Manager
Manages supplier communications and reminders
Tracks supplier response times and sends reminders after timeout
"""
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import structlog

from config.settings import settings
from src.database.models import Supplier, SupplierMessage, TicketState
from src.api.ticketing_client import TicketingAPIClient

logger = structlog.get_logger(__name__)


class SupplierManager:
    """Manages supplier communications and reminder system"""

    def __init__(self, ticketing_client: TicketingAPIClient, db_session: Any):
        self.ticketing_client = ticketing_client
        self.db_session = db_session

    def get_or_create_supplier(self, supplier_name: str, default_email: str) -> Supplier:
        """
        Get existing supplier or create new one

        Args:
            supplier_name: Supplier name
            default_email: Default contact email

        Returns:
            Supplier object
        """
        supplier = self.db_session.query(Supplier).filter_by(name=supplier_name).first()

        if not supplier:
            supplier = Supplier(
                name=supplier_name,
                default_email=default_email,
                contact_fields={}
            )
            self.db_session.add(supplier)
            self.db_session.commit()
            logger.info("Created new supplier", supplier_name=supplier_name)

        return supplier

    def record_supplier_message(
        self,
        ticket_state: TicketState,
        supplier: Supplier,
        message_content: str,
        purpose: str
    ) -> SupplierMessage:
        """
        Record a message sent to supplier

        Args:
            ticket_state: Ticket state object
            supplier: Supplier object
            message_content: Message content
            purpose: Purpose of message (e.g., 'tracking_request')

        Returns:
            SupplierMessage object
        """
        supplier_message = SupplierMessage(
            ticket_id=ticket_state.id,
            supplier_id=supplier.id,
            message_content=message_content,
            sent_at=datetime.utcnow(),
            purpose=purpose,
            response_received=False
        )

        self.db_session.add(supplier_message)
        self.db_session.commit()

        logger.info(
            "Recorded supplier message",
            ticket_number=ticket_state.ticket_number,
            supplier=supplier.name,
            purpose=purpose
        )

        return supplier_message

    def mark_supplier_response_received(self, ticket_number: str) -> None:
        """
        Mark that supplier has responded to a ticket

        Args:
            ticket_number: Ticket number
        """
        # Get ticket state
        ticket_state = self.db_session.query(TicketState).filter_by(
            ticket_number=ticket_number
        ).first()

        if not ticket_state:
            logger.warning("Ticket state not found", ticket_number=ticket_number)
            return

        # Find latest unreplied supplier message for this ticket
        supplier_message = self.db_session.query(SupplierMessage).filter_by(
            ticket_id=ticket_state.id,
            response_received=False
        ).order_by(SupplierMessage.sent_at.desc()).first()

        if supplier_message:
            supplier_message.response_received = True
            supplier_message.response_received_at = datetime.utcnow()
            self.db_session.commit()

            logger.info(
                "Marked supplier response received",
                ticket_number=ticket_number,
                response_time=supplier_message.response_received_at - supplier_message.sent_at
            )

    def check_and_send_reminders(self) -> int:
        """
        Check for overdue supplier messages and send reminders

        Returns:
            Number of reminders sent
        """
        logger.info("Checking for overdue supplier messages")

        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=settings.supplier_reminder_hours)

        # Find overdue messages without reminders
        overdue_messages = self.db_session.query(SupplierMessage).filter(
            SupplierMessage.response_received == False,
            SupplierMessage.reminder_sent == False,
            SupplierMessage.sent_at <= cutoff_time
        ).all()

        reminders_sent = 0

        for supplier_message in overdue_messages:
            try:
                self._send_reminder(supplier_message)
                reminders_sent += 1
            except Exception as e:
                logger.error(
                    "Failed to send reminder",
                    message_id=supplier_message.id,
                    error=str(e)
                )

        logger.info("Reminder check complete", reminders_sent=reminders_sent)
        return reminders_sent

    def _send_reminder(self, supplier_message: SupplierMessage) -> None:
        """
        Send reminder for an overdue supplier message

        Args:
            supplier_message: SupplierMessage object
        """
        # Get ticket and supplier info
        ticket_state = self.db_session.query(TicketState).get(supplier_message.ticket_id)
        supplier = self.db_session.query(Supplier).get(supplier_message.supplier_id)

        if not ticket_state or not supplier:
            logger.error("Missing ticket or supplier data", message_id=supplier_message.id)
            return

        logger.info(
            "Sending supplier reminder",
            ticket_number=ticket_state.ticket_number,
            supplier=supplier.name,
            hours_elapsed=(datetime.utcnow() - supplier_message.sent_at).total_seconds() / 3600
        )

        # Build reminder message
        reminder_message = f"""Reminder: Response Needed

We sent you a message regarding ticket {ticket_state.ticket_number} (Order: {ticket_state.order_number}) on {supplier_message.sent_at.strftime('%Y-%m-%d %H:%M')} UTC.

We have not yet received a response. Please respond as soon as possible.

Original message:
---
{supplier_message.message_content}
---

Thank you for your prompt attention.
"""

        try:
            # Send reminder via ticketing API
            result = self.ticketing_client.send_message_to_supplier(
                ticket_id=ticket_state.ticket_id,
                message=reminder_message,
                ticket_status_id=ticket_state.ticket_status_id,
                owner_id=ticket_state.owner_id
            )

            if result.get('succeeded'):
                # Mark reminder as sent
                supplier_message.reminder_sent = True
                supplier_message.reminder_sent_at = datetime.utcnow()
                self.db_session.commit()

                logger.info("Reminder sent to supplier", ticket_number=ticket_state.ticket_number)

                # Send internal alert to operations
                self._send_internal_alert(ticket_state, supplier, supplier_message)

            else:
                logger.error(
                    "Failed to send supplier reminder",
                    ticket_number=ticket_state.ticket_number,
                    api_messages=result.get('messages', [])
                )

        except Exception as e:
            logger.error("Error sending supplier reminder", error=str(e))
            raise

    def _send_internal_alert(
        self,
        ticket_state: TicketState,
        supplier: Supplier,
        supplier_message: SupplierMessage
    ) -> None:
        """
        Send internal alert to operations team about overdue supplier response

        Args:
            ticket_state: Ticket state
            supplier: Supplier
            supplier_message: Supplier message
        """
        alert_message = f"""⚠️ Supplier Response Overdue - Call Required

Ticket: {ticket_state.ticket_number}
Order: {ticket_state.order_number}
Supplier: {supplier.name}
Customer: {ticket_state.customer_name}

The supplier has not responded to our message sent on {supplier_message.sent_at.strftime('%Y-%m-%d %H:%M')} UTC (over {settings.supplier_reminder_hours} hours ago).

A reminder email has been sent to the supplier. Please call the supplier to follow up.

Supplier Contact: {supplier.default_email}
Purpose: {supplier_message.purpose}
"""

        try:
            # Send internal note to ticket
            result = self.ticketing_client.send_internal_message(
                ticket_id=ticket_state.ticket_id,
                message=alert_message,
                ticket_status_id=ticket_state.ticket_status_id,
                owner_id=ticket_state.owner_id
            )

            if result.get('succeeded'):
                supplier_message.internal_alert_sent = True
                supplier_message.internal_alert_sent_at = datetime.utcnow()
                self.db_session.commit()

                logger.info("Internal alert sent", ticket_number=ticket_state.ticket_number)

            # TODO: Also send email to operations team if configured
            # This would require email sending capability beyond the ticketing API
            # For now, the internal note in the ticket should suffice

        except Exception as e:
            logger.error("Failed to send internal alert", error=str(e))

    def update_supplier_contact(
        self,
        supplier_name: str,
        field_name: str,
        email_address: str
    ) -> bool:
        """
        Update or add a contact field for a supplier

        Args:
            supplier_name: Supplier name
            field_name: Contact field name (e.g., 'returns', 'tracking')
            email_address: Email address

        Returns:
            True if successful
        """
        supplier = self.db_session.query(Supplier).filter_by(name=supplier_name).first()

        if not supplier:
            logger.warning("Supplier not found", supplier_name=supplier_name)
            return False

        if not supplier.contact_fields:
            supplier.contact_fields = {}

        supplier.contact_fields[field_name] = email_address
        self.db_session.commit()

        logger.info(
            "Updated supplier contact",
            supplier=supplier_name,
            field=field_name,
            email=email_address
        )

        return True
