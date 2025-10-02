"""
Configuration settings for AI Support Agent
Loads configuration from environment variables with validation
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator
from typing import Literal
import os


class Settings(BaseSettings):
    """Application settings with environment variable loading"""

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        case_sensitive=False
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
        le=4000,
        description="Maximum tokens for AI responses"
    )

    # Phase Configuration
    deployment_phase: Literal[1, 2, 3] = Field(
        default=1,
        description="1=Shadow, 2=Partial Automation, 3=Full Integration"
    )
    confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum confidence for auto-responses"
    )

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///data/support_agent.db",
        description="Database connection string"
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

    # Logging Configuration
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="logs/support_agent.log")

    # Polling Configuration
    email_poll_interval_seconds: int = Field(
        default=60,
        ge=10,
        description="Email polling interval"
    )

    @validator('ai_provider')
    def validate_ai_provider(cls, v, values):
        """Ensure appropriate API key is set for selected provider"""
        if v == 'openai' and not values.get('openai_api_key'):
            raise ValueError("OPENAI_API_KEY must be set when using openai provider")
        elif v == 'anthropic' and not values.get('anthropic_api_key'):
            raise ValueError("ANTHROPIC_API_KEY must be set when using anthropic provider")
        elif v == 'gemini' and not values.get('google_api_key'):
            raise ValueError("GOOGLE_API_KEY must be set when using gemini provider")
        return v

    def get_project_root(self) -> str:
        """Get absolute path to project root"""
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Global settings instance
settings = Settings()
