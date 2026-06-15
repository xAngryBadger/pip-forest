"""Orchestrator — the main scheduling entry point (calcular_cronograma_inteligente).

This module is a thin wrapper that re-exports from the orchestrator package.
The actual implementation is split into phases:
- phase1_setup: Setup, validation, initial configuration
- phase2_linking: Activity linking and conflict configuration
- phase3_checkpoint: Checkpoint retroativo and budget validation
- phase4_demands: Build demands and pre-scheduler checks
- phase5_scheduler_loop: Execute scheduler loop
- phase6_mecanizado: Execute mechanizado mode and multi-fator simulation
- phase7_audit_export: Audit scope and export dossier
- phase8_comparativo: Execute comparativo and build final result
- runner: Main entry point coordinating all phases
"""

from .orchestrator import (
    _phase1_setup,
    _phase2_linking,
    _phase3_checkpoint,
    _phase4_demands,
    _phase5_scheduler_loop,
    _phase6_mecanizado,
    _phase7_audit_export,
    _phase8_comparativo,
    calcular_cronograma_inteligente,
)

__all__ = [
    "_phase1_setup",
    "_phase2_linking",
    "_phase3_checkpoint",
    "_phase4_demands",
    "_phase5_scheduler_loop",
    "_phase6_mecanizado",
    "_phase7_audit_export",
    "_phase8_comparativo",
    "calcular_cronograma_inteligente",
]