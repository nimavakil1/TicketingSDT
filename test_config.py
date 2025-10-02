#!/usr/bin/env python3
"""
Quick test to verify configuration loads correctly
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    print("Testing configuration loading...")
    from config.settings import settings

    print("\n✅ Configuration loaded successfully!")
    print(f"\nCurrent settings:")
    print(f"  AI Provider: {settings.ai_provider}")
    print(f"  AI Model: {settings.ai_model}")
    print(f"  Deployment Phase: {settings.deployment_phase} (type: {type(settings.deployment_phase).__name__})")
    print(f"  Confidence Threshold: {settings.confidence_threshold}")
    print(f"  Email Poll Interval: {settings.email_poll_interval_seconds}s")
    print(f"  Ticketing API URL: {settings.ticketing_api_base_url}")
    print(f"  Gmail Support Email: {settings.gmail_support_email}")
    print(f"  Database URL: {settings.database_url}")
    print(f"  Log Level: {settings.log_level}")

    # Validate types
    assert isinstance(settings.deployment_phase, int), "deployment_phase should be int"
    assert settings.deployment_phase in [1, 2, 3], "deployment_phase should be 1, 2, or 3"
    assert isinstance(settings.ai_temperature, float), "ai_temperature should be float"
    assert isinstance(settings.confidence_threshold, float), "confidence_threshold should be float"

    print("\n✅ All type validations passed!")

except Exception as e:
    print(f"\n❌ Configuration loading failed!")
    print(f"Error: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
