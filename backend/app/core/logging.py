"""
Logging configuration using loguru.
"""

import sys
from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """Configure loguru for the application."""
    logger.remove()

    log_format_text = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    log_format_json = "{time} {level} {name}:{function}:{line} {message}"

    fmt = log_format_json if settings.log_format == "json" else log_format_text

    logger.add(
        sys.stdout,
        format=fmt,
        level=settings.log_level,
        colorize=(settings.log_format == "text"),
        serialize=(settings.log_format == "json"),
    )

    logger.add(
        "logs/app.log",
        format=fmt,
        level=settings.log_level,
        rotation="10 MB",
        retention="30 days",
        serialize=(settings.log_format == "json"),
    )

    logger.info(
        "Logging initialised",
        log_level=settings.log_level,
        log_format=settings.log_format,
    )
