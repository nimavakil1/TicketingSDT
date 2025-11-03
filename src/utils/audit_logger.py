"""
Audit Logging Utility
Helper functions for creating audit log entries
"""
import structlog
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from src.database.models import TicketAuditLog, TicketState, User

logger = structlog.get_logger(__name__)


def log_ticket_action(
    db: Session,
    ticket_number: str,
    action_type: str,
    action_description: str,
    user_id: Optional[int] = None,
    field_name: Optional[str] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Create an audit log entry for a ticket action

    Args:
        db: Database session
        ticket_number: Ticket number
        action_type: Type of action (e.g., "status_change", "message_sent", "comment_added")
        action_description: Human-readable description
        user_id: ID of user who performed action (None for system actions)
        field_name: Name of field that changed (optional)
        old_value: Previous value (optional)
        new_value: New value (optional)
        extra_data: Additional JSON data (optional)

    Returns:
        True if logged successfully, False otherwise
    """
    try:
        # Get ticket
        ticket = db.query(TicketState).filter(
            TicketState.ticket_number == ticket_number
        ).first()

        if not ticket:
            logger.warning(
                "Cannot log action: ticket not found",
                ticket_number=ticket_number
            )
            return False

        # Create audit log entry
        audit_log = TicketAuditLog(
            ticket_id=ticket.id,
            user_id=user_id,
            action_type=action_type,
            action_description=action_description,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            extra_data=extra_data,
            created_at=datetime.utcnow()
        )

        db.add(audit_log)
        db.commit()

        logger.info(
            "Audit log created",
            ticket_number=ticket_number,
            action_type=action_type,
            user_id=user_id
        )

        return True

    except Exception as e:
        logger.error(
            "Failed to create audit log",
            ticket_number=ticket_number,
            action_type=action_type,
            error=str(e)
        )
        db.rollback()
        return False


def log_status_change(
    db: Session,
    ticket_number: str,
    old_status_name: str,
    new_status_name: str,
    user_id: Optional[int] = None
) -> bool:
    """Log a ticket status change"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="status_change",
        action_description=f"changed status from '{old_status_name}' to '{new_status_name}'",
        user_id=user_id,
        field_name="status",
        old_value=old_status_name,
        new_value=new_status_name
    )


def log_message_sent(
    db: Session,
    ticket_number: str,
    message_type: str,  # "customer_email", "supplier_email", "old_system", "internal_note"
    recipient: Optional[str] = None,
    user_id: Optional[int] = None
) -> bool:
    """Log a message being sent"""
    if message_type == "customer_email":
        description = f"sent email to customer"
        if recipient:
            description += f" ({recipient})"
    elif message_type == "supplier_email":
        description = f"sent email to supplier"
        if recipient:
            description += f" ({recipient})"
    elif message_type == "old_system":
        description = f"sent message to old ticketing system"
    elif message_type == "internal_note":
        description = f"added internal comment"
    else:
        description = f"sent {message_type} message"

    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type=f"message_{message_type}",
        action_description=description,
        user_id=user_id,
        extra_data={"recipient": recipient} if recipient else None
    )


def log_message_received(
    db: Session,
    ticket_number: str,
    sender: str,
    is_supplier: bool = False
) -> bool:
    """Log a message being received from customer or supplier"""
    if is_supplier:
        description = f"received email from supplier ({sender})"
        action_type = "message_received_supplier"
    else:
        description = f"received email from customer ({sender})"
        action_type = "message_received_customer"

    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type=action_type,
        action_description=description,
        user_id=None,  # System action
        extra_data={"sender": sender, "is_supplier": is_supplier}
    )


def log_attachment_added(
    db: Session,
    ticket_number: str,
    filename: str,
    file_size: int,
    user_id: Optional[int] = None
) -> bool:
    """Log an attachment being added"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="attachment_added",
        action_description=f"uploaded attachment '{filename}'",
        user_id=user_id,
        extra_data={"filename": filename, "size_bytes": file_size}
    )


def log_ticket_created(
    db: Session,
    ticket_number: str,
    created_by: str = "System",
    user_id: Optional[int] = None
) -> bool:
    """Log ticket creation"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="ticket_created",
        action_description=f"created ticket",
        user_id=user_id
    )


def log_field_update(
    db: Session,
    ticket_number: str,
    field_name: str,
    old_value: str,
    new_value: str,
    user_id: Optional[int] = None
) -> bool:
    """Log a field being updated"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="field_update",
        action_description=f"updated {field_name}",
        user_id=user_id,
        field_name=field_name,
        old_value=old_value,
        new_value=new_value
    )


def log_ticket_reprocessed(
    db: Session,
    ticket_number: str,
    user_id: Optional[int] = None
) -> bool:
    """Log ticket being reprocessed"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="reprocess",
        action_description="reprocessed ticket with AI",
        user_id=user_id
    )


def log_ticket_analyzed(
    db: Session,
    ticket_number: str,
    user_id: Optional[int] = None
) -> bool:
    """Log ticket being analyzed"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="analyze",
        action_description="analyzed ticket with AI",
        user_id=user_id
    )


def log_ticket_refreshed(
    db: Session,
    ticket_number: str,
    user_id: Optional[int] = None
) -> bool:
    """Log ticket data being refreshed from old system"""
    return log_ticket_action(
        db=db,
        ticket_number=ticket_number,
        action_type="refresh",
        action_description="refreshed ticket data from old system",
        user_id=user_id
    )
