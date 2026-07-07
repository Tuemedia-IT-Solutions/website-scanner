"""
scanner/scans/seo/content.py

SEO check: page content length.

Checks:
  - Very thin content (< 100 words)  → warning
"""

from __future__ import annotations

from bs4 import BeautifulSoup, NavigableString

from ._types import SeoIssue

_THIN_THRESHOLD = 100
_SKIP_TAGS = {"script", "style", "noscript"}


def check_content(soup: BeautifulSoup) -> list[SeoIssue]:
    word_count = _body_word_count(soup)
    if word_count < _THIN_THRESHOLD:
        return [
            SeoIssue(
                check="Very thin content",
                severity="warning",
                detail=(
                    f"Page body contains only ~{word_count} words. "
                    "Very thin content may be penalised by search engines."
                ),
            )
        ]
    return []


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
