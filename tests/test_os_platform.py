"""Tests for scanner/scans/os_platform.py"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests
from rich.console import Console

from scanner.scans.os_platform import _check_page, run

_PAGE = "https://example.com/impressum"


def _resp(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status.return_value = None
    return resp


def _check(html: str):
    with patch("scanner.scans.os_platform.requests.get", return_value=_resp(html)):
        return _check_page(_PAGE)


def test_detects_odr_link():
    r = _check('<a href="http://ec.europa.eu/consumers/odr/">ODR</a>')
    assert r.links == ["http://ec.europa.eu/consumers/odr/"]
    assert not r.ok


def test_detects_webgate_link():
    r = _check('<a href="https://webgate.ec.europa.eu/odr">x</a>')
    assert len(r.links) == 1


def test_detects_text_with_curly_quotes():
    r = _check("<p>Die EU hat eine Plattform („OS-Plattform\") geschaffen.</p>")
    assert r.text_excerpts
    assert not r.ok


def test_detects_online_streitbeilegung_heading():
    r = _check("<h2>Online-Streitbeilegung</h2>")
    assert r.text_excerpts


def test_clean_page_is_ok():
    r = _check('<p>Impressum</p><a href="https://example.com/kontakt">Kontakt</a>')
    assert r.ok
    assert not r.errors


def test_duplicate_links_reported_once():
    html = '<a href="http://ec.europa.eu/consumers/odr/">a</a>' * 2
    assert len(_check(html).links) == 1


def test_timeout_recorded_as_error():
    with patch(
        "scanner.scans.os_platform.requests.get",
        side_effect=requests.exceptions.Timeout,
    ):
        r = _check_page(_PAGE)
    assert r.errors == ["Request timed out"]


def test_run_adds_imprint_url_when_not_in_pages():
    with patch("scanner.scans.os_platform.requests.get", return_value=_resp("<p></p>")) as get:
        results = run(
            ["https://example.com/"],
            Console(quiet=True),
            {"imprint_url": _PAGE},
        )
    assert [r.url for r in results] == ["https://example.com/", _PAGE]
    assert get.call_count == 2


def test_run_does_not_duplicate_imprint_url():
    with patch("scanner.scans.os_platform.requests.get", return_value=_resp("<p></p>")):
        results = run([_PAGE], Console(quiet=True), {"imprint_url": _PAGE})
    assert len(results) == 1
