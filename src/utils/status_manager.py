"""
Status Management Utility
Helper functions for updating ticket statuses
"""
import structlog
from typing import Optional
from sqlalchemy.orm import Session
from src.database.models import CustomStatus, TicketState
from src.utils.audit_logger import log_status_change

logger = structlog.get_logger(__name__)


def update_ticket_status(
    ticket_number: str,
    status_name: str,
    db: Session,
    user_id: Optional[int] = None
) -> bool:
    """
    Update a ticket's custom status by status name

    Args:
        ticket_number: Ticket number to update
        status_name: Name of the status (e.g., "ESCALATED", "Resolved")
        db: Database session
        user_id: ID of user making the change (None for system changes)

    Returns:
        True if status was updated, False otherwise
    """
    try:
        # Get status by name
        status = db.query(CustomStatus).filter(
            CustomStatus.name == status_name
        ).first()

        if not status:
            logger.warning(
                "Status not found",
                status_name=status_name,
                ticket_number=ticket_number
            )
            return False

        # Get ticket
        ticket = db.query(TicketState).filter(
            TicketState.ticket_number == ticket_number
        ).first()

        if not ticket:
            logger.warning(
                "Ticket not found",
                ticket_number=ticket_number
            )
            return False

        # Get old status name for logging
        old_status_name = None
        if ticket.custom_status_id:
            old_status = db.query(CustomStatus).filter(
                CustomStatus.id == ticket.custom_status_id
            ).first()
            if old_status:
                old_status_name = old_status.name

        # Update status
        old_status_id = ticket.custom_status_id
        ticket.custom_status_id = status.id
        db.commit()

        # Log the status change
        if old_status_name and old_status_name != status_name:
            log_status_change(
                db=db,
                ticket_number=ticket_number,
                old_status_name=old_status_name,
                new_status_name=status_name,
                user_id=user_id
            )

        logger.info(
            "Ticket status updated",
            ticket_number=ticket_number,
            old_status_id=old_status_id,
            new_status=status_name,
            new_status_id=status.id
        )

        return True

    except Exception as e:
        logger.error(
            "Failed to update ticket status",
            ticket_number=ticket_number,
            status_name=status_name,
            error=str(e)
        )
        db.rollback()
        return False


def get_status_by_name(status_name: str, db: Session) -> CustomStatus | None:
    """
    Get a status by name

    Args:
        status_name: Name of the status
        db: Database session

    Returns:
        CustomStatus object or None if not found
    """
    try:
        return db.query(CustomStatus).filter(
            CustomStatus.name == status_name
        ).first()
    except Exception as e:
        logger.error(
            "Failed to get status",
            status_name=status_name,
            error=str(e)
        )
        return None
