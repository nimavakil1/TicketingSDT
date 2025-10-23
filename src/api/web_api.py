"""
Web API for AI Agent Management UI
FastAPI application that exposes existing system functionality via REST API
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import structlog
import re
import html
from html.parser import HTMLParser
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status, Form, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Load environment variables at startup
load_dotenv()

from config.settings import settings
from src.database.models import TicketState, AIDecisionLog, ProcessedEmail, RetryQueue, User, PendingMessage, MessageTemplate, Attachment, TicketAuditLog, init_database
from src.ai.ai_engine import AIEngine
from src.api.ticketing_client import TicketingAPIClient
from src.utils.message_service import MessageService
from src.utils.text_filter import TextFilter
from src.utils.status_manager import update_ticket_status
from src.scheduler.message_retry_scheduler import start_scheduler, stop_scheduler

logger = structlog.get_logger(__name__)

# FastAPI app
app = FastAPI(
    title="AI Support Agent API",
    description="Management API for AI-powered customer support automation",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# JWT settings
SECRET_KEY = settings.jwt_secret_key if hasattr(settings, 'jwt_secret_key') else "change-this-secret-key-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours


# Pydantic models
class LoginRequest(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime


class UserInfo(BaseModel):
    id: int
    username: str
    email: str
    role: str
    created_at: datetime


class DashboardStats(BaseModel):
    emails_processed_today: int
    tickets_active: int
    tickets_escalated: int
    ai_decisions_today: int
    average_confidence: float
    emails_in_retry_queue: int
    phase: int


class CustomStatusInfo(BaseModel):
    id: int
    name: str
    color: str
    is_closed: bool
    display_order: int

    class Config:
        from_attributes = True


class TicketInfo(BaseModel):
    ticket_number: str
    status: str
    customer_email: str
    customer_name: Optional[str]
    order_number: Optional[str]
    purchase_order_number: Optional[str]
    last_updated: datetime
    escalated: bool
    ai_decision_count: int
    ticket_status_id: int
    owner_id: Optional[int]
    custom_status_id: Optional[int]
    custom_status: Optional[CustomStatusInfo]


class AIDecisionInfo(BaseModel):
    id: int
    ticket_number: str
    timestamp: datetime
    detected_language: Optional[str]
    detected_intent: Optional[str]
    confidence_score: Optional[float]
    action_taken: str
    deployment_phase: int


class RetryQueueItem(BaseModel):
    id: int
    gmail_message_id: str
    subject: Optional[str]
    from_address: Optional[str]
    attempts: int
    next_attempt_at: Optional[datetime]
    last_error: Optional[str]


class SettingsUpdate(BaseModel):
    deployment_phase: Optional[int]
    confidence_threshold: Optional[float]
    ai_temperature: Optional[float]
    ai_model: Optional[str]
    ai_max_tokens: Optional[int]
    system_prompt: Optional[str]


class PendingMessageInfo(BaseModel):
    id: int
    ticket_number: str
    message_type: str  # 'supplier', 'customer', 'internal'
    recipient_email: Optional[str]
    cc_emails: List[str]
    subject: str
    body: str
    attachments: List[str]
    confidence_score: Optional[float]
    status: str  # 'pending', 'approved', 'rejected', 'sent', 'failed'
    retry_count: int
    last_error: Optional[str]
    created_at: datetime
    reviewed_at: Optional[datetime]
    sent_at: Optional[datetime]


class PendingMessageUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    cc_emails: Optional[List[str]] = None
    attachments: Optional[List[str]] = None


class PendingMessageCreate(BaseModel):
    ticket_id: int
    message_type: str  # 'customer', 'supplier', 'internal'
    recipient_email: str
    subject: str
    body: str
    cc_emails: Optional[List[str]] = None
    attachments: Optional[List[str]] = None


class MessageApproval(BaseModel):
    action: str  # 'approve' or 'reject'
    rejection_reason: Optional[str] = None
    updated_data: Optional[PendingMessageUpdate] = None


class AttachmentInfo(BaseModel):
    id: int
    ticket_id: int
    filename: str
    original_filename: str
    mime_type: Optional[str]
    file_size: Optional[int]
    extraction_status: str
    extracted_text: Optional[str]
    created_at: datetime
    gmail_message_id: Optional[str]


class TicketAuditLogInfo(BaseModel):
    id: int
    ticket_id: int
    user_id: Optional[int]
    username: Optional[str]  # For display
    action_type: str
    action_description: str
    field_name: Optional[str]
    old_value: Optional[str]
    new_value: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime


class PromptApprovalRequest(BaseModel):
    new_prompt: str
    change_summary: str


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    role: str = 'viewer'  # 'admin', 'operator', 'viewer'
    full_name: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str]
    password: Optional[str]
    role: Optional[str]
    full_name: Optional[str]
    is_active: Optional[bool]


# Initialize database session maker
SessionMaker = init_database()

# Database dependency
def get_db():
    """Get database session"""
    session = SessionMaker()
    try:
        yield session
    finally:
        session.close()


# Helper function to ensure timezone-aware datetimes
def ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert naive datetime to UTC-aware datetime"""
    if dt is None:
        return None
    if dt.tzinfo is None:
        # Assume naive datetimes from database are UTC
        return dt.replace(tzinfo=timezone.utc)
    return dt


# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception

    return user


# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    logger.info("Starting AI Support Agent API...")

    # Database already initialized at module level
    logger.info("Database initialized")

    # Start message retry scheduler
    try:
        ticketing_client = TicketingAPIClient()
        start_scheduler(ticketing_client, SessionMaker)
        logger.info("Message retry scheduler started")
    except Exception as e:
        logger.error(f"Failed to start message retry scheduler: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down AI Support Agent API...")

    # Stop message retry scheduler
    try:
        stop_scheduler()
        logger.info("Message retry scheduler stopped")
    except Exception as e:
        logger.error(f"Error stopping scheduler: {e}", exc_info=True)


# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "phase": settings.deployment_phase
    }


# Authentication endpoints
@app.post("/api/auth/login", response_model=Token)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login and get JWT token"""
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_at": datetime.utcnow() + access_token_expires
    }


@app.get("/api/auth/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        role=current_user.role,
        created_at=current_user.created_at
    )


# Dashboard endpoints
@app.get("/api/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    today = datetime.utcnow().date()

    # Count emails processed today
    emails_today = db.query(ProcessedEmail).filter(
        ProcessedEmail.processed_at >= today
    ).count()

    # Count active tickets (not resolved/closed)
    active_tickets = db.query(TicketState).filter(
        TicketState.escalated == False
    ).count()

    # Count escalated tickets
    escalated_tickets = db.query(TicketState).filter(
        TicketState.escalated == True
    ).count()

    # Count AI decisions today
    decisions_today = db.query(AIDecisionLog).filter(
        AIDecisionLog.timestamp >= today
    ).count()

    # Calculate average confidence today
    avg_confidence_result = db.query(
        func.avg(AIDecisionLog.confidence_score)
    ).filter(
        AIDecisionLog.timestamp >= today,
        AIDecisionLog.confidence_score.isnot(None)
    ).scalar()

    avg_confidence = float(avg_confidence_result) if avg_confidence_result else 0.0

    # Count retry queue items
    retry_count = db.query(RetryQueue).count()

    return DashboardStats(
        emails_processed_today=emails_today,
        tickets_active=active_tickets,
        tickets_escalated=escalated_tickets,
        ai_decisions_today=decisions_today,
        average_confidence=avg_confidence,
        emails_in_retry_queue=retry_count,
        phase=settings.deployment_phase
    )


# Email queue endpoints
@app.get("/api/emails/processed", response_model=List[Dict[str, Any]])
async def get_processed_emails(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get list of processed emails"""
    processed = db.query(ProcessedEmail).order_by(
        ProcessedEmail.processed_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        {
            "id": msg.id,
            "gmail_message_id": msg.gmail_message_id,
            "subject": msg.subject or "N/A",
            "from_address": msg.from_address or "N/A",
            "order_number": msg.order_number or "N/A",
            "processed_at": ensure_utc(msg.processed_at),
            "success": getattr(msg, 'success', True),  # Default to True for old records
            "error_message": getattr(msg, 'error_message', None)
        }
        for msg in processed
    ]


@app.get("/api/emails/retry-queue", response_model=List[RetryQueueItem])
async def get_retry_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0
):
    """Get emails in retry queue (most recent first)"""
    retries = db.query(RetryQueue).order_by(
        RetryQueue.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        RetryQueueItem(
            id=retry.id,
            gmail_message_id=retry.gmail_message_id,
            subject=retry.subject,
            from_address=retry.from_address,
            attempts=retry.attempts,
            next_attempt_at=ensure_utc(retry.next_attempt_at),
            last_error=retry.last_error
        )
        for retry in retries
    ]


# Ticket endpoints
@app.get("/api/tickets", response_model=List[TicketInfo])
async def get_tickets(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    escalated_only: bool = False
):
    """Get list of tickets"""
    query = db.query(TicketState).order_by(TicketState.updated_at.desc())

    if escalated_only:
        query = query.filter(TicketState.escalated == True)

    tickets = query.offset(offset).limit(limit).all()

    return [
        TicketInfo(
            ticket_number=ticket.ticket_number,
            status=ticket.current_state or "unknown",
            customer_email=ticket.customer_email or "N/A",
            customer_name=ticket.customer_name,
            order_number=ticket.order_number,
            purchase_order_number=ticket.purchase_order_number,
            last_updated=ticket.updated_at,
            escalated=ticket.escalated,
            ai_decision_count=len(ticket.ai_decisions),
            ticket_status_id=ticket.ticket_status_id or 0,
            owner_id=ticket.owner_id,
            custom_status_id=ticket.custom_status_id,
            custom_status=CustomStatusInfo.model_validate(ticket.custom_status) if ticket.custom_status else None
        )
        for ticket in tickets
    ]


@app.get("/api/tickets/{ticket_number}", response_model=Dict[str, Any])
async def get_ticket_detail(
    ticket_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed ticket information including AI decisions and message history"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get AI decisions for this ticket
    decisions = db.query(AIDecisionLog).filter(
        AIDecisionLog.ticket_id == ticket.id
    ).order_by(AIDecisionLog.timestamp.desc()).all()

    # For imported tickets, get messages from database
    # For live tickets, fetch from ticketing system API
    messages = []

    if ticket.current_state == 'imported':
        # Get messages from processed_emails table
        from sqlalchemy import text
        result = db.execute(text("""
            SELECT id, gmail_message_id, processed_at, subject, from_address, message_body
            FROM processed_emails
            WHERE ticket_id = :ticket_id
            ORDER BY processed_at ASC
        """), {"ticket_id": ticket.id}).fetchall()

        for row in result:
            email_id, gmail_message_id, processed_at, subject, from_address, message_body = row

            # Determine message type from subject
            subject_lower = (subject or "").lower()
            if "from customer" in subject_lower:
                message_type = "customer"
                is_internal = False
            elif "to customer" in subject_lower:
                message_type = "operator_to_customer"
                is_internal = False
            elif "to supplier" in subject_lower:
                message_type = "operator_to_supplier"
                is_internal = False
            elif "from supplier" in subject_lower:
                message_type = "supplier"
                is_internal = False
            elif "internal" in subject_lower:
                message_type = "internal"
                is_internal = True
            else:
                message_type = "unknown"
                is_internal = False

            message = {
                "id": email_id,
                "gmail_message_id": gmail_message_id,
                "createdAt": processed_at if processed_at else None,  # Already a string from DB
                "messageText": message_body or "(No content)",
                "messageType": message_type,
                "isInternal": is_internal,
                "authorName": None,
                "authorEmail": from_address,
                "sourceType": "email"
            }
            messages.append(message)
    else:
        # Fetch ticket messages from ticketing system API
        from src.api.ticketing_client import TicketingAPIClient
        try:
            ticketing_client = TicketingAPIClient()
            ticket_data = ticketing_client.get_ticket_by_ticket_number(ticket_number)
            if ticket_data and len(ticket_data) > 0:
                # The API returns ticketDetails array with message objects
                ticket_details = ticket_data[0].get("ticketDetails", [])

                # Initialize text filter for cleaning message text
                text_filter = TextFilter(db)

                # Transform ticketDetails into a simpler message format
                for detail in ticket_details:
                    # Get raw message text
                    raw_message_text = detail.get("comment", "")

                    # Skip ALL AI Agent messages (case-insensitive) - same logic as orchestrator
                    if raw_message_text:
                        comment_lower = raw_message_text.strip().lower()
                        if (comment_lower.startswith('ai agent') or
                            'ai agent proposes' in comment_lower or
                            'ai agent suggests' in comment_lower or
                            raw_message_text.strip().startswith('🚨')):
                            continue

                    source = detail.get("sourceTicketSideTypeId")
                    target = detail.get("targetTicketSideTypeId")

                    # Determine message type based on source and target
                    # 1 = System/Operator, 2 = Customer, 3 = Supplier
                    if source == 2 and target == 1:
                        message_type = "customer"
                        is_internal = False
                    elif source == 1 and target == 2:
                        message_type = "operator_to_customer"
                        is_internal = False
                    elif source == 1 and target == 3:
                        message_type = "operator_to_supplier"
                        is_internal = False
                    elif source == 3 and target == 1:
                        message_type = "supplier"
                        is_internal = False
                    elif source == 1 and target == 1:
                        message_type = "internal"
                        is_internal = True
                    else:
                        message_type = "unknown"
                        is_internal = False

                    # Apply text filtering to remove skip blocks
                    filtered_message_text = text_filter.filter_email_body(raw_message_text)

                    message = {
                        "id": detail.get("id"),
                        "gmail_message_id": None,  # Not available from ticketing system API
                        "createdAt": detail.get("createdDateTime"),
                        "messageText": filtered_message_text,
                        "messageType": message_type,
                        "isInternal": is_internal,
                        "authorName": None,  # Not available in this API
                        "authorEmail": detail.get("receiverEmailAddress") or detail.get("entranceEmailSenderAddress"),
                        "sourceType": "email" if detail.get("entranceEmailBody") else "note"
                    }
                    messages.append(message)

                logger.info("Fetched ticket messages", ticket_number=ticket_number, message_count=len(messages))
        except Exception as e:
            logger.warning("Failed to fetch ticket messages from ticketing API", error=str(e), ticket_number=ticket_number)
            # Continue without messages rather than failing

    return {
        "ticket_number": ticket.ticket_number,
        "ticket_id": ticket.ticket_id,
        "status": ticket.current_state or "unknown",
        "customer_email": ticket.customer_email,
        "customer_name": ticket.customer_name,
        "customer_address": ticket.customer_address,
        "customer_city": ticket.customer_city,
        "customer_postal_code": ticket.customer_postal_code,
        "customer_country": ticket.customer_country,
        "customer_phone": ticket.customer_phone,
        "order_number": ticket.order_number,
        "order_total": ticket.order_total,
        "order_currency": ticket.order_currency,
        "order_date": ticket.order_date,
        "purchase_order_number": ticket.purchase_order_number,
        "tracking_number": ticket.tracking_number,
        "tracking_url": ticket.tracking_url,
        "carrier_name": ticket.carrier_name,
        "delivery_status": ticket.delivery_status,
        "expected_delivery_date": ticket.expected_delivery_date,
        "product_details": ticket.product_details,
        "supplier_name": ticket.supplier_name,
        "supplier_email": ticket.supplier_email,
        "supplier_phone": ticket.supplier_phone,
        "supplier_contact_person": ticket.supplier_contact_person,
        "ticket_status_id": ticket.ticket_status_id,
        "owner_id": ticket.owner_id,
        "custom_status_id": ticket.custom_status_id,
        "custom_status": {
            "id": ticket.custom_status.id,
            "name": ticket.custom_status.name,
            "color": ticket.custom_status.color,
            "is_closed": ticket.custom_status.is_closed,
            "display_order": ticket.custom_status.display_order
        } if ticket.custom_status else None,
        "escalated": ticket.escalated,
        "escalation_reason": ticket.escalation_reason,
        "escalation_date": ensure_utc(ticket.escalation_date),
        "last_updated": ensure_utc(ticket.updated_at),
        "created_at": ensure_utc(ticket.created_at),
        "messages": messages,
        "ai_decisions": [
            {
                "id": dec.id,
                "timestamp": ensure_utc(dec.timestamp),
                "detected_language": dec.detected_language,
                "detected_intent": dec.detected_intent,
                "confidence_score": dec.confidence_score,
                "recommended_action": dec.recommended_action,
                "response_generated": dec.response_generated,
                "action_taken": dec.action_taken,
                "deployment_phase": dec.deployment_phase,
                "feedback": dec.feedback,
                "feedback_notes": dec.feedback_notes
            }
            for dec in decisions
        ]
    }


@app.post("/api/tickets/{ticket_number}/reprocess")
async def reprocess_ticket(
    ticket_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reprocess a ticket - run AI analysis again on the last email"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    try:
        # Fetch ticket data from API
        from src.api.ticketing_client import TicketingAPIClient
        ticketing_client = TicketingAPIClient()
        ticket_data = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not ticket_data or len(ticket_data) == 0:
            raise HTTPException(status_code=404, detail="Ticket not found in ticketing system")

        ticket_api_data = ticket_data[0]

        # Get the email from ticketing API
        ticket_details = ticket_api_data.get("ticketDetails", [])
        if not ticket_details:
            raise HTTPException(status_code=404, detail="No messages found for this ticket")

        # Find the first customer email (entrance email)
        customer_email = None
        for detail in ticket_details:
            if detail.get("entranceEmailBody"):
                customer_email = {
                    'subject': detail.get("entranceEmailSubject", ""),
                    'body': detail.get("entranceEmailBody", ""),
                    'from': detail.get("entranceEmailSenderAddress", ticket.customer_email)
                }
                break

        if not customer_email:
            raise HTTPException(status_code=404, detail="No customer email found in ticket")

        email_data = customer_email

        # Get supplier language
        supplier_language = None
        purchase_orders = ticket_api_data.get('salesOrder', {}).get('purchaseOrders', [])
        if purchase_orders:
            supplier_name = purchase_orders[0].get('supplierName')
            if supplier_name:
                # Look up supplier in database
                from src.database.models import Supplier
                supplier = db.query(Supplier).filter(Supplier.name == supplier_name).first()
                if supplier and supplier.language_code:
                    supplier_language = supplier.language_code

        # Re-run AI analysis
        ai_engine = AIEngine()

        analysis = ai_engine.analyze_email(
            email_data=email_data,
            ticket_data=ticket_api_data,
            supplier_language=supplier_language
        )

        # Create new AI decision log
        new_decision = AIDecisionLog(
            ticket_id=ticket.id,
            detected_language=analysis.get('language'),
            detected_intent=analysis.get('intent'),
            confidence_score=analysis.get('confidence'),
            recommended_action=analysis.get('summary'),
            response_generated=analysis.get('customer_response'),
            action_taken='reprocessed' if analysis.get('requires_escalation') else 'analyzed',
            deployment_phase=settings.deployment_phase
        )
        db.add(new_decision)

        # Update ticket state if needed
        if analysis.get('requires_escalation'):
            ticket.escalated = True
            ticket.escalation_reason = analysis.get('escalation_reason')
            ticket.current_state = 'escalated'
            # Update custom status to ESCALATED
            update_ticket_status(ticket.ticket_number, 'ESCALATED', db)
        else:
            ticket.escalated = False
            ticket.escalation_reason = None
            # Update custom status to In Progress (being worked on)
            update_ticket_status(ticket.ticket_number, 'In Progress', db)

        ticket.updated_at = datetime.utcnow()
        db.commit()

        logger.info("Ticket reprocessed", ticket_number=ticket_number, decision_id=new_decision.id)

        # Send internal note to ticketing system
        try:
            intent = analysis.get('intent', 'unknown')
            confidence = analysis.get('confidence', 0)
            confidence_pct = int(confidence * 100)
            escalated = "Yes" if analysis.get('requires_escalation') else "No"
            escalation_reason = analysis.get('escalation_reason', '')

            # Build internal note message
            internal_note = f"""🔄 Ticket Reprocessed by AI Agent

**Analysis Results:**
- Intent: {intent}
- Confidence: {confidence_pct}%
- Escalated: {escalated}
"""
            if escalation_reason:
                internal_note += f"- Escalation Reason: {escalation_reason}\n"

            internal_note += f"\nReprocessed by: {current_user.username}\nTimestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"

            # Send internal note
            ticketing_client.add_internal_note(
                ticket_id=ticket.ticket_id,
                note=internal_note
            )
            logger.info("Internal note sent to ticketing system", ticket_number=ticket_number)
        except Exception as note_error:
            logger.error("Failed to send internal note to ticketing system",
                        ticket_number=ticket_number,
                        error=str(note_error))
            # Don't fail the whole operation if note fails

        return {
            "success": True,
            "message": "Ticket reprocessed successfully",
            "decision_id": new_decision.id,
            "requires_escalation": analysis.get('requires_escalation'),
            "confidence": analysis.get('confidence')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to reprocess ticket", ticket_number=ticket_number, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to reprocess ticket: {str(e)}")


class AnalyzeRequest(BaseModel):
    ignored_message_ids: List[int] = []
    preview_only: bool = False


@app.post("/api/tickets/{ticket_number}/analyze")
async def analyze_ticket(
    ticket_number: str,
    request: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Run AI analysis on imported ticket with specific messages ignored"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    try:
        # Get messages from database with source/target info
        from sqlalchemy import text

        # First get ticketDetails from API to determine message types
        from src.api.ticketing_client import TicketingAPIClient
        ticketing_client = TicketingAPIClient()
        ticket_data_api = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not ticket_data_api:
            raise HTTPException(status_code=404, detail="Ticket not found in API")

        ticket_details = ticket_data_api[0].get('ticketDetails', [])

        # Build a map of message ID to type
        message_types = {}
        for detail in ticket_details:
            detail_id = detail.get('id')
            source = detail.get('sourceTicketSideTypeId')
            target = detail.get('targetTicketSideTypeId')

            # Determine message type: 1=System/Operator, 2=Customer, 3=Supplier
            if source == 2 and target == 1:
                msg_type = "customer_to_us"
            elif source == 1 and target == 2:
                msg_type = "us_to_customer"
            elif source == 1 and target == 3:
                msg_type = "us_to_supplier"
            elif source == 3 and target == 1:
                msg_type = "supplier_to_us"
            elif source == 1 and target == 1:
                msg_type = "internal_note"
            else:
                msg_type = "unknown"

            message_types[detail_id] = msg_type

        # Get messages from database
        result = db.execute(text("""
            SELECT id, message_body, from_address, processed_at
            FROM processed_emails
            WHERE ticket_id = :ticket_id
            ORDER BY processed_at ASC
        """), {"ticket_id": ticket.id}).fetchall()

        # Helper function to strip HTML and normalize text
        import html
        from html.parser import HTMLParser

        class MLStripper(HTMLParser):
            def __init__(self):
                super().__init__()
                self.reset()
                self.strict = False
                self.convert_charrefs= True
                self.text = []
            def handle_data(self, d):
                self.text.append(d)
            def get_data(self):
                return ''.join(self.text)

        def strip_html_tags(html_text):
            s = MLStripper()
            s.feed(html_text)
            return s.get_data()

        def normalize_for_comparison(text):
            """Normalize text for duplicate detection"""
            if not text:
                return ""
            # Strip HTML
            text = strip_html_tags(text)
            # Decode HTML entities
            text = html.unescape(text)
            # Lowercase and remove extra whitespace
            text = re.sub(r'\s+', ' ', text.lower()).strip()
            # Remove common email artifacts
            text = re.sub(r'http[s]?://\S+', '', text)  # URLs
            text = re.sub(r'[-_]{10,}', '', text)  # Separator lines
            return text

        # Initialize text filter
        text_filter = TextFilter(db)

        # Build structured conversation, excluding ignored messages
        conversation_parts = []
        seen_content = set()  # To detect duplicates

        for msg_id, body, from_addr, created_at in result:
            if msg_id not in request.ignored_message_ids:
                # Extract actual ID from gmail_message_id (format: imported_{ticket_number}_{id})
                detail_id = None
                db_msg = db.execute(text("SELECT gmail_message_id FROM processed_emails WHERE id = :id"),
                                   {"id": msg_id}).fetchone()
                if db_msg:
                    parts = db_msg[0].split('_')
                    if len(parts) >= 3:
                        try:
                            detail_id = int(parts[-1])
                        except:
                            pass

                msg_type = message_types.get(detail_id, "unknown")

                # Apply text filtering to remove boilerplate FIRST
                body_filtered = text_filter.filter_email_body(body or '')

                # Then normalize for duplicate detection
                body_normalized = normalize_for_comparison(body_filtered)

                # Skip if empty after normalization
                if not body_normalized or len(body_normalized) < 20:
                    continue

                # Skip duplicates
                if body_normalized in seen_content:
                    continue

                # Check if this message contains a previous message (email threading)
                is_duplicate = False
                for prev_content in seen_content:
                    if len(prev_content) > 50 and prev_content in body_normalized:
                        is_duplicate = True
                        break

                if is_duplicate:
                    continue

                seen_content.add(body_normalized)

                # Format message with clear label
                if msg_type == "customer_to_us":
                    label = "MESSAGE FROM CUSTOMER"
                elif msg_type == "us_to_customer":
                    label = "OUR RESPONSE TO CUSTOMER"
                elif msg_type == "us_to_supplier":
                    label = "OUR MESSAGE TO SUPPLIER"
                elif msg_type == "supplier_to_us":
                    label = "SUPPLIER'S RESPONSE"
                elif msg_type == "internal_note":
                    label = "INTERNAL NOTE"
                else:
                    label = "MESSAGE"

                conversation_parts.append(f"[{label}] ({created_at})\n{body_normalized}")

        if not conversation_parts:
            raise HTTPException(status_code=400, detail="No messages to analyze (all messages ignored)")

        # Build clean, structured conversation
        combined_body = '\n\n' + '='*80 + '\n\n'.join(conversation_parts)

        # Build email data for AI analysis
        email_data = {
            'subject': f'Ticket {ticket.ticket_number}',
            'body': combined_body,
            'from': ticket.customer_email
        }

        # Build ticket data
        ticket_data_dict = {
            'ticketNumber': ticket.ticket_number,
            'customerName': ticket.customer_name,
            'customerEmail': ticket.customer_email,
            'orderNumber': ticket.order_number,
            'trackingNumber': ticket.tracking_number,
            'carrierName': ticket.carrier_name,
            'supplierName': ticket.supplier_name,
            'items': ticket.product_details
        }

        # If preview_only, build and return the prompt without running analysis
        if request.preview_only:
            from src.ai.ai_engine import AIEngine
            ai_engine = AIEngine()

            # Detect language
            combined_text = f"{email_data['subject']} {email_data['body']}"
            language = ai_engine.language_detector.detect_language(combined_text)
            language_name = ai_engine.language_detector.get_language_name(language)

            # Build the prompt
            prompt = ai_engine._build_analysis_prompt(
                subject=email_data['subject'],
                body=email_data['body'],
                from_address=email_data['from'],
                language=language_name,
                ticket_data=ticket_data_dict,
                ticket_history=None,
                supplier_language=ticket.customer_language
            )

            return {
                "preview": True,
                "system_prompt": ai_engine.system_prompt or "No custom system prompt configured",
                "user_prompt": prompt,
                "email_data": email_data,
                "ticket_data": ticket_data_dict
            }

        # Run AI analysis
        from src.ai.ai_engine import AIEngine
        ai_engine = AIEngine()

        analysis = ai_engine.analyze_email(
            email_data=email_data,
            ticket_data=ticket_data_dict,
            ticket_history=None,
            supplier_language=ticket.customer_language
        )

        # Log AI decision
        new_decision = AIDecisionLog(
            ticket_id=ticket.id,
            detected_language=analysis.get('language'),
            detected_intent=analysis.get('intent'),
            confidence_score=analysis.get('confidence'),
            recommended_action=analysis.get('summary'),
            response_generated=analysis.get('customer_response'),
            action_taken='manual_analysis',
            deployment_phase=settings.deployment_phase
        )
        db.add(new_decision)

        # Update status based on analysis result
        if analysis.get('requires_escalation'):
            update_ticket_status(ticket.ticket_number, 'ESCALATED', db)
        else:
            update_ticket_status(ticket.ticket_number, 'In Progress', db)

        db.commit()

        logger.info("Manual AI analysis completed", ticket_number=ticket_number, decision_id=new_decision.id)

        return {
            "success": True,
            "message": "AI analysis completed",
            "decision_id": new_decision.id,
            "requires_escalation": analysis.get('requires_escalation'),
            "confidence": analysis.get('confidence')
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to analyze ticket", ticket_number=ticket_number, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to analyze ticket: {str(e)}")


@app.post("/api/tickets/{ticket_number}/refresh")
async def refresh_ticket(
    ticket_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Refresh ticket data from ticketing system"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found in local database")

    try:
        # Fetch fresh ticket data from API
        from src.api.ticketing_client import TicketingAPIClient
        ticketing_client = TicketingAPIClient()
        ticket_data = ticketing_client.get_ticket_by_ticket_number(ticket_number)

        if not ticket_data or len(ticket_data) == 0:
            raise HTTPException(status_code=404, detail="Ticket not found in ticketing system")

        ticket_api_data = ticket_data[0]

        # Update basic ticket fields from API
        ticket.ticket_status_id = ticket_api_data.get("ticketStatusId")
        ticket.owner_id = ticket_api_data.get("ownerId")
        ticket.current_state = ticket_api_data.get("ticketStatusName", "unknown")
        ticket.customer_name = ticket_api_data.get("contactName")
        ticket.customer_language = ticket_api_data.get("customerLanguageCultureName", ticket.customer_language)

        # Extract data from salesOrder
        sales_order = ticket_api_data.get("salesOrder", {})
        if sales_order:
            # Use 'reference' field for Amazon order number (e.g., 303-5532872-4861939)
            # Always overwrite if reference exists
            if sales_order.get("reference"):
                ticket.order_number = sales_order.get("reference")
            ticket.customer_email = sales_order.get("customerEmail") or ticket.customer_email

            # Extract delivery customer information
            delivery_name_parts = []
            if sales_order.get("deliveryCustomerName"):
                delivery_name_parts.append(sales_order.get("deliveryCustomerName"))
            if sales_order.get("deliveryCustomerName2"):
                delivery_name_parts.append(sales_order.get("deliveryCustomerName2"))
            if sales_order.get("deliveryCustomerName3"):
                delivery_name_parts.append(sales_order.get("deliveryCustomerName3"))
            if delivery_name_parts:
                ticket.customer_name = " ".join(delivery_name_parts)

            # Extract delivery address
            address_parts = []
            if sales_order.get("deliveryCustomerStreet"):
                address_parts.append(sales_order.get("deliveryCustomerStreet"))
            if sales_order.get("deliveryCustomerStreet2"):
                address_parts.append(sales_order.get("deliveryCustomerStreet2"))
            if address_parts:
                ticket.customer_address = ", ".join(address_parts)

            ticket.customer_city = sales_order.get("deliveryCustomerCity") or ticket.customer_city
            ticket.customer_postal_code = sales_order.get("deliveryCustomerZipCode") or ticket.customer_postal_code
            ticket.customer_country = sales_order.get("deliveryCustomerCountryName") or ticket.customer_country
            ticket.customer_phone = sales_order.get("deliveryCustomerPhoneNumber") or ticket.customer_phone

            # Extract tracking information
            ticket.tracking_number = sales_order.get("trackingNumber") or ticket.tracking_number
            ticket.carrier_name = sales_order.get("carrierName") or ticket.carrier_name
            ticket.delivery_status = sales_order.get("deliveryStatus") or ticket.delivery_status
            ticket.expected_delivery_date = sales_order.get("expectedDeliveryDate") or ticket.expected_delivery_date

            # Extract order financial details
            ticket.order_total = sales_order.get("totalAmount") or ticket.order_total
            ticket.order_currency = sales_order.get("currency") or ticket.order_currency
            ticket.order_date = sales_order.get("orderDate") or ticket.order_date

            # Extract product details
            import json
            sales_order_items = sales_order.get("salesOrderItems", [])
            if sales_order_items:
                products = []
                for item in sales_order_items:
                    products.append({
                        'sku': item.get('sku', ''),
                        'title': item.get('productTitle', ''),
                        'quantity': item.get('quantity', 1),
                        'price': item.get('unitPrice', 0)
                    })
                ticket.product_details = json.dumps(products)

            # Extract purchase order data
            purchase_orders = sales_order.get("purchaseOrders", [])
            if purchase_orders and len(purchase_orders) > 0:
                po_data = purchase_orders[0]
                ticket.purchase_order_number = po_data.get("purchaseOrderNumber") or po_data.get("orderNumber")
                ticket.supplier_name = po_data.get("supplierName") or ticket.supplier_name
                ticket.supplier_email = po_data.get("supplierEmail") or ticket.supplier_email
                ticket.supplier_phone = po_data.get("supplierPhone") or ticket.supplier_phone
                ticket.supplier_contact_person = po_data.get("supplierContactPerson") or ticket.supplier_contact_person

        db.commit()
        db.refresh(ticket)

        logger.info("Ticket refreshed from ticketing system", ticket_number=ticket_number)

        return {
            "success": True,
            "message": "Ticket refreshed successfully",
            "ticket": {
                "ticket_number": ticket.ticket_number,
                "status": ticket.current_state,
                "customer_email": ticket.customer_email,
                "order_number": ticket.order_number,
                "updated_at": ensure_utc(ticket.updated_at)
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to refresh ticket", ticket_number=ticket_number, error=str(e))
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to refresh ticket: {str(e)}")


# Email sending endpoint
class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str
    cc: Optional[List[str]] = None
    bcc: Optional[List[str]] = None
    reply_to_message_id: Optional[str] = None
    thread_id: Optional[str] = None


@app.post("/api/tickets/{ticket_number}/send-email")
async def send_email_via_gmail(
    ticket_number: str,
    to: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...),
    cc: Optional[str] = Form(None),
    bcc: Optional[str] = Form(None),
    thread_id: Optional[str] = Form(None),
    attachments: List[UploadFile] = File(default=[]),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send an email through Gmail API and save to ticket history"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    attachment_paths = []
    try:
        from src.email.gmail_sender import GmailSender
        import os
        import tempfile
        import json

        # Parse CC and BCC if provided as JSON strings
        cc_list = json.loads(cc) if cc else None
        bcc_list = json.loads(bcc) if bcc else None

        # Save attachments temporarily
        if attachments:
            temp_dir = tempfile.mkdtemp()
            for file in attachments:
                if file.filename:
                    file_path = os.path.join(temp_dir, file.filename)
                    content = await file.read()
                    with open(file_path, 'wb') as f:
                        f.write(content)
                    attachment_paths.append(file_path)

        gmail_sender = GmailSender()
        result = gmail_sender.send_email(
            to=to,
            subject=subject,
            body=body,
            cc=cc_list,
            bcc=bcc_list,
            attachments=attachment_paths if attachment_paths else None,
            reply_to_message_id=None,
            thread_id=thread_id
        )

        # Save sent message to ticket history
        sent_message = ProcessedEmail(
            gmail_message_id=result.get('id'),
            gmail_thread_id=result.get('threadId') or thread_id,
            ticket_id=ticket.id,
            order_number=ticket.order_number,
            subject=subject,
            from_address=settings.gmail_support_email,  # Our email address
            message_body=body,
            success=True,
            processed_at=datetime.now(timezone.utc)
        )
        db.add(sent_message)
        db.commit()
        db.refresh(sent_message)

        # Save attachments to database
        saved_attachments = []
        if attachments and attachment_paths:
            from pathlib import Path
            import mimetypes
            import uuid
            from src.email.text_extractor import TextExtractor

            base_dir = Path(settings.attachments_dir if hasattr(settings, 'attachments_dir') else 'attachments')
            email_dir = base_dir / f"email_{ticket_number}"
            email_dir.mkdir(parents=True, exist_ok=True)

            text_extractor = TextExtractor()

            for idx, file in enumerate(attachments):
                if file.filename and idx < len(attachment_paths):
                    # Generate unique filename
                    unique_id = uuid.uuid4().hex[:8]
                    safe_filename = f"{unique_id}_{file.filename}"
                    dest_path = email_dir / safe_filename
                    relative_path = f"email_{ticket_number}/{safe_filename}"

                    # Copy from temp to permanent location
                    import shutil
                    shutil.copy2(attachment_paths[idx], dest_path)

                    # Get mime type
                    mime_type, _ = mimetypes.guess_type(file.filename)
                    file_size = os.path.getsize(dest_path)

                    # Try to extract text
                    extracted_text = None
                    extraction_status = 'pending'
                    extraction_error = None
                    try:
                        extracted_text = text_extractor.extract_text(str(dest_path))
                        if extracted_text:
                            extraction_status = 'completed'
                        else:
                            extraction_status = 'skipped'
                    except Exception as ex:
                        logger.warning(f"Failed to extract text from sent attachment: {ex}")
                        extraction_status = 'failed'
                        extraction_error = str(ex)

                    # Create attachment record
                    attachment_record = Attachment(
                        ticket_id=ticket.id,
                        gmail_message_id=result.get('id'),
                        processed_email_id=sent_message.id,
                        filename=safe_filename,
                        original_filename=file.filename,
                        file_path=relative_path,
                        mime_type=mime_type,
                        file_size=file_size,
                        extracted_text=extracted_text,
                        extraction_status=extraction_status,
                        extraction_error=extraction_error,
                        uploaded_by_user_id=current_user.id
                    )
                    db.add(attachment_record)
                    saved_attachments.append(file.filename)

            db.commit()

        logger.info(
            "Email sent via Gmail and saved to history",
            ticket_number=ticket_number,
            to=to,
            subject=subject,
            message_id=result.get('id'),
            attachment_count=len(attachment_paths),
            saved_attachments=len(saved_attachments)
        )

        return {
            "success": True,
            "message_id": result.get('id'),
            "thread_id": result.get('threadId'),
            "attachments_saved": len(saved_attachments)
        }

    except Exception as e:
        db.rollback()
        logger.error("Failed to send email", ticket_number=ticket_number, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
    finally:
        # Clean up temporary files
        import shutil
        for file_path in attachment_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                # Clean up temp directory if empty
                temp_dir = os.path.dirname(file_path)
                if os.path.exists(temp_dir) and not os.listdir(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp file: {e}")


# Internal note endpoint
class InternalNoteRequest(BaseModel):
    subject: str
    body: str


@app.post("/api/tickets/{ticket_number}/internal-note")
async def save_internal_note(
    ticket_number: str,
    request: InternalNoteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Save an internal note to ticket history"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    try:
        # Create a unique message ID for internal note
        import uuid
        internal_msg_id = f"internal_{ticket_number}_{uuid.uuid4().hex[:8]}"

        # Get gmail_thread_id from most recent email for this ticket
        recent_email = db.query(ProcessedEmail).filter(
            ProcessedEmail.ticket_id == ticket.id
        ).order_by(ProcessedEmail.processed_at.desc()).first()

        gmail_thread_id = recent_email.gmail_thread_id if recent_email else None

        # Save internal note to ticket history
        internal_note = ProcessedEmail(
            gmail_message_id=internal_msg_id,
            gmail_thread_id=gmail_thread_id,
            ticket_id=ticket.id,
            order_number=ticket.order_number,
            subject=request.subject,
            from_address="Internal",
            message_body=request.body,
            success=True,
            processed_at=datetime.now(timezone.utc)
        )
        db.add(internal_note)
        db.commit()

        logger.info(
            "Internal note saved",
            ticket_number=ticket_number,
            subject=request.subject,
            message_id=internal_msg_id
        )

        return {
            "success": True,
            "message_id": internal_msg_id
        }

    except Exception as e:
        db.rollback()
        logger.error("Failed to save internal note", ticket_number=ticket_number, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save internal note: {str(e)}")


# Attachment endpoints
@app.get("/api/tickets/{ticket_number}/attachments")
async def get_ticket_attachments(
    ticket_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> List[AttachmentInfo]:
    """Get all attachments for a ticket"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    attachments = db.query(Attachment).filter(
        Attachment.ticket_id == ticket.id
    ).order_by(Attachment.created_at.desc()).all()

    return [
        AttachmentInfo(
            id=att.id,
            ticket_id=att.ticket_id,
            filename=att.filename,
            original_filename=att.original_filename,
            mime_type=att.mime_type,
            file_size=att.file_size,
            extraction_status=att.extraction_status,
            extracted_text=att.extracted_text,
            created_at=att.created_at,
            gmail_message_id=att.gmail_message_id
        )
        for att in attachments
    ]


@app.get("/api/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download an attachment file"""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Build full file path
    import os
    from pathlib import Path

    # Attachments are stored in attachments directory
    base_dir = Path(settings.attachments_dir if hasattr(settings, 'attachments_dir') else 'attachments')
    file_path = base_dir / attachment.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=attachment.original_filename,
        media_type=attachment.mime_type or 'application/octet-stream'
    )


@app.get("/api/attachments/{attachment_id}/view")
async def view_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """View/preview an attachment file inline (for images)"""
    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    # Build full file path
    import os
    from pathlib import Path

    # Attachments are stored in attachments directory
    base_dir = Path(settings.attachments_dir if hasattr(settings, 'attachments_dir') else 'attachments')
    file_path = base_dir / attachment.file_path

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Attachment file not found on disk")

    # Return file for inline display (without Content-Disposition header forcing download)
    return FileResponse(
        path=str(file_path),
        media_type=attachment.mime_type or 'application/octet-stream',
        headers={"Content-Disposition": f"inline; filename=\"{attachment.original_filename}\""}
    )


@app.post("/api/tickets/{ticket_number}/attachments/upload")
async def upload_attachment(
    ticket_number: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload an attachment to a ticket"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    try:
        import os
        import mimetypes
        from pathlib import Path
        import uuid
        from src.email.text_extractor import TextExtractor

        # Validate file type (extension)
        allowed_extensions = {'.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.docx', '.txt', '.csv', '.xlsx', '.xls', '.gif', '.webp'}
        file_ext = Path(file.filename).suffix.lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type '{file_ext}' not allowed. Allowed types: PDF, images (JPG, PNG, GIF, TIFF, BMP, WebP), documents (DOCX, TXT, CSV, XLSX)"
            )

        # Block dangerous file types (extra safety check)
        dangerous_extensions = {'.exe', '.bat', '.sh', '.cmd', '.com', '.scr', '.vbs', '.js', '.jar', '.app', '.dmg', '.msi', '.dll', '.so', '.dylib'}
        if file_ext in dangerous_extensions:
            raise HTTPException(
                status_code=400,
                detail="Executable files are not allowed for security reasons"
            )

        # Validate file size (100MB max)
        max_size = 100 * 1024 * 1024  # 100MB
        file_content = await file.read()
        if len(file_content) > max_size:
            raise HTTPException(status_code=400, detail="File size exceeds 100MB limit")

        # Create upload directory for this ticket
        base_dir = Path(settings.attachments_dir if hasattr(settings, 'attachments_dir') else 'attachments')
        upload_dir = base_dir / f"uploaded_{ticket_number}"
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        unique_id = uuid.uuid4().hex[:8]
        safe_filename = f"{unique_id}_{file.filename}"
        file_path = upload_dir / safe_filename

        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)

        # Get mime type
        mime_type, _ = mimetypes.guess_type(file.filename)

        # Extract text if possible
        text_extractor = TextExtractor()
        extracted_text = None
        extraction_status = 'pending'
        extraction_error = None

        try:
            extracted_text = text_extractor.extract_text(str(file_path))
            if extracted_text:
                extraction_status = 'completed'
            else:
                extraction_status = 'skipped'
        except Exception as e:
            logger.warning("Failed to extract text from uploaded file",
                         filename=file.filename,
                         error=str(e))
            extraction_status = 'failed'
            extraction_error = str(e)

        # Create relative path
        relative_path = f"uploaded_{ticket_number}/{safe_filename}"

        # Create attachment record
        attachment = Attachment(
            ticket_id=ticket.id,
            gmail_message_id=None,  # Manually uploaded
            processed_email_id=None,
            filename=safe_filename,
            original_filename=file.filename,
            file_path=relative_path,
            mime_type=mime_type,
            file_size=len(file_content),
            extracted_text=extracted_text,
            extraction_status=extraction_status,
            extraction_error=extraction_error,
            uploaded_by_user_id=current_user.id
        )

        db.add(attachment)
        db.commit()
        db.refresh(attachment)

        logger.info("Attachment uploaded",
                   ticket_number=ticket_number,
                   filename=file.filename,
                   size=len(file_content),
                   user=current_user.username)

        return AttachmentInfo(
            id=attachment.id,
            ticket_id=attachment.ticket_id,
            filename=attachment.filename,
            original_filename=attachment.original_filename,
            mime_type=attachment.mime_type,
            file_size=attachment.file_size,
            extraction_status=attachment.extraction_status,
            extracted_text=attachment.extracted_text,
            created_at=attachment.created_at,
            gmail_message_id=attachment.gmail_message_id
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to upload attachment",
                    ticket_number=ticket_number,
                    filename=file.filename,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to upload attachment: {str(e)}")


@app.delete("/api/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an attachment"""
    # Only allow operators and admins to delete
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    attachment = db.query(Attachment).filter(Attachment.id == attachment_id).first()

    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    try:
        import os
        from pathlib import Path

        # Delete file from disk
        base_dir = Path(settings.attachments_dir if hasattr(settings, 'attachments_dir') else 'attachments')
        file_path = base_dir / attachment.file_path

        if file_path.exists():
            os.remove(file_path)

        # Delete database record
        db.delete(attachment)
        db.commit()

        logger.info("Attachment deleted",
                   attachment_id=attachment_id,
                   filename=attachment.filename,
                   user=current_user.username)

        return {"success": True, "message": "Attachment deleted"}

    except Exception as e:
        db.rollback()
        logger.error("Failed to delete attachment",
                    attachment_id=attachment_id,
                    error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete attachment: {str(e)}")


# Audit Log endpoints
@app.get("/api/tickets/{ticket_number}/audit-logs")
async def get_ticket_audit_logs(
    ticket_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100
) -> List[TicketAuditLogInfo]:
    """Get audit log for a ticket"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    logs = db.query(TicketAuditLog).filter(
        TicketAuditLog.ticket_id == ticket.id
    ).order_by(TicketAuditLog.created_at.desc()).limit(limit).all()

    return [
        TicketAuditLogInfo(
            id=log.id,
            ticket_id=log.ticket_id,
            user_id=log.user_id,
            username=log.user.username if log.user else "System",
            action_type=log.action_type,
            action_description=log.action_description,
            field_name=log.field_name,
            old_value=log.old_value,
            new_value=log.new_value,
            metadata=log.metadata,
            created_at=log.created_at
        )
        for log in logs
    ]


# AI Decision Log endpoints
@app.get("/api/ai-decisions")
async def get_ai_decisions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """Get list of AI decisions with total count"""
    # Get total count
    total = db.query(func.count(AIDecisionLog.id)).scalar()

    # Get paginated results
    decisions = db.query(AIDecisionLog).order_by(
        AIDecisionLog.timestamp.desc()
    ).offset(offset).limit(limit).all()

    return {
        "total": total,
        "items": [
            AIDecisionInfo(
                id=dec.id,
                ticket_number=dec.ticket.ticket_number,
                timestamp=dec.timestamp,
                detected_language=dec.detected_language,
                detected_intent=dec.detected_intent,
                confidence_score=dec.confidence_score,
                action_taken=dec.action_taken,
                deployment_phase=dec.deployment_phase
            )
            for dec in decisions
        ]
    }


class FeedbackSubmission(BaseModel):
    feedback: str  # 'correct', 'incorrect', 'partially_correct'
    feedback_notes: Optional[str] = None


class FeedbackUpdate(BaseModel):
    feedback_notes: Optional[str] = None
    addressed: Optional[bool] = None


@app.post("/api/ai-decisions/{decision_id}/feedback")
async def submit_feedback(
    decision_id: int,
    feedback_data: FeedbackSubmission,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback on AI decision"""
    decision = db.query(AIDecisionLog).filter(AIDecisionLog.id == decision_id).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.feedback = feedback_data.feedback
    decision.feedback_notes = feedback_data.feedback_notes
    db.commit()

    logger.info("Feedback submitted", decision_id=decision_id, feedback=feedback_data.feedback, user=current_user.username)

    return {"success": True, "message": "Feedback recorded"}


@app.get("/api/feedback")
async def get_feedback(
    filter: str = 'all',  # 'all' or 'unaddressed'
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all feedback items"""
    query = db.query(AIDecisionLog).filter(AIDecisionLog.feedback == 'incorrect')

    if filter == 'unaddressed':
        # Check if addressed column exists, otherwise assume False
        try:
            query = query.filter(AIDecisionLog.addressed == False)
        except:
            pass  # Column might not exist yet

    decisions = query.order_by(AIDecisionLog.timestamp.desc()).offset(offset).limit(limit).all()

    return [
        {
            "id": dec.id,
            "ticket_number": dec.ticket.ticket_number,
            "timestamp": ensure_utc(dec.timestamp),
            "detected_intent": dec.detected_intent,
            "detected_language": dec.detected_language,
            "response_generated": dec.response_generated,
            "feedback": dec.feedback,
            "feedback_notes": dec.feedback_notes,
            "addressed": getattr(dec, 'addressed', False)
        }
        for dec in decisions
    ]


@app.patch("/api/feedback/{decision_id}")
async def update_feedback(
    decision_id: int,
    update_data: FeedbackUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update feedback notes or addressed status"""
    decision = db.query(AIDecisionLog).filter(AIDecisionLog.id == decision_id).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    if update_data.feedback_notes is not None:
        decision.feedback_notes = update_data.feedback_notes

    if update_data.addressed is not None:
        try:
            decision.addressed = update_data.addressed
        except AttributeError:
            pass  # Column might not exist yet

    db.commit()

    logger.info("Feedback updated", decision_id=decision_id, user=current_user.username)

    return {"success": True, "message": "Feedback updated"}


@app.delete("/api/feedback/{decision_id}")
async def delete_feedback(
    decision_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete feedback (clear feedback fields)"""
    decision = db.query(AIDecisionLog).filter(AIDecisionLog.id == decision_id).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.feedback = None
    decision.feedback_notes = None
    try:
        decision.addressed = False
    except AttributeError:
        pass

    db.commit()

    logger.info("Feedback deleted", decision_id=decision_id, user=current_user.username)

    return {"success": True, "message": "Feedback deleted"}


# Prompt improvement endpoints
@app.post("/api/prompt/analyze-feedback")
async def analyze_feedback_for_prompt_improvement(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Use Claude to analyze unaddressed feedback and suggest prompt improvements
    Returns suggested improvements with explanations
    """
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(status_code=403, detail="Operator or admin access required")

    try:
        # Get all unaddressed feedback
        unaddressed_feedback = db.query(AIDecisionLog).filter(
            AIDecisionLog.feedback == 'incorrect',
            AIDecisionLog.addressed == False
        ).all()

        if not unaddressed_feedback:
            return {
                "success": True,
                "feedback_count": 0,
                "message": "No unaddressed feedback found",
                "suggestions": []
            }

        # Load current system prompt
        import os
        from pathlib import Path

        if hasattr(settings, 'prompt_path') and settings.prompt_path:
            prompt_path = Path(settings.prompt_path)
            if not prompt_path.is_absolute():
                prompt_path = Path(os.getcwd()) / prompt_path
        else:
            prompt_path = Path(os.getcwd()) / "prompts" / "system_prompt.txt"

        current_prompt = ""
        if prompt_path.exists():
            current_prompt = prompt_path.read_text(encoding='utf-8')
        else:
            raise HTTPException(status_code=404, detail="System prompt file not found")

        # Prepare feedback summary for AI analysis
        feedback_summary = []
        for item in unaddressed_feedback:
            ticket = item.ticket
            feedback_summary.append({
                "ticket_number": ticket.ticket_number if ticket else "Unknown",
                "detected_intent": item.detected_intent,
                "detected_language": item.detected_language,
                "confidence": item.confidence_score,
                "ai_response": item.response_generated[:200] if item.response_generated else "",
                "feedback_notes": item.feedback_notes or "No specific notes",
                "timestamp": item.timestamp.isoformat() if item.timestamp else ""
            })

        # Use AI to analyze patterns and suggest improvements
        ai_engine = AIEngine()

        analysis_prompt = f"""You are an AI prompt engineering expert. Analyze the following feedback on an AI support agent's performance and suggest improvements to the system prompt.

CURRENT SYSTEM PROMPT:
{current_prompt}

FEEDBACK ON INCORRECT AI DECISIONS (Total: {len(feedback_summary)}):
{chr(10).join([f"- Ticket {f['ticket_number']}: Intent={f['detected_intent']}, Language={f['detected_language']}, Notes: {f['feedback_notes']}" for f in feedback_summary[:20]])}

Analyze the patterns in the feedback and provide:
1. **Key Issues**: What are the main problems the AI is having? (2-3 bullet points)
2. **Suggested Changes**: Specific, actionable changes to the system prompt (be concrete, not vague)
3. **Improved Prompt Section**: Write the specific sections of the prompt that need to be changed (use markdown code blocks)

Focus on the most impactful improvements. Be specific and concrete."""

        analysis_result = ai_engine.provider.generate_response(
            prompt=analysis_prompt,
            temperature=0.3
        )

        logger.info(
            "Prompt improvement analysis completed",
            feedback_count=len(feedback_summary),
            user=current_user.username
        )

        return {
            "success": True,
            "feedback_count": len(feedback_summary),
            "analysis": analysis_result,
            "feedback_items": feedback_summary
        }

    except Exception as e:
        logger.error("Failed to analyze feedback", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to analyze feedback: {str(e)}")


@app.post("/api/prompt/generate-improved")
async def generate_improved_prompt(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a complete improved prompt based on feedback analysis
    Uses Claude to rewrite the entire prompt incorporating feedback
    """
    if current_user.role not in ['admin', 'operator']:
        raise HTTPException(status_code=403, detail="Operator or admin access required")

    try:
        # Get all unaddressed feedback
        unaddressed_feedback = db.query(AIDecisionLog).filter(
            AIDecisionLog.feedback == 'incorrect',
            AIDecisionLog.addressed == False
        ).all()

        if not unaddressed_feedback:
            return {
                "success": False,
                "message": "No unaddressed feedback found to improve from"
            }

        # Load current system prompt
        import os
        from pathlib import Path

        if hasattr(settings, 'prompt_path') and settings.prompt_path:
            prompt_path = Path(settings.prompt_path)
            if not prompt_path.is_absolute():
                prompt_path = Path(os.getcwd()) / prompt_path
        else:
            prompt_path = Path(os.getcwd()) / "prompts" / "system_prompt.txt"

        current_prompt = ""
        if prompt_path.exists():
            current_prompt = prompt_path.read_text(encoding='utf-8')
        else:
            raise HTTPException(status_code=404, detail="System prompt file not found")

        # Prepare feedback summary
        feedback_summary = []
        for item in unaddressed_feedback:
            ticket = item.ticket
            feedback_summary.append({
                "ticket_number": ticket.ticket_number if ticket else "Unknown",
                "detected_intent": item.detected_intent,
                "detected_language": item.detected_language,
                "feedback_notes": item.feedback_notes or "No specific notes",
            })

        # Use AI to generate improved prompt
        ai_engine = AIEngine()

        improvement_prompt = f"""You are an AI prompt engineering expert. Improve the following system prompt based on operator feedback about incorrect AI decisions.

CURRENT SYSTEM PROMPT:
{current_prompt}

FEEDBACK ON ISSUES (Total: {len(feedback_summary)}):
{chr(10).join([f"- Ticket {f['ticket_number']}: {f['feedback_notes']}" for f in feedback_summary[:30]])}

Rewrite the ENTIRE system prompt to address these issues. Key improvements to make:
1. Make instructions more explicit and actionable
2. Add specific examples for problematic cases
3. Emphasize critical requirements that were missed
4. Keep the structure and tone, but improve clarity and specificity

Return ONLY the improved system prompt text. Do not include any preamble or explanation."""

        improved_prompt = ai_engine.provider.generate_response(
            prompt=improvement_prompt,
            temperature=0.3
        )

        logger.info(
            "Improved prompt generated",
            feedback_count=len(feedback_summary),
            user=current_user.username
        )

        return {
            "success": True,
            "current_prompt": current_prompt,
            "improved_prompt": improved_prompt,
            "feedback_count": len(feedback_summary)
        }

    except Exception as e:
        logger.error("Failed to generate improved prompt", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate improved prompt: {str(e)}")


@app.post("/api/prompt/approve")
async def approve_prompt_version(
    request: PromptApprovalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Approve and deploy a new prompt version
    Saves the prompt, creates version record, marks feedback as addressed
    """
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        from src.database.models import PromptVersion
        import os
        from pathlib import Path

        # Get count of unaddressed feedback that will be addressed by this version
        unaddressed_count = db.query(func.count(AIDecisionLog.id)).filter(
            AIDecisionLog.feedback == 'incorrect',
            AIDecisionLog.addressed == False
        ).scalar()

        # Get next version number
        latest_version = db.query(func.max(PromptVersion.version_number)).scalar() or 0
        new_version_number = latest_version + 1

        # Deactivate current active version
        db.query(PromptVersion).filter(PromptVersion.is_active == True).update({"is_active": False})

        # Create new prompt version record
        new_version = PromptVersion(
            version_number=new_version_number,
            prompt_text=request.new_prompt,
            created_by=current_user.username,
            change_summary=request.change_summary,
            feedback_count=unaddressed_count,
            is_active=True
        )
        db.add(new_version)

        # Mark all unaddressed feedback as addressed
        db.query(AIDecisionLog).filter(
            AIDecisionLog.feedback == 'incorrect',
            AIDecisionLog.addressed == False
        ).update({"addressed": True})

        # Save new prompt to file
        if hasattr(settings, 'prompt_path') and settings.prompt_path:
            prompt_path = Path(settings.prompt_path)
            if not prompt_path.is_absolute():
                prompt_path = Path(os.getcwd()) / prompt_path
        else:
            prompt_path = Path(os.getcwd()) / "prompts" / "system_prompt.txt"

        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt_path.write_text(request.new_prompt, encoding='utf-8')

        db.commit()

        logger.info(
            "New prompt version approved and deployed",
            version=new_version_number,
            feedback_addressed=unaddressed_count,
            user=current_user.username
        )

        return {
            "success": True,
            "version": new_version_number,
            "feedback_addressed": unaddressed_count,
            "message": f"Prompt v{new_version_number} deployed successfully. {unaddressed_count} feedback items marked as addressed."
        }

    except Exception as e:
        db.rollback()
        logger.error("Failed to approve prompt version", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to approve prompt: {str(e)}")


# Settings endpoints
@app.get("/api/settings")
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get current system settings"""
    import os
    from pathlib import Path

    # Load system prompt if it exists
    system_prompt = None
    try:
        # Try to load from prompt_path setting
        if hasattr(settings, 'prompt_path') and settings.prompt_path:
            prompt_path = Path(settings.prompt_path)
            # If it's not absolute, make it relative to current directory
            if not prompt_path.is_absolute():
                prompt_path = Path(os.getcwd()) / prompt_path
        else:
            # Fallback to default location
            prompt_path = Path(os.getcwd()) / "prompts" / "system_prompt.txt"

        if prompt_path.exists():
            system_prompt = prompt_path.read_text(encoding='utf-8')
    except Exception as e:
        logger.warning("Could not load system prompt", error=str(e))

    return {
        "deployment_phase": settings.deployment_phase,
        "confidence_threshold": settings.confidence_threshold,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "ai_temperature": settings.ai_temperature,
        "ai_max_tokens": settings.ai_max_tokens,
        "retry_enabled": getattr(settings, 'retry_enabled', True),
        "retry_max_attempts": getattr(settings, 'retry_max_attempts', 3),
        "retry_delay_minutes": getattr(settings, 'retry_delay_minutes', 30),
        "gmail_check_interval": getattr(settings, 'gmail_check_interval', 60),
        "system_prompt": system_prompt
    }


@app.patch("/api/settings")
async def update_settings(
    updates: SettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update system settings (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    # Update .env file with new settings
    import os
    from pathlib import Path

    env_path = Path(os.getcwd()) / ".env"
    changes_made = []

    try:
        # Read current .env file
        if env_path.exists():
            with open(env_path, 'r') as f:
                lines = f.readlines()
        else:
            lines = []

        # Update lines with new values
        updated_lines = []
        keys_updated = set()

        for line in lines:
            line_updated = False
            if updates.deployment_phase is not None and line.startswith('DEPLOYMENT_PHASE='):
                updated_lines.append(f'DEPLOYMENT_PHASE={updates.deployment_phase}\n')
                keys_updated.add('DEPLOYMENT_PHASE')
                changes_made.append(f'deployment_phase={updates.deployment_phase}')
                line_updated = True
            elif updates.confidence_threshold is not None and line.startswith('CONFIDENCE_THRESHOLD='):
                updated_lines.append(f'CONFIDENCE_THRESHOLD={updates.confidence_threshold}\n')
                keys_updated.add('CONFIDENCE_THRESHOLD')
                changes_made.append(f'confidence_threshold={updates.confidence_threshold}')
                line_updated = True
            elif updates.ai_temperature is not None and line.startswith('AI_TEMPERATURE='):
                updated_lines.append(f'AI_TEMPERATURE={updates.ai_temperature}\n')
                keys_updated.add('AI_TEMPERATURE')
                changes_made.append(f'ai_temperature={updates.ai_temperature}')
                line_updated = True
            elif updates.ai_model is not None and line.startswith('AI_MODEL='):
                updated_lines.append(f'AI_MODEL={updates.ai_model}\n')
                keys_updated.add('AI_MODEL')
                changes_made.append(f'ai_model={updates.ai_model}')
                line_updated = True
            elif updates.ai_max_tokens is not None and line.startswith('AI_MAX_TOKENS='):
                updated_lines.append(f'AI_MAX_TOKENS={updates.ai_max_tokens}\n')
                keys_updated.add('AI_MAX_TOKENS')
                changes_made.append(f'ai_max_tokens={updates.ai_max_tokens}')
                line_updated = True

            if not line_updated:
                updated_lines.append(line)

        # Add new keys that weren't in the file
        if updates.deployment_phase is not None and 'DEPLOYMENT_PHASE' not in keys_updated:
            updated_lines.append(f'DEPLOYMENT_PHASE={updates.deployment_phase}\n')
            changes_made.append(f'deployment_phase={updates.deployment_phase}')
        if updates.confidence_threshold is not None and 'CONFIDENCE_THRESHOLD' not in keys_updated:
            updated_lines.append(f'CONFIDENCE_THRESHOLD={updates.confidence_threshold}\n')
            changes_made.append(f'confidence_threshold={updates.confidence_threshold}')
        if updates.ai_temperature is not None and 'AI_TEMPERATURE' not in keys_updated:
            updated_lines.append(f'AI_TEMPERATURE={updates.ai_temperature}\n')
            changes_made.append(f'ai_temperature={updates.ai_temperature}')
        if updates.ai_model is not None and 'AI_MODEL' not in keys_updated:
            updated_lines.append(f'AI_MODEL={updates.ai_model}\n')
            changes_made.append(f'ai_model={updates.ai_model}')
        if updates.ai_max_tokens is not None and 'AI_MAX_TOKENS' not in keys_updated:
            updated_lines.append(f'AI_MAX_TOKENS={updates.ai_max_tokens}\n')
            changes_made.append(f'ai_max_tokens={updates.ai_max_tokens}')

        # Write back to file
        with open(env_path, 'w') as f:
            f.writelines(updated_lines)

        # Handle system prompt separately
        if updates.system_prompt is not None:
            if hasattr(settings, 'prompt_path') and settings.prompt_path:
                prompt_path = Path(settings.prompt_path)
                if not prompt_path.is_absolute():
                    prompt_path = Path(os.getcwd()) / prompt_path
            else:
                prompt_path = Path(os.getcwd()) / "prompts" / "system_prompt.txt"

            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            prompt_path.write_text(updates.system_prompt, encoding='utf-8')
            changes_made.append('system_prompt updated')

        logger.info(
            "Settings updated",
            changes=changes_made,
            user=current_user.username
        )

        # Reload settings from environment
        try:
            import importlib
            import sys
            # Remove cached module
            if 'config.settings' in sys.modules:
                del sys.modules['config.settings']
            # Reload environment variables
            from dotenv import load_dotenv
            load_dotenv(override=True)
            # Import fresh settings
            from config import settings as new_settings
            logger.info("Settings reloaded from .env file")
        except Exception as reload_error:
            logger.warning("Failed to reload settings in memory", error=str(reload_error))

        return {
            "success": True,
            "message": f"Settings updated successfully. Changes: {', '.join(changes_made)}. Restart AI agent service to apply changes.",
            "changes": changes_made
        }
    except Exception as e:
        logger.error("Failed to update settings", error=str(e), user=current_user.username)
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


# User Management endpoints
@app.get("/api/users", response_model=List[UserInfo])
async def get_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get list of all users (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    users = db.query(User).order_by(User.created_at.desc()).all()

    return [
        UserInfo(
            id=user.id,
            username=user.username,
            email=user.email,
            role=user.role,
            created_at=ensure_utc(user.created_at)
        )
        for user in users
    ]


@app.post("/api/users")
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    # Check if username or email already exists
    existing = db.query(User).filter(
        (User.username == user_data.username) | (User.email == user_data.email)
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="Username or email already exists")

    # Validate role
    if user_data.role not in ['admin', 'operator', 'viewer']:
        raise HTTPException(status_code=400, detail="Invalid role. Must be admin, operator, or viewer")

    # Create new user
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role,
        full_name=user_data.full_name,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info("User created", username=user_data.username, role=user_data.role, by=current_user.username)

    return {
        "success": True,
        "message": f"User {user_data.username} created successfully",
        "user_id": new_user.id
    }


@app.patch("/api/users/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user information (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields if provided
    if user_data.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(User.email == user_data.email, User.id != user_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already in use")
        user.email = user_data.email

    if user_data.password is not None:
        user.password_hash = get_password_hash(user_data.password)

    if user_data.role is not None:
        if user_data.role not in ['admin', 'operator', 'viewer']:
            raise HTTPException(status_code=400, detail="Invalid role")
        user.role = user_data.role

    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    db.commit()

    logger.info("User updated", user_id=user_id, username=user.username, by=current_user.username)

    return {
        "success": True,
        "message": f"User {user.username} updated successfully"
    }


@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    # Prevent deleting yourself
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    username = user.username
    db.delete(user)
    db.commit()

    logger.info("User deleted", user_id=user_id, username=username, by=current_user.username)

    return {
        "success": True,
        "message": f"User {username} deleted successfully"
    }


# Supplier Management Endpoints

@app.get("/api/suppliers")
async def get_suppliers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all suppliers"""
    from src.database.models import Supplier

    suppliers = db.query(Supplier).order_by(Supplier.name).all()

    return [{
        "id": s.id,
        "supplier_number": s.supplier_number,
        "name": s.name,
        "default_email": s.default_email,
        "language_code": s.language_code,
        "contact_fields": s.contact_fields or {},
        "created_at": s.created_at.isoformat() if s.created_at else None
    } for s in suppliers]


@app.post("/api/suppliers")
async def create_supplier(
    supplier_number: int = Form(...),
    name: str = Form(...),
    default_email: str = Form(...),
    language_code: str = Form("de-DE"),
    contact_fields: str = Form("{}"),  # JSON string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new supplier (requires operator or admin role)"""
    if current_user.role not in ['operator', 'admin']:
        raise HTTPException(status_code=403, detail="Operator or admin access required")

    from src.database.models import Supplier
    import json

    # Check if supplier already exists
    existing = db.query(Supplier).filter(Supplier.supplier_number == supplier_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier with this number already exists")

    # Parse contact_fields JSON
    try:
        contact_fields_dict = json.loads(contact_fields)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON for contact_fields")

    supplier = Supplier(
        supplier_number=supplier_number,
        name=name,
        default_email=default_email,
        language_code=language_code,
        contact_fields=contact_fields_dict
    )

    db.add(supplier)
    db.commit()
    db.refresh(supplier)

    logger.info("Supplier created", supplier_number=supplier_number, supplier_name=name, by=current_user.username)

    return {
        "success": True,
        "message": f"Supplier {name} created successfully",
        "supplier": {
            "id": supplier.id,
            "supplier_number": supplier.supplier_number,
            "name": supplier.name,
            "default_email": supplier.default_email,
            "language_code": supplier.language_code,
            "contact_fields": supplier.contact_fields or {}
        }
    }


@app.patch("/api/suppliers/{supplier_id}")
async def update_supplier(
    supplier_id: int,
    default_email: str = Form(None),
    language_code: str = Form(None),
    contact_fields: str = Form(None),  # JSON string
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update supplier information (requires operator or admin role)"""
    if current_user.role not in ['operator', 'admin']:
        raise HTTPException(status_code=403, detail="Operator or admin access required")

    from src.database.models import Supplier
    import json

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # Update fields if provided
    if default_email is not None:
        supplier.default_email = default_email

    if language_code is not None:
        supplier.language_code = language_code

    if contact_fields is not None:
        try:
            contact_fields_dict = json.loads(contact_fields)
            supplier.contact_fields = contact_fields_dict
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON for contact_fields")

    db.commit()

    logger.info("Supplier updated", supplier_id=supplier_id, supplier_name=supplier.name, by=current_user.username)

    return {
        "success": True,
        "message": f"Supplier {supplier.name} updated successfully"
    }


@app.delete("/api/suppliers/{supplier_id}")
async def delete_supplier(
    supplier_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a supplier (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    from src.database.models import Supplier

    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    supplier_name = supplier.name
    db.delete(supplier)
    db.commit()

    logger.info("Supplier deleted", supplier_id=supplier_id, supplier_name=supplier_name, by=current_user.username)

    return {
        "success": True,
        "message": f"Supplier {supplier_name} deleted successfully"
    }


@app.post("/api/services/restart")
async def restart_services(
    current_user: User = Depends(get_current_user)
):
    """Restart the AI agent services (requires admin role)"""
    if current_user.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    import subprocess

    services = ['ai-agent', 'ai-agent-api']
    results = {}

    for service in services:
        try:
            # Run systemctl restart command
            result = subprocess.run(
                ['sudo', 'systemctl', 'restart', service],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                results[service] = {'success': True, 'message': f'{service} restarted successfully'}
                logger.info(f"Service restarted", service=service, by=current_user.username)
            else:
                results[service] = {'success': False, 'message': f'Failed to restart {service}: {result.stderr}'}
                logger.error(f"Service restart failed", service=service, error=result.stderr)
        except subprocess.TimeoutExpired:
            results[service] = {'success': False, 'message': f'Restart of {service} timed out'}
            logger.error(f"Service restart timeout", service=service)
        except Exception as e:
            results[service] = {'success': False, 'message': f'Error restarting {service}: {str(e)}'}
            logger.error(f"Service restart error", service=service, error=str(e))

    # Check if all succeeded
    all_success = all(r['success'] for r in results.values())

    return {
        "success": all_success,
        "services": results,
        "message": "All services restarted successfully" if all_success else "Some services failed to restart"
    }


# WebSocket for real-time logs
class ConnectionManager:
    """Manage WebSocket connections"""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                pass


manager = ConnectionManager()


# Text Filter endpoints
@app.get("/api/text-filters/skip-blocks")
async def get_skip_text_blocks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all skip text block patterns"""
    from src.database.models import SkipTextBlock
    blocks = db.query(SkipTextBlock).order_by(SkipTextBlock.created_at.desc()).all()
    return [
        {
            "id": block.id,
            "pattern": block.pattern,
            "description": block.description,
            "is_regex": block.is_regex,
            "enabled": block.enabled,
            "created_at": ensure_utc(block.created_at)
        }
        for block in blocks
    ]


@app.post("/api/text-filters/skip-blocks")
async def create_skip_text_block(
    pattern: str = Form(...),
    description: str = Form(""),
    is_regex: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new skip text block pattern"""
    from src.database.models import SkipTextBlock
    block = SkipTextBlock(
        pattern=pattern,
        description=description,
        is_regex=is_regex,
        enabled=True
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return {"id": block.id, "message": "Skip text block created successfully"}


@app.patch("/api/text-filters/skip-blocks/{block_id}")
async def update_skip_text_block(
    block_id: int,
    pattern: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    is_regex: Optional[bool] = Form(None),
    enabled: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a skip text block pattern"""
    from src.database.models import SkipTextBlock
    block = db.query(SkipTextBlock).filter(SkipTextBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Skip text block not found")

    if pattern is not None:
        block.pattern = pattern
    if description is not None:
        block.description = description
    if is_regex is not None:
        block.is_regex = is_regex
    if enabled is not None:
        block.enabled = enabled

    db.commit()
    return {"message": "Skip text block updated successfully"}


@app.delete("/api/text-filters/skip-blocks/{block_id}")
async def delete_skip_text_block(
    block_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a skip text block pattern"""
    from src.database.models import SkipTextBlock
    block = db.query(SkipTextBlock).filter(SkipTextBlock.id == block_id).first()
    if not block:
        raise HTTPException(status_code=404, detail="Skip text block not found")

    db.delete(block)
    db.commit()
    return {"message": "Skip text block deleted successfully"}


@app.get("/api/text-filters/ignore-patterns")
async def get_ignore_email_patterns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all ignore email patterns"""
    from src.database.models import IgnoreEmailPattern
    patterns = db.query(IgnoreEmailPattern).order_by(IgnoreEmailPattern.created_at.desc()).all()
    return [
        {
            "id": p.id,
            "pattern": p.pattern,
            "description": p.description,
            "match_subject": p.match_subject,
            "match_body": p.match_body,
            "is_regex": p.is_regex,
            "enabled": p.enabled,
            "created_at": ensure_utc(p.created_at)
        }
        for p in patterns
    ]


@app.post("/api/text-filters/ignore-patterns")
async def create_ignore_email_pattern(
    pattern: str = Form(...),
    description: str = Form(""),
    match_subject: bool = Form(True),
    match_body: bool = Form(True),
    is_regex: bool = Form(False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new ignore email pattern"""
    from src.database.models import IgnoreEmailPattern
    ignore_pattern = IgnoreEmailPattern(
        pattern=pattern,
        description=description,
        match_subject=match_subject,
        match_body=match_body,
        is_regex=is_regex,
        enabled=True
    )
    db.add(ignore_pattern)
    db.commit()
    db.refresh(ignore_pattern)
    return {"id": ignore_pattern.id, "message": "Ignore email pattern created successfully"}


@app.patch("/api/text-filters/ignore-patterns/{pattern_id}")
async def update_ignore_email_pattern(
    pattern_id: int,
    pattern: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    match_subject: Optional[bool] = Form(None),
    match_body: Optional[bool] = Form(None),
    is_regex: Optional[bool] = Form(None),
    enabled: Optional[bool] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an ignore email pattern"""
    from src.database.models import IgnoreEmailPattern
    ignore_pattern = db.query(IgnoreEmailPattern).filter(IgnoreEmailPattern.id == pattern_id).first()
    if not ignore_pattern:
        raise HTTPException(status_code=404, detail="Ignore email pattern not found")

    if pattern is not None:
        ignore_pattern.pattern = pattern
    if description is not None:
        ignore_pattern.description = description
    if match_subject is not None:
        ignore_pattern.match_subject = match_subject
    if match_body is not None:
        ignore_pattern.match_body = match_body
    if is_regex is not None:
        ignore_pattern.is_regex = is_regex
    if enabled is not None:
        ignore_pattern.enabled = enabled

    db.commit()
    return {"message": "Ignore email pattern updated successfully"}


@app.delete("/api/text-filters/ignore-patterns/{pattern_id}")
async def delete_ignore_email_pattern(
    pattern_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an ignore email pattern"""
    from src.database.models import IgnoreEmailPattern
    ignore_pattern = db.query(IgnoreEmailPattern).filter(IgnoreEmailPattern.id == pattern_id).first()
    if not ignore_pattern:
        raise HTTPException(status_code=404, detail="Ignore email pattern not found")

    db.delete(ignore_pattern)
    db.commit()
    return {"message": "Ignore email pattern deleted successfully"}


@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# Pending Messages endpoints
@app.get("/api/messages/pending", response_model=List[PendingMessageInfo])
async def get_pending_messages(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    status: Optional[str] = None,
    message_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Get list of pending messages for approval"""
    query = db.query(PendingMessage).join(TicketState)

    # Filter by status if provided
    if status:
        query = query.filter(PendingMessage.status == status)
    else:
        # Default to pending only
        query = query.filter(PendingMessage.status == 'pending')

    # Filter by message type if provided
    if message_type:
        query = query.filter(PendingMessage.message_type == message_type)

    # Order by confidence (low confidence first for review) then creation time
    messages = query.order_by(
        PendingMessage.confidence_score.asc(),
        PendingMessage.created_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        PendingMessageInfo(
            id=msg.id,
            ticket_number=msg.ticket.ticket_number,
            message_type=msg.message_type,
            recipient_email=msg.recipient_email,
            cc_emails=msg.cc_emails or [],
            subject=msg.subject,
            body=msg.body,
            attachments=msg.attachments or [],
            confidence_score=msg.confidence_score,
            status=msg.status,
            retry_count=msg.retry_count,
            last_error=msg.last_error,
            created_at=ensure_utc(msg.created_at),
            reviewed_at=ensure_utc(msg.reviewed_at),
            sent_at=ensure_utc(msg.sent_at)
        )
        for msg in messages
    ]


@app.post("/api/messages/pending", response_model=PendingMessageInfo)
async def create_pending_message(
    message_data: PendingMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new pending message for a ticket"""
    # Verify ticket exists
    ticket = db.query(TicketState).filter(TicketState.id == message_data.ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Create pending message
    pending_message = PendingMessage(
        ticket_id=message_data.ticket_id,
        message_type=message_data.message_type,
        recipient_email=message_data.recipient_email,
        cc_emails=message_data.cc_emails or [],
        subject=message_data.subject,
        body=message_data.body,
        attachments=message_data.attachments or [],
        status='pending',
        retry_count=0
    )

    db.add(pending_message)
    db.commit()
    db.refresh(pending_message)

    return PendingMessageInfo(
        id=pending_message.id,
        ticket_number=ticket.ticket_number,
        message_type=pending_message.message_type,
        recipient_email=pending_message.recipient_email,
        cc_emails=pending_message.cc_emails or [],
        subject=pending_message.subject,
        body=pending_message.body,
        attachments=pending_message.attachments or [],
        confidence_score=pending_message.confidence_score,
        status=pending_message.status,
        retry_count=pending_message.retry_count,
        last_error=pending_message.last_error,
        created_at=ensure_utc(pending_message.created_at),
        reviewed_at=ensure_utc(pending_message.reviewed_at),
        sent_at=ensure_utc(pending_message.sent_at)
    )


@app.get("/api/messages/pending/count")
async def get_pending_message_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get count of pending messages for dashboard"""
    count = db.query(PendingMessage).filter(PendingMessage.status == 'pending').count()
    low_confidence_count = db.query(PendingMessage).filter(
        PendingMessage.status == 'pending',
        PendingMessage.confidence_score < 0.8
    ).count()

    return {
        "total_pending": count,
        "low_confidence": low_confidence_count,
        "high_priority": low_confidence_count
    }


@app.get("/api/messages/pending/{message_id}", response_model=PendingMessageInfo)
async def get_pending_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific pending message"""
    msg = db.query(PendingMessage).filter(PendingMessage.id == message_id).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    return PendingMessageInfo(
        id=msg.id,
        ticket_number=msg.ticket.ticket_number,
        message_type=msg.message_type,
        recipient_email=msg.recipient_email,
        cc_emails=msg.cc_emails or [],
        subject=msg.subject,
        body=msg.body,
        attachments=msg.attachments or [],
        confidence_score=msg.confidence_score,
        status=msg.status,
        retry_count=msg.retry_count,
        last_error=msg.last_error,
        created_at=ensure_utc(msg.created_at),
        reviewed_at=ensure_utc(msg.reviewed_at),
        sent_at=ensure_utc(msg.sent_at)
    )


@app.post("/api/messages/pending/{message_id}/approve")
async def approve_pending_message(
    message_id: int,
    approval: MessageApproval,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Approve and send or reject a pending message"""
    # Get message
    pending_message = db.query(PendingMessage).filter(PendingMessage.id == message_id).first()
    if not pending_message:
        raise HTTPException(status_code=404, detail="Message not found")

    # Initialize services
    ticketing_client = TicketingAPIClient()
    message_service = MessageService(db, ticketing_client)

    if approval.action == "approve":
        # Extract updated data if provided
        updated_body = approval.updated_data.body if approval.updated_data and approval.updated_data.body else None
        updated_subject = approval.updated_data.subject if approval.updated_data and approval.updated_data.subject else None
        updated_cc = approval.updated_data.cc_emails if approval.updated_data and approval.updated_data.cc_emails is not None else None
        updated_attachments = approval.updated_data.attachments if approval.updated_data and approval.updated_data.attachments is not None else None

        # Send message
        success = message_service.send_pending_message(
            pending_message_id=message_id,
            reviewed_by_user_id=current_user.id,
            updated_body=updated_body,
            updated_subject=updated_subject,
            updated_cc=updated_cc,
            updated_attachments=updated_attachments
        )

        if success:
            return {"message": "Message sent successfully", "status": "sent"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send message")

    elif approval.action == "reject":
        success = message_service.reject_pending_message(
            pending_message_id=message_id,
            reviewed_by_user_id=current_user.id,
            rejection_reason=approval.rejection_reason
        )

        if success:
            return {"message": "Message rejected", "status": "rejected"}
        else:
            raise HTTPException(status_code=500, detail="Failed to reject message")

    else:
        raise HTTPException(status_code=400, detail="Invalid action. Use 'approve' or 'reject'")


@app.post("/api/messages/pending/{message_id}/retry")
async def retry_pending_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry a failed message"""
    ticketing_client = TicketingAPIClient()
    message_service = MessageService(db, ticketing_client)

    success = message_service.retry_failed_message(message_id)

    if success:
        return {"message": "Message queued for retry"}
    else:
        raise HTTPException(status_code=400, detail="Cannot retry message")


@app.get("/api/messages/scheduler/status")
async def get_scheduler_status(
    current_user: User = Depends(get_current_user)
):
    """Get message retry scheduler status"""
    from src.scheduler.message_retry_scheduler import get_scheduler

    try:
        scheduler = get_scheduler()
        return scheduler.get_status()
    except ValueError:
        return {
            "running": False,
            "error": "Scheduler not initialized"
        }


# ============================================================================
# System Settings Endpoints
# ============================================================================

@app.get("/api/settings/{key}")
async def get_setting(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a system setting value"""
    from sqlalchemy import text
    result = db.execute(text("SELECT value FROM system_settings WHERE key = :key"), {"key": key}).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail=f"Setting '{key}' not found")

    return {"key": key, "value": result[0]}


@app.put("/api/settings/{key}")
async def update_setting(
    key: str,
    value: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a system setting value"""
    from sqlalchemy import text

    db.execute(
        text("""
            INSERT OR REPLACE INTO system_settings (key, value, updated_at)
            VALUES (:key, :value, CURRENT_TIMESTAMP)
        """),
        {"key": key, "value": value}
    )
    db.commit()

    logger.info(f"System setting updated: {key}={value} by user {current_user.username}")

    return {"key": key, "value": value, "message": "Setting updated successfully"}


# Include status management router
from src.api.status_api import router as status_router
app.include_router(status_router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
