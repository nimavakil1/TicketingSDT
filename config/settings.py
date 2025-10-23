"""
Configuration settings for AI Support Agent
Loads configuration from environment variables with validation
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from typing import Literal, Union
import os


class Settings(BaseSettings):
    """Application settings with environment variable loading"""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False,
        validate_default=True,
        extra='ignore'
    )

    # Ticketing API Configuration
    ticketing_api_base_url: str = Field(
        default="https://api.distri-smart.com/api/sdt/1",
        description="Base URL for ticketing API"
    )
    ticketing_api_username: str = Field(
        default="TicketingAgent",
        description="Ticketing API username"
    )
    ticketing_api_password: str = Field(
        ...,
        description="Ticketing API password"
    )

    # Gmail Configuration
    gmail_credentials_path: str = Field(
        default="config/gmail_credentials.json",
        description="Path to Gmail OAuth credentials"
    )
    gmail_token_path: str = Field(
        default="config/gmail_token.json",
        description="Path to Gmail OAuth token storage"
    )
    gmail_support_email: str = Field(
        ...,
        description="Support email address to monitor"
    )
    gmail_processed_label: str = Field(
        default="AI_Agent_Processed",
        description="Gmail label for processed emails"
    )
    gmail_start_at: str | None = Field(
        default=None,
        description="ISO8601 or epoch seconds to start processing from"
    )
    gmail_max_results: int = Field(
        default=25,
        ge=1,
        le=500,
        description="Max messages to fetch per poll"
    )
    preparation_mode: bool = Field(
        default=False,
        description="Preparation mode: only label emails; skip AI and ticketing"
    )

    # AI Configuration
    ai_provider: Literal["openai", "anthropic", "gemini"] = Field(
        default="openai",
        description="AI provider to use"
    )
    openai_api_key: str | None = Field(default=None)
    anthropic_api_key: str | None = Field(default=None)
    google_api_key: str | None = Field(default=None)
    ai_model: str = Field(
        default="gpt-4",
        description="AI model identifier"
    )
    ai_temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="AI response temperature"
    )
    ai_max_tokens: int = Field(
        default=2000,
        ge=100,
        le=16000,
        description="Maximum tokens for AI responses (GPT-5 reasoning models need more)"
    )

    # Phase Configuration
    deployment_phase: int = Field(
        default=1,
        description="1=Shadow, 2=Partial Automation, 3=Full Integration"
    )
    confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for auto-responses"
    )

    @field_validator('deployment_phase')
    @classmethod
    def validate_deployment_phase(cls, v: Union[str, int]) -> int:
        """Convert deployment phase to int and validate"""
        try:
            phase = int(v)
            if phase not in [1, 2, 3]:
                raise ValueError("Deployment phase must be 1, 2, or 3")
            return phase
        except (ValueError, TypeError):
            raise ValueError("Deployment phase must be 1, 2, or 3")

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///data/support_agent.db",
        description="Database connection string"
    )

    # Web UI Configuration
    jwt_secret_key: str = Field(
        default="change-this-secret-key-in-production-use-openssl-rand-hex-32",
        description="Secret key for JWT token signing"
    )
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm"
    )
    jwt_access_token_expire_minutes: int = Field(
        default=1440,  # 24 hours
        description="JWT access token expiration in minutes"
    )

    # Default Ticket Configuration
    default_owner_id: int = Field(
        default=1087,
        description="Default ticket owner ID"
    )

    # Supplier Configuration
    supplier_reminder_hours: int = Field(
        default=24,
        ge=1,
        description="Hours before sending supplier reminder"
    )
    internal_alert_email: str = Field(
        ...,
        description="Email for internal alerts"
    )
    supplier_default_language: str = Field(
        default="de-DE",
        description="Default language for supplier communications"
    )
    supplier_language_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of supplier name -> language code (JSON or 'Name:code;Name2:code2')"
    )

    # CC Configuration for Messages
    supplier_cc_config: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Mapping of supplier name -> list of CC emails (JSON format)"
    )
    internal_cc_high_priority: list[str] = Field(
        default_factory=list,
        description="CC addresses for high-priority internal notifications"
    )
    customer_escalation_cc: list[str] = Field(
        default_factory=list,
        description="CC addresses for escalated customer messages"
    )
    supplier_escalation_cc: str = Field(
        default="",
        description="CC address for escalated supplier messages"
    )
    vip_support_cc: str = Field(
        default="",
        description="CC address for VIP/high-value customer support"
    )
    high_value_order_threshold: float = Field(
        default=500.0,
        description="Order amount threshold for VIP treatment (in EUR)"
    )
    high_priority_ticket_types: list[int] = Field(
        default_factory=list,
        description="List of ticket type IDs considered high priority"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/support_agent.log")

    # Polling Configuration
    email_poll_interval_seconds: int = Field(
        default=60,
        ge=10,
        description="Email polling interval"
    )

    # Prompt Configuration
    prompt_path: str = Field(
        default="config/prompt/agent_prompt.md",
        description="Path to the operating prompt injected into AI analysis"
    )
    few_shots_path: str = Field(
        default="config/prompt/few_shots.json",
        description="Optional path to few-shot examples (JSON)"
    )

    # Phase 1 Internal Note Formatting
    phase1_customer_prefix: str = Field(
        default="AI agent proposes to send to the customer:",
        description="Prefix line used in Phase 1 internal notes before the suggested customer message"
    )
    phase1_supplier_prefix: str = Field(
        default="AI agent proposes to send to the supplier:",
        description="Prefix line used in Phase 1 internal notes before the suggested supplier message"
    )

    # Retry configuration for pending tickets (Phase 1)
    retry_enabled: bool = Field(
        default=True,
        description="Enable retry queue when ticket lookup fails"
    )
    retry_max_attempts: int = Field(
        default=5,
        ge=1,
        description="Maximum number of retry attempts per email"
    )
    retry_delay_minutes: int = Field(
        default=60,
        ge=1,
        description="Minutes between retry attempts"
    )

    @field_validator('default_owner_id', 'supplier_reminder_hours', 'ai_max_tokens', 'email_poll_interval_seconds', 'gmail_max_results', mode='before')
    @classmethod
    def validate_integers(cls, v: Union[str, int]) -> int:
        """Convert string integers from env vars to int"""
        try:
            return int(v)
        except (ValueError, TypeError):
            raise ValueError(f"Must be a valid integer")

    @field_validator('ai_temperature', 'confidence_threshold', mode='before')
    @classmethod
    def validate_floats(cls, v: Union[str, float]) -> float:
        """Convert string floats from env vars to float"""
        try:
            return float(v)
        except (ValueError, TypeError):
            raise ValueError(f"Must be a valid number")

    @field_validator('supplier_language_overrides', mode='before')
    @classmethod
    def parse_supplier_lang_overrides(cls, v):
        """Allow JSON or 'Name:code;Name2:code2' mapping in env."""
        if isinstance(v, dict) or v is None:
            return v or {}
        s = str(v).strip()
        if not s:
            return {}
        # Try JSON first
        try:
            import json
            m = json.loads(s)
            if isinstance(m, dict):
                return m
        except Exception:
            pass
        # Fallback: semi-colon separated pairs
        result = {}
        for part in s.split(';'):
            part = part.strip()
            if not part:
                continue
            if ':' in part:
                name, code = part.split(':', 1)
                result[name.strip()] = code.strip()
        return result

    @field_validator('ai_provider', mode='after')
    @classmethod
    def validate_ai_provider(cls, v: str, info) -> str:
        """Ensure appropriate API key is set for selected provider"""
        # Note: This validation is relaxed to allow initial setup
        # The AI engine will fail gracefully if keys are missing
        return v

    def get_project_root(self) -> str:
        """Get absolute path to project root"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Global settings instance
settings = Settings()
