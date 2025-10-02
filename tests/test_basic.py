"""
Basic tests to verify system components
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test that all main modules can be imported"""
    from config.settings import settings
    from src.api.ticketing_client import TicketingAPIClient
    from src.email.gmail_monitor import GmailMonitor
    from src.ai.ai_engine import AIEngine
    from src.ai.language_detector import LanguageDetector
    from src.dispatcher.action_dispatcher import ActionDispatcher
    from src.utils.supplier_manager import SupplierManager
    from src.database.models import init_database
    from src.orchestrator import SupportAgentOrchestrator

    assert settings is not None
    assert TicketingAPIClient is not None
    assert GmailMonitor is not None
    assert AIEngine is not None
    assert LanguageDetector is not None
    assert ActionDispatcher is not None
    assert SupplierManager is not None
    assert init_database is not None
    assert SupportAgentOrchestrator is not None


def test_language_detection():
    """Test language detection"""
    from src.ai.language_detector import LanguageDetector

    detector = LanguageDetector()

    # Test German
    german_text = "Wo ist meine Bestellung? Ich habe sie vor einer Woche bestellt."
    assert detector.detect_language(german_text) == 'de-DE'

    # Test English
    english_text = "Where is my order? I ordered it a week ago."
    assert detector.detect_language(english_text) == 'en-US'

    # Test French
    french_text = "Où est ma commande? Je l'ai commandée il y a une semaine."
    assert detector.detect_language(french_text) == 'fr-FR'


def test_order_number_extraction():
    """Test order number extraction"""
    from src.email.gmail_monitor import GmailMonitor

    monitor = GmailMonitor()

    # Test various formats
    test_cases = [
        ("Order 123-4567890-1234567", "123-4567890-1234567"),
        ("My order number is 123-4567890-1234567", "123-4567890-1234567"),
        ("Bestellung: 123-4567890-1234567", "123-4567890-1234567"),
        ("Order #123-4567890-1234567", "123-4567890-1234567"),
        ("No order here", None),
    ]

    for text, expected in test_cases:
        result = monitor.extract_order_number(text)
        assert result == expected, f"Failed for: {text}"


def test_database_init():
    """Test database initialization"""
    from src.database.models import init_database, Supplier
    import tempfile
    import os

    # Use temporary database
    temp_db = tempfile.mktemp(suffix='.db')
    Session = init_database(f"sqlite:///{temp_db}")

    # Test creating a supplier
    session = Session()
    try:
        supplier = Supplier(
            name="Test Supplier",
            default_email="test@supplier.com",
            contact_fields={"returns": "returns@supplier.com"}
        )
        session.add(supplier)
        session.commit()

        # Retrieve it
        retrieved = session.query(Supplier).filter_by(name="Test Supplier").first()
        assert retrieved is not None
        assert retrieved.default_email == "test@supplier.com"
        assert retrieved.get_email_for_purpose("returns") == "returns@supplier.com"
        assert retrieved.get_email_for_purpose("general") == "test@supplier.com"  # Fallback

    finally:
        session.close()
        if os.path.exists(temp_db):
            os.remove(temp_db)


def test_ticket_types():
    """Test ticket type mapping"""
    from src.ai.ai_engine import AIEngine

    engine = AIEngine()

    assert engine.TICKET_TYPES['return'] == 1
    assert engine.TICKET_TYPES['tracking'] == 2
    assert engine.TICKET_TYPES['unknown'] == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
