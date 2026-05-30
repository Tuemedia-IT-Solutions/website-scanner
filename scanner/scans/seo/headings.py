"""
scanner/scans/seo/headings.py

SEO check: heading structure.

Checks:
  - No <h1> present                              → error
  - More than one <h1>                           → warning
  - Heading levels skipped (e.g. h1 → h3)       → warning
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ._types import SeoIssue

_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]


def check_headings(soup: BeautifulSoup) -> list[SeoIssue]:
    issues: list[SeoIssue] = []

    headings: list[tuple[int, str]] = [
        (int(tag.name[1]), tag.get_text(strip=True)) for tag in soup.find_all(_HEADING_TAGS)
    ]

    h1s = [h for h in headings if h[0] == 1]

    # ── H1 presence ──────────────────────────────────────────────────────────
    if not h1s:
        issues.append(
            SeoIssue(
                check="Missing H1",
                severity="error",
                detail="No <h1> found. Every page should have exactly one H1 as its main heading.",
            )
        )
    elif len(h1s) > 1:
        issues.append(
            SeoIssue(
                check="Multiple H1 elements",
                severity="warning",
                detail=f"Found {len(h1s)} <h1> elements. A page should have exactly one.",
                element=", ".join(f'"{t[:40]}"' for _, t in h1s),
            )
        )

    # ── Skipped levels ────────────────────────────────────────────────────────
    prev = 0
    for level, text in headings:
        if prev > 0 and level > prev + 1:
            issues.append(
                SeoIssue(
                    check="Skipped heading level",
                    severity="warning",
                    detail=(f"Heading jumped from H{prev} to H{level} (H{prev + 1} is missing)."),
                    element=f"<h{level}>{text[:60]}</h{level}>",
                )
            )
        prev = level

    return issues
