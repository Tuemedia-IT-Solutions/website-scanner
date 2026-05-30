"""Tests for scanner/scans/link_check.py"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from rich.console import Console

from scanner.scans.link_check import LinkResult, _check_url, run


def _mock_response(status: int, final_url: str | None = None, history=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status
    resp.url = final_url or "https://example.com/"
    resp.history = history or []
    return resp


def _null_console() -> Console:
    return Console(quiet=True)


# ── LinkResult.severity ───────────────────────────────────────────────────────


def test_2xx_is_ok():
    r = LinkResult(url="https://x.com/", status=200)
    assert r.severity == "ok"


def test_204_is_ok():
    r = LinkResult(url="https://x.com/", status=204)
    assert r.severity == "ok"


def test_301_is_redirect():
    r = LinkResult(url="https://x.com/", status=301)
    assert r.severity == "redirect"


def test_302_is_redirect():
    r = LinkResult(url="https://x.com/", status=302)
    assert r.severity == "redirect"


def test_404_is_error():
    r = LinkResult(url="https://x.com/", status=404)
    assert r.severity == "error"


def test_500_is_error():
    r = LinkResult(url="https://x.com/", status=500)
    assert r.severity == "error"


def test_connection_error_is_error():
    r = LinkResult(url="https://x.com/", error="refused")
    assert r.severity == "error"


def test_status_none_without_error_is_error():
    r = LinkResult(url="https://x.com/", status=None)
    assert r.severity == "error"


# ── LinkResult.status_label ───────────────────────────────────────────────────


def test_status_label_returns_string():
    assert LinkResult(url="u", status=200).status_label == "200"


def test_status_label_none_returns_dash():
    assert LinkResult(url="u", status=None).status_label == "—"


# ── _check_url ────────────────────────────────────────────────────────────────


def test_check_url_200_ok():
    with patch("scanner.scans.link_check.requests.get", return_value=_mock_response(200)):
        result = _check_url("https://example.com/")
    assert result.status == 200
    assert result.severity == "ok"
    assert result.error is None


def test_check_url_404_error():
    with patch("scanner.scans.link_check.requests.get", return_value=_mock_response(404)):
        result = _check_url("https://example.com/missing")
    assert result.status == 404
    assert result.severity == "error"


def test_check_url_redirect_records_final_url():
    history = [MagicMock()]  # non-empty = redirect occurred
    resp = _mock_response(200, final_url="https://www.example.com/", history=history)
    with patch("scanner.scans.link_check.requests.get", return_value=resp):
        result = _check_url("https://example.com/")
    assert result.final_url == "https://www.example.com/"


def test_check_url_no_redirect_final_url_is_none():
    with patch(
        "scanner.scans.link_check.requests.get",
        return_value=_mock_response(200, final_url="https://example.com/", history=[]),
    ):
        result = _check_url("https://example.com/")
    assert result.final_url is None


def test_check_url_timeout_sets_error():
    with patch(
        "scanner.scans.link_check.requests.get",
        side_effect=requests.exceptions.Timeout(),
    ):
        result = _check_url("https://example.com/slow")
    assert result.error == "Request timed out"
    assert result.status is None


def test_check_url_connection_error_sets_error():
    with patch(
        "scanner.scans.link_check.requests.get",
        side_effect=requests.exceptions.ConnectionError("refused"),
    ):
        result = _check_url("https://example.com/down")
    assert result.error is not None
    assert "refused" in result.error


def test_check_url_generic_request_exception():
    with patch(
        "scanner.scans.link_check.requests.get",
        side_effect=requests.exceptions.RequestException("oops"),
    ):
        result = _check_url("https://example.com/")
    assert result.error == "oops"


# ── run() ─────────────────────────────────────────────────────────────────────


def test_run_returns_one_result_per_page():
    pages = ["https://example.com/a", "https://example.com/b", "https://example.com/c"]
    with patch("scanner.scans.link_check.requests.get", return_value=_mock_response(200)):
        results = run(pages, _null_console(), {})
    assert len(results) == 3
    assert [r.url for r in results] == pages


def test_run_empty_pages_returns_empty():
    results = run([], _null_console(), {})
    assert results == []


def test_run_mixed_results():
    def _side_effect(url, **kwargs):
        if "ok" in url:
            return _mock_response(200)
        if "missing" in url:
            return _mock_response(404)
        return _mock_response(200)

    pages = ["https://example.com/ok", "https://example.com/missing"]
    with patch("scanner.scans.link_check.requests.get", side_effect=_side_effect):
        results = run(pages, _null_console(), {})

    by_url = {r.url: r for r in results}
    assert by_url["https://example.com/ok"].severity == "ok"
    assert by_url["https://example.com/missing"].severity == "error"
