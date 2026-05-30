"""Tests for scanner/scans/seo/meta.py"""

from __future__ import annotations

from bs4 import BeautifulSoup

from scanner.scans.seo.meta import (
    _DESC_MAX,
    _DESC_MIN,
    _TITLE_MAX,
    _TITLE_MIN,
    check_meta,
)


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _by_check(issues) -> dict[str, str]:
    return {i.check: i.severity for i in issues}


# ── Title ─────────────────────────────────────────────────────────────────────


def test_missing_title_is_error():
    issues = check_meta(_soup("<html><head></head></html>"))
    by = _by_check(issues)
    assert by["Missing title"] == "error"


def test_empty_title_is_error():
    issues = check_meta(_soup("<html><head><title>   </title></head></html>"))
    by = _by_check(issues)
    assert by["Missing title"] == "error"


def test_short_title_is_warning():
    title = "Hi"  # 2 chars < 10
    issues = check_meta(_soup(f"<html><head><title>{title}</title></head></html>"))
    by = _by_check(issues)
    assert by["Title too short"] == "warning"


def test_title_at_min_boundary_no_issue():
    title = "A" * _TITLE_MIN  # exactly 10 chars
    issues = check_meta(_soup(f"<html><head><title>{title}</title></head></html>"))
    assert not any(i.check.startswith("Title") for i in issues)


def test_title_at_max_boundary_no_issue():
    title = "A" * _TITLE_MAX  # exactly 60 chars
    issues = check_meta(_soup(f"<html><head><title>{title}</title></head></html>"))
    assert not any(i.check.startswith("Title") for i in issues)


def test_long_title_is_warning():
    title = "A" * (_TITLE_MAX + 1)  # 61 chars
    issues = check_meta(_soup(f"<html><head><title>{title}</title></head></html>"))
    by = _by_check(issues)
    assert by["Title too long"] == "warning"


def test_valid_title_no_issue():
    title = "Awesome Website — Products & Services"
    issues = check_meta(_soup(f"<html><head><title>{title}</title></head></html>"))
    assert not any(i.check.startswith("Title") for i in issues)


# ── Meta description ──────────────────────────────────────────────────────────


def test_missing_description_is_warning():
    issues = check_meta(_soup("<html><head><title>Valid Title Here!</title></head></html>"))
    by = _by_check(issues)
    assert by["Missing meta description"] == "warning"


def test_empty_description_is_warning():
    html = '<html><head><title>Valid Title Here!</title><meta name="description" content=""></head></html>'
    issues = check_meta(_soup(html))
    by = _by_check(issues)
    assert by["Missing meta description"] == "warning"


def _html_with_desc(title: str, desc: str) -> str:
    return (
        f"<html><head>"
        f"<title>{title}</title>"
        f'<meta name="description" content="{desc}">'
        f"</head></html>"
    )


_GOOD_TITLE = "A Good Page Title Here"


def test_short_description_is_warning():
    desc = "Too short"  # < 50 chars
    issues = check_meta(_soup(_html_with_desc(_GOOD_TITLE, desc)))
    by = _by_check(issues)
    assert by["Meta description too short"] == "warning"


def test_description_at_min_boundary_no_issue():
    desc = "A" * _DESC_MIN  # exactly 50 chars
    issues = check_meta(_soup(_html_with_desc(_GOOD_TITLE, desc)))
    assert not any(i.check.startswith("Meta description") for i in issues)


def test_description_at_max_boundary_no_issue():
    desc = "A" * _DESC_MAX  # exactly 160 chars
    issues = check_meta(_soup(_html_with_desc(_GOOD_TITLE, desc)))
    assert not any(i.check.startswith("Meta description") for i in issues)


def test_long_description_is_warning():
    desc = "A" * (_DESC_MAX + 1)  # 161 chars
    issues = check_meta(_soup(_html_with_desc(_GOOD_TITLE, desc)))
    by = _by_check(issues)
    assert by["Meta description too long"] == "warning"


def test_valid_description_no_issue():
    desc = "This is a great description that is within the recommended length limits for search engine snippets."
    issues = check_meta(_soup(_html_with_desc(_GOOD_TITLE, desc)))
    assert not any(i.check.startswith("Meta description") for i in issues)


# ── Canonical ─────────────────────────────────────────────────────────────────


def test_missing_canonical_is_info():
    issues = check_meta(_soup(_html_with_desc(_GOOD_TITLE, "A" * _DESC_MIN)))
    by = _by_check(issues)
    assert by["Missing canonical URL"] == "info"


def test_canonical_present_no_canonical_issue():
    html = (
        f"<html><head>"
        f"<title>{_GOOD_TITLE}</title>"
        f'<meta name="description" content="{"A" * _DESC_MIN}">'
        f'<link rel="canonical" href="https://example.com/page">'
        f"</head></html>"
    )
    issues = check_meta(_soup(html))
    assert not any(i.check == "Missing canonical URL" for i in issues)


# ── Combined ──────────────────────────────────────────────────────────────────


def test_all_clean_returns_only_canonical_info():
    """A page with perfect title and description still gets canonical info."""
    title = "Perfect Page Title for SEO"
    desc = "A" * _DESC_MIN
    html = _html_with_desc(title, desc)
    issues = check_meta(_soup(html))
    checks = {i.check for i in issues}
    assert checks == {"Missing canonical URL"}
