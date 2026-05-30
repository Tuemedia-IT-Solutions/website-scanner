"""Integration tests for scanner/scans/seo/__init__.py (the run() entry point)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from rich.console import Console

from scanner.scans.seo import run

# ── Helpers ───────────────────────────────────────────────────────────────────


def _mock_response(html: str, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.content = html.encode("utf-8")
    resp.status_code = status
    if status >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"HTTP {status}", response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def _null_console() -> Console:
    """Console that discards all output (no TTY noise in tests)."""
    return Console(quiet=True)


_GOOD_PAGE_HTML = """<!DOCTYPE html>
<html>
<head>
  <title>A Good Example Page for Testing</title>
  <meta name="description" content="This is a very informative description for the test page that is within the correct length range.">
  <link rel="canonical" href="https://example.com/page">
</head>
<body>
  <h1>Main Heading</h1>
  <h2>Sub-section</h2>
  <img src="photo.jpg" alt="A descriptive photo of something meaningful">
</body>
</html>"""

_PROBLEM_PAGE_HTML = """<!DOCTYPE html>
<html>
<head></head>
<body>
  <h2>No H1 here</h2>
  <img src="bad.jpg">
</body>
</html>"""


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_run_returns_one_result_per_page():
    pages = ["https://example.com/a", "https://example.com/b"]
    with patch("scanner.scans.seo.requests.get", return_value=_mock_response(_GOOD_PAGE_HTML)):
        results = run(pages, _null_console(), {})
    assert len(results) == 2
    assert results[0].url == "https://example.com/a"
    assert results[1].url == "https://example.com/b"


def test_run_good_page_has_no_issues():
    with patch("scanner.scans.seo.requests.get", return_value=_mock_response(_GOOD_PAGE_HTML)):
        results = run(["https://example.com/"], _null_console(), {})
    assert results[0].fetch_error is None
    assert results[0].issues == []


def test_run_problem_page_has_issues():
    with patch(
        "scanner.scans.seo.requests.get",
        return_value=_mock_response(_PROBLEM_PAGE_HTML),
    ):
        results = run(["https://example.com/bad"], _null_console(), {})
    issue_checks = {i.check for i in results[0].issues}
    assert "Missing H1" in issue_checks
    assert "Missing ALT attribute" in issue_checks
    assert "Missing title" in issue_checks


def test_run_http_error_sets_fetch_error():
    with patch("scanner.scans.seo.requests.get", return_value=_mock_response("", status=404)):
        results = run(["https://example.com/missing"], _null_console(), {})
    assert results[0].fetch_error is not None
    assert results[0].issues == []


def test_run_connection_error_sets_fetch_error():
    with patch(
        "scanner.scans.seo.requests.get",
        side_effect=requests.exceptions.ConnectionError("refused"),
    ):
        results = run(["https://example.com/down"], _null_console(), {})
    assert "refused" in results[0].fetch_error
    assert results[0].issues == []


def test_run_timeout_sets_fetch_error():
    with patch(
        "scanner.scans.seo.requests.get",
        side_effect=requests.exceptions.Timeout("timed out"),
    ):
        results = run(["https://example.com/slow"], _null_console(), {})
    assert results[0].fetch_error is not None
    assert results[0].issues == []


def test_run_empty_page_list_returns_empty():
    results = run([], _null_console(), {})
    assert results == []
