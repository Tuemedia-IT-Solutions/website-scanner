"""Tests for scanner/scans/seo/images.py"""

from __future__ import annotations

import pytest
from bs4 import BeautifulSoup

from scanner.scans.seo.images import check_images


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _by_check(issues) -> dict[str, str]:
    """Map check name → severity."""
    return {i.check: i.severity for i in issues}


# ── Missing ALT ───────────────────────────────────────────────────────────────


def test_missing_alt_is_error():
    issues = check_images(_soup('<img src="photo.jpg">'))
    by = _by_check(issues)
    assert by["Missing ALT attribute"] == "error"


def test_missing_alt_element_snippet_included():
    issues = check_images(_soup('<img src="photo.jpg">'))
    assert issues[0].element is not None
    assert "photo.jpg" in issues[0].element


def test_no_images_returns_empty():
    assert check_images(_soup("<p>No images here</p>")) == []


# ── Empty ALT ─────────────────────────────────────────────────────────────────


def test_empty_alt_without_role_is_warning():
    issues = check_images(_soup('<img src="x.jpg" alt="">'))
    by = _by_check(issues)
    assert by["Empty ALT attribute"] == "warning"


def test_empty_alt_with_role_presentation_no_issue():
    issues = check_images(_soup('<img src="x.jpg" alt="" role="presentation">'))
    assert issues == []


def test_empty_alt_with_role_none_no_issue():
    issues = check_images(_soup('<img src="x.jpg" alt="" role="none">'))
    assert issues == []


def test_empty_alt_whitespace_only_is_warning():
    issues = check_images(_soup('<img src="x.jpg" alt="   ">'))
    by = _by_check(issues)
    assert by["Empty ALT attribute"] == "warning"


# ── Generic ALT ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "alt",
    [
        "image",
        "img",
        "foto",
        "bild",
        "picture",
        "photo",
        "graphic",
        "icon",
        "banner",
        "logo",
        "thumbnail",
    ],
)
def test_generic_alt_is_warning(alt: str):
    issues = check_images(_soup(f'<img src="x.jpg" alt="{alt}">'))
    by = _by_check(issues)
    assert by["Generic ALT text"] == "warning"


def test_generic_alt_case_insensitive():
    issues = check_images(_soup('<img src="x.jpg" alt="LOGO">'))
    by = _by_check(issues)
    assert by["Generic ALT text"] == "warning"


def test_generic_alt_with_trailing_digit_is_warning():
    issues = check_images(_soup('<img src="x.jpg" alt="image1">'))
    by = _by_check(issues)
    assert by["Generic ALT text"] == "warning"


# ── Valid ALT ─────────────────────────────────────────────────────────────────


def test_valid_descriptive_alt_no_issue():
    issues = check_images(_soup('<img src="x.jpg" alt="A photo of the Berlin skyline">'))
    assert issues == []


# ── Snippet helper ────────────────────────────────────────────────────────────


def test_long_src_is_truncated_in_snippet():
    long_src = "https://example.com/" + "a" * 100
    issues = check_images(_soup(f'<img src="{long_src}">'))
    assert issues[0].element is not None
    assert "…" in issues[0].element


def test_multiple_images_multiple_issues():
    html = '<img src="a.jpg"><img src="b.jpg" alt="">'
    issues = check_images(_soup(html))
    checks = {i.check for i in issues}
    assert "Missing ALT attribute" in checks
    assert "Empty ALT attribute" in checks
