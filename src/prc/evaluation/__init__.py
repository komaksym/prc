"""Deterministic logic for the solo pilot evaluation protocol."""

from prc.evaluation.analysis import AnalysisReport, Decision, PairOutcome, Scenario, analyze
from prc.evaluation.kit import PAIRED_PROTOCOL_V2, KitError
from prc.evaluation.protocol import (
    PROTOCOL,
    Condition,
    Pair,
    Protocol,
    SealedExperiment,
    assign,
    seal_experiment,
    verify_seal,
)

__all__ = [
    "PROTOCOL",
    "AnalysisReport",
    "KitError",
    "PAIRED_PROTOCOL_V2",
    "Condition",
    "Decision",
    "Pair",
    "PairOutcome",
    "Protocol",
    "Scenario",
    "SealedExperiment",
    "analyze",
    "assign",
    "seal_experiment",
    "verify_seal",
]
