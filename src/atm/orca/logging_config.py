"""Logging configuration for the orca package.

Usage:
    from orca.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("message")
    logger.warning("message", exc_info=True)

Environment variables:
    ORCA_LOG_LEVEL: DEBUG, INFO, WARNING, ERROR, CRITICAL (default: INFO)
"""

import logging
import os
import sys


def _configure_root() -> None:
    level_name = os.environ.get("ORCA_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger("orca")
    root.setLevel(level)

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s.%(funcName)s | %(message)s"
        datefmt = "%H:%M:%S"
        handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(handler)

    root.propagate = False


_configure_root()


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
