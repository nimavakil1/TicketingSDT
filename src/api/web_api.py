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
    ai_model: Optional[str]
    ai_max_tokens: Optional[int]
    system_prompt: Optional[str]


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
    query = db.query(TicketState).order_by(TicketState.updated_at.desc())

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

        return {
            "success": True,
            "message": f"Settings updated successfully. Changes: {', '.join(changes_made)}. Restart services to apply changes.",
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
            created_at=user.created_at
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
