"""Tests for scanner/scans/seo/content.py"""

from __future__ import annotations

from bs4 import BeautifulSoup

from scanner.scans.seo.content import check_content


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _words(n: int) -> str:
    return " ".join(["word"] * n)


# ── Thin content ──────────────────────────────────────────────────────────────


def test_zero_words_is_warning():
    issues = check_content(_soup("<body></body>"))
    assert any(i.check == "Very thin content" for i in issues)


def test_99_words_is_warning():
    issues = check_content(_soup(f"<body><p>{_words(99)}</p></body>"))
    assert any(i.check == "Very thin content" for i in issues)
    issue = next(i for i in issues if i.check == "Very thin content")
    assert issue.severity == "warning"


def test_100_words_is_ok():
    issues = check_content(_soup(f"<body><p>{_words(100)}</p></body>"))
    assert not any(i.check == "Very thin content" for i in issues)


def test_200_words_is_ok():
    issues = check_content(_soup(f"<body><p>{_words(200)}</p></body>"))
    assert not any(i.severity in ("error", "warning") for i in issues)


def test_script_content_excluded():
    # 5 real words + lots of script "words" — should still be flagged as thin
    html = f"<body><p>{_words(5)}</p><script>{_words(200)}</script></body>"
    issues = check_content(_soup(html))
    assert any(i.check == "Very thin content" for i in issues)
