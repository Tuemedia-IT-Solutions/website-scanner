"""
scanner/scans/seo/_types.py

Shared result types for the SEO scan.
Defined here (not in __init__) to avoid circular imports with check modules.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SeoIssue:
    check: str
    severity: str  # "error" | "warning" | "info" | "ok"
    detail: str
    element: str | None = None  # short HTML snippet of the offending element
    weight: float = (
        1.0  # criticality multiplier (errors: -weight*10, warnings: -weight*3)
    )


@dataclass
class SeoScore:
    positives: int  # number of checks that passed
    warnings: int  # number of checks with warnings
    errors: int  # number of checks with errors
    score: int  # composite 0-100 score


@dataclass
class PageSeoResult:
    url: str
    issues: list[SeoIssue] = field(default_factory=list)
    fetch_error: str | None = None
    score: SeoScore | None = None
    page_title: str | None = None
    meta_description: str | None = None
