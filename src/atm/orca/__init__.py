"""Orca v7 — Forest Restoration Scheduling Engine.

This package contains the pure computational engine.
Application layer (entry.py, app.py, ui.py, etc.) is accessed via
scheduler_core/ and tarifas/ subpackages.
"""
from .logging_config import get_logger
logger = get_logger(__name__)
