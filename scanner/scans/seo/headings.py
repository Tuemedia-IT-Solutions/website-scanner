"""
scanner/scans/seo/headings.py

SEO check: heading structure.

Checks:
  - No <h1> present                              → error
  - More than one <h1>                           → warning
  - Heading levels skipped (e.g. h1 → h3)       → warning
  - High heading density (< 30 words/heading,   → warning
    requires ≥ 4 headings to avoid false positives)
"""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString

from ._types import SeoIssue

_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
_DENSITY_MIN_HEADINGS = 4
_DENSITY_WORDS_PER_HEADING = 30
_SKIP_TAGS = {"script", "style", "noscript"}


def check_headings(soup: BeautifulSoup) -> list[SeoIssue]:
    issues: list[SeoIssue] = []

    headings: list[tuple[int, str]] = [
        (int(tag.name[1]), tag.get_text(strip=True))
        for tag in soup.find_all(_HEADING_TAGS)
    ]

    h1s = [h for h in headings if h[0] == 1]

    # ── H1 presence ──────────────────────────────────────────────────────────
    if not h1s:
        issues.append(
            SeoIssue(
                check="Missing H1",
                severity="error",
                detail="No <h1> found. Every page should have exactly one H1 as its main heading.",
                weight=1.5,
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
                    detail=(
                        f"Heading jumped from H{prev} to H{level} (H{prev + 1} is missing)."
                    ),
                    element=f"<h{level}>{text[:60]}</h{level}>",
                )
            )
        prev = level

    # ── Heading density ───────────────────────────────────────────────────────
    if len(headings) >= _DENSITY_MIN_HEADINGS:
        word_count = _body_word_count(soup)
        if word_count > 0 and word_count / len(headings) < _DENSITY_WORDS_PER_HEADING:
            avg = word_count // len(headings)
            issues.append(
                SeoIssue(
                    check="High heading density",
                    severity="warning",
                    detail=(
                        f"Found {len(headings)} headings for ~{word_count} words "
                        f"(~{avg} words/heading). "
                        "Excessive headings relative to content can appear spammy to search engines."
                    ),
                )
            )

    if not issues:
        issues.append(
            SeoIssue(
                check="Heading structure",
                severity="ok",
                detail="Heading structure is well-formed (single H1, no skipped levels).",
            )
        )

    return issues


def _body_word_count(soup: BeautifulSoup) -> int:
    """Count visible words in the page body, ignoring script/style/noscript."""
    body = soup.find("body") or soup
    words = 0
    for element in body.descendants:
        if (
            isinstance(element, NavigableString)
            and element.parent.name not in _SKIP_TAGS
        ):
            words += len(str(element).split())
    return words
