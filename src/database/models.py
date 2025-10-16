"""
Database Models
SQLAlchemy models for storing ticket state, processed emails, and supplier information
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Boolean, Float,
    ForeignKey, JSON, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from config.settings import settings

Base = declarative_base()


class ProcessedEmail(Base):
    """
    Track processed emails to ensure idempotency
    Prevents processing the same email multiple times
    """
    __tablename__ = 'processed_emails'

    id = Column(Integer, primary_key=True, autoincrement=True)
    gmail_message_id = Column(String(255), unique=True, nullable=False, index=True)
    gmail_thread_id = Column(String(255), index=True)
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    ticket_id = Column(Integer, ForeignKey('ticket_states.id'), nullable=True)
    order_number = Column(String(50), index=True)
    subject = Column(String(500))
    from_address = Column(String(255))
    success = Column(Boolean, default=True, nullable=False, index=True)
    error_message = Column(Text)

    def __repr__(self):
        return f"<ProcessedEmail(id={self.id}, gmail_id={self.gmail_message_id}, success={self.success})>"


class TicketState(Base):
    """
    Store ticket state and context for AI decision making
    Maintains conversation history and current status
    """
    __tablename__ = 'ticket_states'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_number = Column(String(50), unique=True, nullable=False, index=True)
    ticket_id = Column(Integer, nullable=False, index=True)  # API ticket ID
    order_number = Column(String(50), index=True)
    customer_name = Column(String(255))
    customer_email = Column(String(255))
    customer_language = Column(String(10))  # e.g., 'de-DE', 'en-US'
    supplier_name = Column(String(255))

    # Ticket classification
    ticket_type_id = Column(Integer)  # 1=Return, 2=Tracking, etc.
    ticket_status_id = Column(Integer)  # Current status from API
    owner_id = Column(Integer)  # Ticket owner from API

    # State tracking
    current_state = Column(String(50))  # e.g., 'awaiting_customer', 'awaiting_supplier', 'resolved'
    last_action = Column(String(50))  # e.g., 'sent_to_customer', 'requested_tracking'
    last_action_date = Column(DateTime)

    # Conversation summary (for AI context)
    conversation_summary = Column(Text)  # JSON or text summary of conversation

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Escalation tracking
    escalated = Column(Boolean, default=False)
    escalation_reason = Column(Text)
    escalation_date = Column(DateTime)

    # Relationships
    emails = relationship('ProcessedEmail', backref='ticket', lazy='dynamic')
    supplier_messages = relationship('SupplierMessage', backref='ticket', lazy='dynamic')

    def __repr__(self):
        return f"<TicketState(id={self.id}, ticket_number={self.ticket_number}, state={self.current_state})>"


class Supplier(Base):
    """
    Store supplier contact information
    Allows for different contact emails per purpose (returns, general, etc.)
    """
    __tablename__ = 'suppliers'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True, nullable=False, index=True)
    default_email = Column(String(255), nullable=False)

    # Additional contact fields (flexible schema using JSON)
    # Example: {"returns": "returns@supplier.com", "tracking": "tracking@supplier.com"}
    contact_fields = Column(JSON, default={})

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    messages = relationship('SupplierMessage', backref='supplier', lazy='dynamic')

    def get_email_for_purpose(self, purpose: str) -> str:
        """
        Get supplier email for a specific purpose
        Falls back to default_email if purpose not found

        Args:
            purpose: Purpose key (e.g., 'returns', 'tracking', 'general')

        Returns:
            Email address
        """
        if self.contact_fields and purpose in self.contact_fields:
            return self.contact_fields[purpose]
        return self.default_email

    def __repr__(self):
        return f"<Supplier(id={self.id}, name={self.name})>"


class SupplierMessage(Base):
    """
    Track messages sent to suppliers for reminder functionality
    Monitors response times and triggers reminders
    """
    __tablename__ = 'supplier_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('ticket_states.id'), nullable=False, index=True)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False, index=True)

    message_content = Column(Text, nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Response tracking
    response_received = Column(Boolean, default=False, index=True)
    response_received_at = Column(DateTime)

    # Reminder tracking
    reminder_sent = Column(Boolean, default=False)
    reminder_sent_at = Column(DateTime)
    internal_alert_sent = Column(Boolean, default=False)
    internal_alert_sent_at = Column(DateTime)

    purpose = Column(String(50))  # e.g., 'tracking_request', 'return_inquiry'

    def __repr__(self):
        return f"<SupplierMessage(id={self.id}, ticket_id={self.ticket_id}, sent_at={self.sent_at})>"


class AIDecisionLog(Base):
    """
    Log AI decisions for learning and auditing
    Captures confidence scores and human feedback
    """
    __tablename__ = 'ai_decision_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('ticket_states.id'), nullable=False, index=True)
    gmail_message_id = Column(String(255), index=True)
    prompt_version_id = Column(Integer, ForeignKey('prompt_versions.id'), index=True)  # Which prompt version was used

    # AI analysis
    detected_language = Column(String(10))
    detected_intent = Column(String(100))  # e.g., 'tracking_inquiry', 'return_request'
    confidence_score = Column(Float)  # 0.0 to 1.0

    # Decision
    recommended_action = Column(String(50))  # e.g., 'reply_to_customer', 'contact_supplier'
    response_generated = Column(Text)
    action_taken = Column(String(50))  # Actual action taken (may differ in Phase 1)

    # Phase tracking
    deployment_phase = Column(Integer)  # 1, 2, or 3

    # Human feedback (for Phase 1 learning)
    feedback = Column(String(20))  # 'correct', 'incorrect', 'partially_correct'
    feedback_notes = Column(Text)
    addressed = Column(Boolean, default=False)  # Whether feedback has been addressed in prompt improvements

    # Legacy fields for backward compatibility
    human_feedback = Column(String(20))  # 'approved', 'rejected', 'modified'
    human_notes = Column(Text)

    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship
    ticket = relationship('TicketState', backref='ai_decisions')

    def __repr__(self):
        return f"<AIDecisionLog(id={self.id}, intent={self.detected_intent}, confidence={self.confidence_score})>"


class PromptVersion(Base):
    """
    Track system prompt versions over time
    Links feedback to specific prompt versions
    """
    __tablename__ = 'prompt_versions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    version_number = Column(Integer, nullable=False, unique=True, index=True)
    prompt_text = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_by = Column(String(100))  # Username who approved this version
    change_summary = Column(Text)  # What changed and why
    feedback_count = Column(Integer, default=0)  # How many feedback items prompted this change
    is_active = Column(Boolean, default=False)  # Currently active version

    def __repr__(self):
        return f"<PromptVersion(id={self.id}, version={self.version_number}, active={self.is_active})>"


class PendingEmailRetry(Base):
    """
    Queue of emails to retry linking to an existing ticket.
    Used when no ticket was found yet; we retry later as the ticketing tool may ingest the email asynchronously.
    """
    __tablename__ = 'pending_email_retries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    gmail_message_id = Column(String(255), unique=True, nullable=False, index=True)
    gmail_thread_id = Column(String(255), index=True)
    subject = Column(String(500))
    from_address = Column(String(255))

    attempts = Column(Integer, default=0, nullable=False)
    next_attempt_at = Column(DateTime, index=True)
    last_error = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<PendingEmailRetry(gmail_id={self.gmail_message_id}, attempts={self.attempts})>"


class User(Base):
    """
    User accounts for web UI authentication
    """
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='viewer', nullable=False)  # 'admin', 'operator', 'viewer'

    # Additional fields
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"


# Aliases for backward compatibility
ProcessedMessage = ProcessedEmail
RetryQueue = PendingEmailRetry


# Database initialization
def init_database(database_url: Optional[str] = None) -> sessionmaker:
    """
    Initialize database and create tables

    Args:
        database_url: Optional database URL override

    Returns:
        SQLAlchemy sessionmaker
    """
    db_url = database_url or settings.database_url

    # Create engine
    engine = create_engine(db_url, echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

    # Create sessionmaker
    Session = sessionmaker(bind=engine)

    return Session


def get_session(Session: sessionmaker):
    """
    Get a database session with automatic cleanup

    Args:
        Session: SQLAlchemy sessionmaker

    Yields:
        Database session
    """
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
