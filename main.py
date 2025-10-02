#!/usr/bin/env python3
"""
AI Customer Support Agent - Main Entry Point
Manages customer and supplier communications for a dropshipping company
"""
import sys
import os
import structlog
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
from src.orchestrator import SupportAgentOrchestrator


def setup_logging():
    """Configure structured logging"""
    # Ensure logs directory exists
    log_dir = Path(settings.log_file).parent
    log_dir.mkdir(parents=True, exist_ok=True)

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Set log level
    import logging
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, settings.log_level.upper()),
        handlers=[
            logging.FileHandler(settings.log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Main entry point"""
    setup_logging()

    logger = structlog.get_logger(__name__)

    logger.info(
        "=" * 60,
    )
    logger.info("AI Customer Support Agent Starting")
    logger.info(
        "Configuration",
        phase=settings.deployment_phase,
        ai_provider=settings.ai_provider,
        ai_model=settings.ai_model
    )
    logger.info("=" * 60)

    try:
        # Initialize and run orchestrator
        orchestrator = SupportAgentOrchestrator()
        orchestrator.run_forever()

    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        sys.exit(0)

    except Exception as e:
        logger.error("Fatal error", error=str(e), exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
