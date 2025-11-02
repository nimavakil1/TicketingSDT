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

    @staticmethod
    def validate_language(text: str, expected_language: str) -> tuple[bool, str]:
        """
        Validate that text is in the expected language

        Args:
            text: Text to validate
            expected_language: Expected culture code (e.g., 'de-DE', 'en-US')

        Returns:
            Tuple of (is_valid: bool, detected_language: str)
            is_valid=True if text matches expected language
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for language validation")
            return False, 'unknown'

        try:
            # Skip very short text (e.g., "OK", "Thanks") - unreliable for detection
            if len(text.strip()) < 20:
                logger.debug("Text too short for reliable language validation", length=len(text))
                return True, expected_language  # Assume correct for short text

            # Detect actual language
            detected = LanguageDetector.detect_language(text)

            # Check if detected matches expected (ignore regional variants)
            expected_base = expected_language.split('-')[0].lower()  # de-DE → de
            detected_base = detected.split('-')[0].lower()  # de-DE → de

            is_valid = expected_base == detected_base

            if not is_valid:
                logger.warning(
                    "Language mismatch detected",
                    expected=expected_language,
                    detected=detected,
                    text_preview=text[:100]
                )

            return is_valid, detected

        except Exception as e:
            logger.error("Language validation failed", error=str(e))
            return True, expected_language  # Assume correct on error to avoid blocking
