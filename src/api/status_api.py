"""
Status management API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from src.database import CustomStatus, TicketState
from src.api.web_api import get_current_user, User, get_db

router = APIRouter()


class StatusCreate(BaseModel):
    name: str
    color: str = 'gray'
    is_closed: bool = False
    display_order: int = 0


class StatusUpdate(BaseModel):
    name: str | None = None
    color: str | None = None
    is_closed: bool | None = None
    display_order: int | None = None


class StatusResponse(BaseModel):
    id: int
    name: str
    color: str
    is_closed: bool
    display_order: int

    class Config:
        from_attributes = True


@router.get("/api/statuses", response_model=List[StatusResponse])
async def get_statuses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all custom statuses ordered by display_order"""
    statuses = db.query(CustomStatus).order_by(CustomStatus.display_order).all()
    return statuses


@router.post("/api/statuses", response_model=StatusResponse)
async def create_status(
    status: StatusCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new custom status"""
    # Check if name already exists
    existing = db.query(CustomStatus).filter(CustomStatus.name == status.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Status name already exists")

    new_status = CustomStatus(
        name=status.name,
        color=status.color,
        is_closed=status.is_closed,
        display_order=status.display_order
    )
    db.add(new_status)
    db.commit()
    db.refresh(new_status)
    return new_status


@router.put("/api/statuses/{status_id}", response_model=StatusResponse)
async def update_status(
    status_id: int,
    status: StatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing status"""
    db_status = db.query(CustomStatus).filter(CustomStatus.id == status_id).first()
    if not db_status:
        raise HTTPException(status_code=404, detail="Status not found")

    # Check name uniqueness if changing name
    if status.name and status.name != db_status.name:
        existing = db.query(CustomStatus).filter(CustomStatus.name == status.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Status name already exists")

    # Update fields
    if status.name is not None:
        db_status.name = status.name
    if status.color is not None:
        db_status.color = status.color
    if status.is_closed is not None:
        db_status.is_closed = status.is_closed
    if status.display_order is not None:
        db_status.display_order = status.display_order

    db.commit()
    db.refresh(db_status)
    return db_status


@router.delete("/api/statuses/{status_id}")
async def delete_status(
    status_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a status (only if no tickets are using it)"""
    db_status = db.query(CustomStatus).filter(CustomStatus.id == status_id).first()
    if not db_status:
        raise HTTPException(status_code=404, detail="Status not found")

    # Check if any tickets are using this status
    ticket_count = db.query(TicketState).filter(TicketState.custom_status_id == status_id).count()
    if ticket_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete status: {ticket_count} ticket(s) are using it"
        )

    db.delete(db_status)
    db.commit()
    return {"message": "Status deleted successfully"}


@router.patch("/api/tickets/{ticket_number}/status")
async def update_ticket_status(
    ticket_number: str,
    status_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a ticket's custom status"""
    ticket = db.query(TicketState).filter(TicketState.ticket_number == ticket_number).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Verify status exists
    status = db.query(CustomStatus).filter(CustomStatus.id == status_id).first()
    if not status:
        raise HTTPException(status_code=404, detail="Status not found")

    ticket.custom_status_id = status_id
    db.commit()

    return {"message": "Ticket status updated", "status_name": status.name}
