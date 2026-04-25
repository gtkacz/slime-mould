"""Loguru configuration with stdlib `logging` interception.

Call `configure_logging()` once at process start. Every other logger
(stdlib, third-party libraries) is redirected into loguru via
`InterceptHandler`, so the entire process emits a single, consistent
log stream.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

from loguru import logger

_DEFAULT_FORMAT: Final[str] = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
    "<level>{level: <8}</level> "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
    "- <level>{message}</level>"
)


class InterceptHandler(logging.Handler):
    """Route stdlib `logging` records into loguru."""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def configure_logging(level: str = "INFO", *, fmt: str = _DEFAULT_FORMAT) -> None:
    """Install loguru as the single sink and intercept stdlib logging."""
    logger.remove()
    logger.add(sys.stderr, level=level, format=fmt, enqueue=False, backtrace=False, diagnose=False)

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    for noisy in ("numba", "numba.core", "numba.core.ssa", "numba.core.byteflow"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
