"""Stable nonjudgmental Portia application-integrity findings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True, slots=True)
class ApplicationFinding:
    """One deterministic graph-integrity finding.

    Messages intentionally describe record integrity only and must not reproduce
    sensitive free-text record content.
    """

    code: str
    subject: str
    message: str
    path: str = ""
    related: tuple[str, ...] = ()
