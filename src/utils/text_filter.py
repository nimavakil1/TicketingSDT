"""
Text Filtering Utilities
Filters out unnecessary text and identifies emails to ignore
"""
import re
from typing import Optional, Tuple
import structlog
from sqlalchemy.orm import Session

from src.database.models import SkipTextBlock, IgnoreEmailPattern

logger = structlog.get_logger(__name__)


class TextFilter:
    """
    Filters email text based on configured patterns
    - Identifies emails that should be completely ignored (auto-replies, OOO, etc.)
    - Removes unnecessary text blocks from email body (signatures, disclaimers, etc.)
    """

    def __init__(self, db_session: Session):
        """
        Initialize text filter with database session

        Args:
            db_session: SQLAlchemy database session
        """
        self.db_session = db_session
        self._skip_blocks_cache = None
        self._ignore_patterns_cache = None

    def _load_skip_blocks(self):
        """Load enabled skip text blocks from database"""
        if self._skip_blocks_cache is None:
            self._skip_blocks_cache = self.db_session.query(SkipTextBlock).filter_by(
                enabled=True
            ).all()
            logger.info("Loaded skip text blocks", count=len(self._skip_blocks_cache))
        return self._skip_blocks_cache

    def _load_ignore_patterns(self):
        """Load enabled ignore email patterns from database"""
        if self._ignore_patterns_cache is None:
            self._ignore_patterns_cache = self.db_session.query(IgnoreEmailPattern).filter_by(
                enabled=True
            ).all()
            logger.info("Loaded ignore email patterns", count=len(self._ignore_patterns_cache))
        return self._ignore_patterns_cache

    def should_ignore_email(self, subject: str, body: str) -> Tuple[bool, Optional[str]]:
        """
        Check if an email should be completely ignored based on patterns

        Args:
            subject: Email subject line
            body: Email body text

        Returns:
            Tuple of (should_ignore, reason)
            - should_ignore: True if email should be ignored
            - reason: Description of why it should be ignored (pattern that matched)
        """
        patterns = self._load_ignore_patterns()

        for pattern in patterns:
            pattern_text = pattern.pattern

            # Check subject if enabled
            if pattern.match_subject and subject:
                if self._matches_pattern(subject, pattern_text, pattern.is_regex):
                    logger.info(
                        "Email should be ignored (subject match)",
                        pattern_id=pattern.id,
                        pattern=pattern_text[:50],
                        description=pattern.description
                    )
                    return True, f"Subject matches ignore pattern: {pattern.description or pattern_text[:50]}"

            # Check body if enabled
            if pattern.match_body and body:
                if self._matches_pattern(body, pattern_text, pattern.is_regex):
                    logger.info(
                        "Email should be ignored (body match)",
                        pattern_id=pattern.id,
                        pattern=pattern_text[:50],
                        description=pattern.description
                    )
                    return True, f"Body matches ignore pattern: {pattern.description or pattern_text[:50]}"

        return False, None

    def filter_email_body(self, body: str) -> str:
        """
        Remove skip text blocks from email body

        Args:
            body: Original email body text

        Returns:
            Filtered email body with skip blocks removed
        """
        if not body:
            return body

        filtered_body = body
        skip_blocks = self._load_skip_blocks()
        removed_count = 0

        for block in skip_blocks:
            pattern_text = block.pattern

            try:
                if block.is_regex:
                    # Use regex pattern
                    new_body = re.sub(pattern_text, '', filtered_body, flags=re.IGNORECASE | re.DOTALL)
                else:
                    # Normalize whitespace for matching (replace multiple whitespace with single space)
                    # This makes matching work even when line breaks differ
                    pattern_normalized = re.sub(r'\s+', ' ', pattern_text).strip().lower()
                    body_normalized = re.sub(r'\s+', ' ', filtered_body).strip().lower()

                    # Check if normalized pattern exists in normalized body
                    if pattern_normalized in body_normalized:
                        # Find the start position in normalized text
                        norm_start = body_normalized.find(pattern_normalized)

                        # Now we need to find corresponding position in original text
                        # We'll use a different approach: create a regex that matches the pattern with flexible whitespace
                        # Escape special regex characters in the pattern
                        pattern_escaped = re.escape(pattern_text)
                        # Replace any whitespace sequence in the pattern with flexible whitespace matcher
                        pattern_regex = re.sub(r'\\\s+', r'\\s+', pattern_escaped)

                        # Remove all occurrences using the flexible regex
                        new_body = re.sub(pattern_regex, '', filtered_body, flags=re.IGNORECASE)
                    else:
                        new_body = filtered_body

                if new_body != filtered_body:
                    removed_count += 1
                    logger.debug(
                        "Removed skip text block",
                        pattern_id=block.id,
                        pattern=pattern_text[:50],
                        description=block.description
                    )

                filtered_body = new_body

            except re.error as e:
                logger.error(
                    "Invalid regex pattern in skip block",
                    pattern_id=block.id,
                    pattern=pattern_text[:50],
                    error=str(e)
                )
                # Skip this pattern and continue with others

        if removed_count > 0:
            # Clean up excessive whitespace left by removed blocks
            filtered_body = re.sub(r'\n\s*\n\s*\n+', '\n\n', filtered_body)
            filtered_body = filtered_body.strip()

            logger.info(
                "Filtered email body",
                original_length=len(body),
                filtered_length=len(filtered_body),
                removed_blocks=removed_count
            )

        return filtered_body

    def _matches_pattern(self, text: str, pattern: str, is_regex: bool) -> bool:
        """
        Check if text matches a pattern

        Args:
            text: Text to check
            pattern: Pattern to match
            is_regex: Whether pattern is a regex

        Returns:
            True if text matches pattern
        """
        try:
            if is_regex:
                # Use regex matching
                return bool(re.search(pattern, text, re.IGNORECASE | re.DOTALL))
            else:
                # Simple case-insensitive substring match
                return pattern.lower() in text.lower()
        except re.error as e:
            logger.error(
                "Invalid regex pattern",
                pattern=pattern[:50],
                error=str(e)
            )
            return False
