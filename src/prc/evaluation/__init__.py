"""Deterministic logic for the solo pilot evaluation protocol."""

from prc.evaluation.analysis import AnalysisReport, Decision, PairOutcome, Scenario, analyze
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
