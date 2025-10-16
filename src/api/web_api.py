"""
Web API for AI Agent Management UI
FastAPI application that exposes existing system functionality via REST API
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import structlog
from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
import jwt
from passlib.context import CryptContext

from config.settings import settings
from src.database.models import TicketState, AIDecisionLog, ProcessedMessage, RetryQueue, User, init_database
from src.ai.ai_engine import AIEngine
from src.api.ticketing_client import TicketingAPIClient

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


class TicketInfo(BaseModel):
    ticket_number: str
    status: str
    customer_email: str
    last_updated: datetime
    escalated: bool
    ai_decision_count: int
    ticket_status_id: int
    owner_id: Optional[int]


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
    emails_today = db.query(ProcessedMessage).filter(
        ProcessedMessage.processed_at >= today
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
    processed = db.query(ProcessedMessage).order_by(
        ProcessedMessage.processed_at.desc()
    ).offset(offset).limit(limit).all()

    return [
        {
            "id": msg.id,
            "gmail_message_id": msg.gmail_message_id,
            "subject": msg.subject or "N/A",
            "from_address": msg.from_address or "N/A",
            "order_number": msg.order_number or "N/A",
            "processed_at": msg.processed_at,
            "success": getattr(msg, 'success', True),  # Default to True for old records
            "error_message": getattr(msg, 'error_message', None)
        }
        for msg in processed
    ]


@app.get("/api/emails/retry-queue", response_model=List[RetryQueueItem])
async def get_retry_queue(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get emails in retry queue"""
    retries = db.query(RetryQueue).order_by(
        RetryQueue.next_retry_at.asc()
    ).all()

    return [
        RetryQueueItem(
            id=retry.id,
            gmail_message_id=retry.gmail_message_id,
            subject=retry.subject,
            from_address=retry.from_address,
            attempts=retry.attempts,
            next_attempt_at=retry.next_attempt_at,
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
    query = db.query(TicketState).order_by(TicketState.last_updated.desc())

    if escalated_only:
        query = query.filter(TicketState.escalated == True)

    tickets = query.offset(offset).limit(limit).all()

    return [
        TicketInfo(
            ticket_number=ticket.ticket_number,
            status=ticket.current_state or "unknown",
            customer_email=ticket.customer_email or "N/A",
            last_updated=ticket.updated_at,
            escalated=ticket.escalated,
            ai_decision_count=len(ticket.ai_decisions),
            ticket_status_id=ticket.ticket_status_id or 0,
            owner_id=ticket.owner_id
        )
        for ticket in tickets
    ]


@app.get("/api/tickets/{ticket_number}", response_model=Dict[str, Any])
async def get_ticket_detail(
    ticket_number: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed ticket information including AI decisions"""
    ticket = db.query(TicketState).filter(
        TicketState.ticket_number == ticket_number
    ).first()

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get AI decisions for this ticket
    decisions = db.query(AIDecisionLog).filter(
        AIDecisionLog.ticket_id == ticket.id
    ).order_by(AIDecisionLog.timestamp.desc()).all()

    return {
        "ticket_number": ticket.ticket_number,
        "ticket_id": ticket.ticket_id,
        "status": ticket.current_state or "unknown",
        "customer_email": ticket.customer_email,
        "ticket_status_id": ticket.ticket_status_id,
        "owner_id": ticket.owner_id,
        "escalated": ticket.escalated,
        "escalation_reason": ticket.escalation_reason,
        "escalation_date": ticket.escalation_date,
        "last_updated": ticket.updated_at,
        "created_at": ticket.created_at,
        "ai_decisions": [
            {
                "id": dec.id,
                "timestamp": dec.timestamp,
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


# AI Decision Log endpoints
@app.get("/api/ai-decisions", response_model=List[AIDecisionInfo])
async def get_ai_decisions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0
):
    """Get list of AI decisions"""
    decisions = db.query(AIDecisionLog).order_by(
        AIDecisionLog.timestamp.desc()
    ).offset(offset).limit(limit).all()

    return [
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


@app.post("/api/ai-decisions/{decision_id}/feedback")
async def submit_feedback(
    decision_id: int,
    feedback: str,  # 'correct', 'incorrect', 'partially_correct'
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback on AI decision"""
    decision = db.query(AIDecisionLog).filter(AIDecisionLog.id == decision_id).first()

    if not decision:
        raise HTTPException(status_code=404, detail="Decision not found")

    decision.feedback = feedback
    decision.feedback_notes = notes
    db.commit()

    logger.info("Feedback submitted", decision_id=decision_id, feedback=feedback, user=current_user.username)

    return {"success": True, "message": "Feedback recorded"}


# Settings endpoints
@app.get("/api/settings")
async def get_settings(current_user: User = Depends(get_current_user)):
    """Get current system settings"""
    return {
        "deployment_phase": settings.deployment_phase,
        "confidence_threshold": settings.confidence_threshold,
        "ai_provider": settings.ai_provider,
        "ai_model": settings.ai_model,
        "ai_temperature": settings.ai_temperature,
        "ai_max_tokens": settings.ai_max_tokens,
        "retry_enabled": settings.retry_enabled,
        "retry_max_attempts": settings.retry_max_attempts,
        "retry_delay_minutes": settings.retry_delay_minutes,
        "gmail_check_interval": settings.gmail_check_interval
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

    # Note: In production, settings should be persisted to database or config file
    # For now, this is a placeholder showing the API structure

    logger.warning(
        "Settings update requested (not yet persisted)",
        updates=updates.dict(exclude_none=True),
        user=current_user.username
    )

    return {
        "success": True,
        "message": "Settings updated (restart required for some changes)"
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
