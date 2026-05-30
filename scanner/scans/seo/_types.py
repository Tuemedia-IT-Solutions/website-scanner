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
    severity: str  # "error" | "warning" | "info"
    detail: str
    element: str | None = None  # short HTML snippet of the offending element


@dataclass
class PageSeoResult:
    url: str
    issues: list[SeoIssue] = field(default_factory=list)
    fetch_error: str | None = None
