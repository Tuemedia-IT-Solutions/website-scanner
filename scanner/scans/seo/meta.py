"""
scanner/scans/seo/meta.py

SEO check: meta tags — title, description, canonical URL.

Checks:
  - Missing / empty <title>                              → error
  - Title shorter than 10 or longer than 60 chars        → warning
  - Missing / empty <meta name="description">            → warning
  - Description shorter than 50 or longer than 160 chars → warning
  - Missing <link rel="canonical">                       → info
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from ._types import SeoIssue

_TITLE_MIN = 10
_TITLE_MAX = 60
_DESC_MIN = 50
_DESC_MAX = 160


def check_meta(soup: BeautifulSoup) -> list[SeoIssue]:
    issues: list[SeoIssue] = []
    issues.extend(_check_title(soup))
    issues.extend(_check_description(soup))
    issues.extend(_check_canonical(soup))
    return issues


# ── Title ─────────────────────────────────────────────────────────────────────


def _check_title(soup: BeautifulSoup) -> list[SeoIssue]:
    tag = soup.find("title")

    if not tag or not tag.get_text(strip=True):
        return [
            SeoIssue(
                check="Missing title",
                severity="error",
                detail="Page has no <title> tag. Required for SEO and browser tab labelling.",
            )
        ]

    title = tag.get_text(strip=True)
    length = len(title)
    issues: list[SeoIssue] = []

    if length < _TITLE_MIN:
        issues.append(
            SeoIssue(
                check="Title too short",
                severity="warning",
                detail=f'Title is {length} chars (min {_TITLE_MIN}): "{title}"',
            )
        )
    elif length > _TITLE_MAX:
        issues.append(
            SeoIssue(
                check="Title too long",
                severity="warning",
                detail=f'Title is {length} chars (max {_TITLE_MAX}): "{title[:60]}…"',
            )
        )

    return issues


# ── Meta description ──────────────────────────────────────────────────────────


def _check_description(soup: BeautifulSoup) -> list[SeoIssue]:
    tag = soup.find("meta", attrs={"name": "description"})

    if not tag or not tag.get("content", "").strip():
        return [
            SeoIssue(
                check="Missing meta description",
                severity="warning",
                detail='No <meta name="description"> found. Affects search result snippets.',
            )
        ]

    desc = tag["content"].strip()
    length = len(desc)
    issues: list[SeoIssue] = []

    if length < _DESC_MIN:
        issues.append(
            SeoIssue(
                check="Meta description too short",
                severity="warning",
                detail=f'Description is {length} chars (min {_DESC_MIN}): "{desc}"',
            )
        )
    elif length > _DESC_MAX:
        issues.append(
            SeoIssue(
                check="Meta description too long",
                severity="warning",
                detail=(
                    f"Description is {length} chars (max {_DESC_MAX}). "
                    "Google truncates long descriptions in search results."
                ),
            )
        )

    return issues


# ── Canonical ─────────────────────────────────────────────────────────────────


def _check_canonical(soup: BeautifulSoup) -> list[SeoIssue]:
    tag = soup.find("link", attrs={"rel": "canonical"})

    if not tag or not tag.get("href", "").strip():
        return [
            SeoIssue(
                check="Missing canonical URL",
                severity="info",
                detail='No <link rel="canonical"> found. Recommended to prevent duplicate-content issues.',
            )
        ]

    return []
