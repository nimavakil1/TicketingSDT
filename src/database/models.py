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

    # Customer address details
    customer_address = Column(Text)
    customer_city = Column(String(100))
    customer_postal_code = Column(String(20))
    customer_country = Column(String(50))
    customer_phone = Column(String(50))

    supplier_name = Column(String(255))
    supplier_email = Column(String(255))  # Supplier contact email
    supplier_ticket_references = Column(Text)  # Comma-separated list of supplier's ticket numbers
    supplier_phone = Column(String(50))
    supplier_contact_person = Column(String(255))
    purchase_order_number = Column(String(50), index=True)  # PO number for supplier communication

    # Delivery/Tracking information
    tracking_number = Column(String(100))
    carrier_name = Column(String(100))
    delivery_status = Column(String(50))
    expected_delivery_date = Column(String(50))

    # Product information (JSON for multiple items)
    product_details = Column(Text)  # JSON: [{sku, title, quantity, price}]

    # Order financial details
    order_total = Column(Float)
    order_currency = Column(String(10))
    order_date = Column(String(50))

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
    supplier_number = Column(Integer, unique=True, index=True)  # Supplier ID from ticketing system
    name = Column(String(255), nullable=False)  # Display name only
    default_email = Column(String(255), nullable=False)
    language_code = Column(String(10), default='de-DE')  # Supplier's preferred language

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
    prompt_version_id = Column(Integer, ForeignKey('prompt_versions.id'), nullable=True, index=True)  # Which prompt version was used (nullable for existing records)

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


class SkipTextBlock(Base):
    """
    Text blocks/patterns to skip/remove from emails before processing
    Used to filter out signatures, disclaimers, boilerplate text
    """
    __tablename__ = 'skip_text_blocks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(Text, nullable=False)
    description = Column(String(255))
    is_regex = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SkipTextBlock(id={self.id}, pattern={self.pattern[:50]})>"


class IgnoreEmailPattern(Base):
    """
    Patterns that indicate an entire email should be ignored
    Used to filter out auto-replies, out-of-office, confirmation emails
    """
    __tablename__ = 'ignore_email_patterns'

    id = Column(Integer, primary_key=True, autoincrement=True)
    pattern = Column(Text, nullable=False)
    description = Column(String(255))
    match_subject = Column(Boolean, default=True)  # Match in subject
    match_body = Column(Boolean, default=True)     # Match in body
    is_regex = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<IgnoreEmailPattern(id={self.id}, pattern={self.pattern[:50]})>"


class MessageTemplate(Base):
    """
    Store message templates for customer and supplier communications
    Templates can be used for consistent messaging and AI-generated content
    """
    __tablename__ = 'message_templates'

    id = Column(Integer, primary_key=True, autoincrement=True)
    template_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    recipient_type = Column(String(20), nullable=False)  # 'supplier', 'customer', 'internal'
    language = Column(String(10), nullable=False)  # e.g., 'de-DE', 'en-US'
    subject_template = Column(Text, nullable=False)
    body_template = Column(Text, nullable=False)
    variables = Column(JSON, default=[])  # List of variable names used in template
    use_cases = Column(JSON, default=[])  # List of intents/use cases (e.g., ['tracking_request', 'shipping_inquiry'])
    requires_attachments = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<MessageTemplate(id={self.id}, name={self.name}, type={self.recipient_type})>"


class PendingMessage(Base):
    """
    Store messages pending human approval before sending
    Used in Phase 1 and 2 for manual review workflow
    """
    __tablename__ = 'pending_messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticket_id = Column(Integer, ForeignKey('ticket_states.id'), nullable=False)
    message_type = Column(String(20), nullable=False)  # 'supplier', 'customer', 'internal'
    recipient_email = Column(String(255))
    cc_emails = Column(JSON, default=[])  # List of CC email addresses
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    attachments = Column(JSON, default=[])  # List of attachment file paths
    confidence_score = Column(Float)  # AI confidence score (0-1)
    ai_decision_id = Column(Integer, ForeignKey('ai_decision_logs.id'))
    status = Column(String(20), default='pending', nullable=False)  # 'pending', 'approved', 'rejected', 'sent', 'failed'
    retry_count = Column(Integer, default=0)  # Number of send attempts
    last_error = Column(Text)  # Last error message if failed
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    reviewed_at = Column(DateTime)
    reviewed_by = Column(Integer, ForeignKey('users.id'))  # User who approved/rejected
    sent_at = Column(DateTime)

    # Relationships
    ticket = relationship('TicketState', backref='pending_messages')
    ai_decision = relationship('AIDecisionLog', backref='pending_messages')
    reviewer = relationship('User', backref='reviewed_messages')

    def __repr__(self):
        return f"<PendingMessage(id={self.id}, type={self.message_type}, status={self.status})>"


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
