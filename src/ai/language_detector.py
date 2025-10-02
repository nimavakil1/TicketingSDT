"""
Language Detection Module
Detects the language of incoming emails for multilingual support
"""
from typing import Optional
import structlog
from langdetect import detect, DetectorFactory, LangDetectException

logger = structlog.get_logger(__name__)

# Set seed for consistent results
DetectorFactory.seed = 0

# Mapping of langdetect codes to culture names
LANGUAGE_MAPPING = {
    'de': 'de-DE',
    'en': 'en-US',
    'fr': 'fr-FR',
    'es': 'es-ES',
    'it': 'it-IT',
    'nl': 'nl-NL',
    'pl': 'pl-PL',
    'pt': 'pt-PT',
}


class LanguageDetector:
    """Detects language of text content"""

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Detect language of text

        Args:
            text: Text to analyze

        Returns:
            Culture name (e.g., 'de-DE', 'en-US')
            Defaults to 'en-US' if detection fails
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for language detection")
            return 'en-US'

        try:
            # Detect language code
            lang_code = detect(text)
            logger.debug("Detected language", lang_code=lang_code)

            # Map to culture name
            culture_name = LANGUAGE_MAPPING.get(lang_code, 'en-US')
            logger.info("Language detected", culture=culture_name)
            return culture_name

        except LangDetectException as e:
            logger.warning("Language detection failed", error=str(e))
            return 'en-US'
        except Exception as e:
            logger.error("Unexpected error in language detection", error=str(e))
            return 'en-US'

    @staticmethod
    def get_language_name(culture: str) -> str:
        """
        Get human-readable language name from culture code

        Args:
            culture: Culture code (e.g., 'de-DE')

        Returns:
            Language name (e.g., 'German')
        """
        names = {
            'de-DE': 'German',
            'en-US': 'English',
            'fr-FR': 'French',
            'es-ES': 'Spanish',
            'it-IT': 'Italian',
            'nl-NL': 'Dutch',
            'pl-PL': 'Polish',
            'pt-PT': 'Portuguese',
        }
        return names.get(culture, 'English')
