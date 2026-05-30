"""Tests for scanner/scans/seo/headings.py"""

from __future__ import annotations

from bs4 import BeautifulSoup

from scanner.scans.seo.headings import check_headings


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _by_check(issues) -> dict[str, str]:
    return {i.check: i.severity for i in issues}


# ── Missing H1 ────────────────────────────────────────────────────────────────


def test_no_headings_at_all_reports_missing_h1():
    issues = check_headings(_soup("<p>No headings</p>"))
    by = _by_check(issues)
    assert by["Missing H1"] == "error"


def test_only_h2_reports_missing_h1():
    issues = check_headings(_soup("<h2>Section</h2>"))
    by = _by_check(issues)
    assert by["Missing H1"] == "error"


def test_single_h1_no_issues():
    issues = check_headings(_soup("<h1>Page Title</h1>"))
    assert issues == []


# ── Multiple H1 ───────────────────────────────────────────────────────────────


def test_two_h1s_is_warning():
    issues = check_headings(_soup("<h1>First</h1><h1>Second</h1>"))
    by = _by_check(issues)
    assert by["Multiple H1 elements"] == "warning"


def test_three_h1s_is_warning():
    html = "<h1>A</h1><h1>B</h1><h1>C</h1>"
    issues = check_headings(_soup(html))
    by = _by_check(issues)
    assert by["Multiple H1 elements"] == "warning"
    # detail mentions count
    detail = next(i.detail for i in issues if i.check == "Multiple H1 elements")
    assert "3" in detail


# ── Skipped levels ────────────────────────────────────────────────────────────


def test_h1_to_h3_skip_is_warning():
    html = "<h1>Title</h1><h3>Sub-section</h3>"
    issues = check_headings(_soup(html))
    by = _by_check(issues)
    assert by["Skipped heading level"] == "warning"


def test_h1_to_h2_to_h3_no_skip():
    html = "<h1>Title</h1><h2>Section</h2><h3>Sub</h3>"
    issues = check_headings(_soup(html))
    assert not any(i.check == "Skipped heading level" for i in issues)


def test_skip_detail_mentions_levels():
    html = "<h1>Title</h1><h4>Deep</h4>"
    issues = check_headings(_soup(html))
    skip = next(i for i in issues if i.check == "Skipped heading level")
    assert "H1" in skip.detail
    assert "H4" in skip.detail


def test_h2_to_h4_skip_is_warning():
    html = "<h1>Title</h1><h2>Section</h2><h4>Deep</h4>"
    issues = check_headings(_soup(html))
    by = _by_check(issues)
    assert by["Skipped heading level"] == "warning"


# ── Element snippets ──────────────────────────────────────────────────────────


def test_multiple_h1_element_snippet_contains_texts():
    issues = check_headings(_soup("<h1>Alpha</h1><h1>Beta</h1>"))
    multi = next(i for i in issues if i.check == "Multiple H1 elements")
    assert multi.element is not None
    assert "Alpha" in multi.element
    assert "Beta" in multi.element


def test_skip_element_snippet_is_set():
    html = "<h1>Title</h1><h3>Jump</h3>"
    issues = check_headings(_soup(html))
    skip = next(i for i in issues if i.check == "Skipped heading level")
    assert skip.element is not None
    assert "h3" in skip.element
