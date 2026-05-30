"""
scanner/crawler.py

Handles sitemap discovery, fetching, and parsing.
Supports both regular sitemaps and sitemap index files.
"""

from __future__ import annotations

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from rich.console import Console

console = Console()

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15


def normalize_url(url: str) -> str:
    """Ensure the URL has an https:// scheme and no trailing slash."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")


def suggest_sitemap_url(base_url: str) -> str:
    """
    Return the most likely sitemap URL for *base_url*.

    Strategy:
    1. Check robots.txt for a ``Sitemap:`` directive.
    2. Fall back to ``<origin>/sitemap.xml``.
    """
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    try:
        resp = requests.get(
            f"{origin}/robots.txt",
            timeout=10,
            headers=_HEADERS,
        )
        if resp.ok:
            for line in resp.text.splitlines():
                if re.match(r"sitemap\s*:", line, re.IGNORECASE):
                    candidate = line.split(":", 1)[1].strip()
                    if candidate:
                        return candidate
    except requests.RequestException:
        pass

    return f"{origin}/sitemap.xml"


# Candidate paths tried in order when auto-detecting the imprint page.
_IMPRINT_PATHS = [
    "/impressum",
    "/imprint",
    "/legal/impressum",
    "/legal/imprint",
    "/legal",
    "/legal-notice",
    "/de/impressum",
    "/kontakt/impressum",
]

# Link text / href substrings that indicate an imprint link.
_IMPRINT_LINK_PATTERNS = re.compile(
    r"impressum|imprint|legal\s*notice|legal\s*disclosure",
    re.IGNORECASE,
)


def detect_imprint_url(base_url: str) -> str | None:
    """
    Try to locate the imprint page for *base_url*.

    Strategy (first match wins):
    1. Check the homepage HTML for ``<a>`` tags whose href or visible text
       looks like an imprint link.
    2. Probe known canonical paths and return the first that responds with 200.

    Returns an absolute URL string, or ``None`` if nothing is found.
    """
    parsed = urlparse(base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    # ── 1. Scan homepage links ────────────────────────────────────────────────
    try:
        resp = requests.get(base_url, timeout=_TIMEOUT, headers=_HEADERS)
        if resp.ok:
            soup = BeautifulSoup(resp.content, "lxml")
            for tag in soup.find_all("a", href=True):
                href: str = tag["href"]
                text: str = tag.get_text(" ", strip=True)
                if _IMPRINT_LINK_PATTERNS.search(href) or _IMPRINT_LINK_PATTERNS.search(text):
                    # Resolve relative URLs
                    if href.startswith("http"):
                        return href.rstrip("/")
                    return (origin + "/" + href.lstrip("/")).rstrip("/")
    except requests.RequestException:
        pass

    # ── 2. Probe known paths ──────────────────────────────────────────────────
    for path in _IMPRINT_PATHS:
        candidate = origin + path
        try:
            r = requests.head(candidate, timeout=8, headers=_HEADERS, allow_redirects=True)
            if r.status_code < 400:
                return candidate
        except requests.RequestException:
            continue

    return None


def fetch_sitemap(sitemap_url: str, _visited: set[str] | None = None) -> list[str]:
    """
    Fetch *sitemap_url* and return a deduplicated, sorted list of page URLs.

    Recursively follows sitemap index files.
    """
    if _visited is None:
        _visited = set()

    if sitemap_url in _visited:
        return []
    _visited.add(sitemap_url)

    try:
        resp = requests.get(sitemap_url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        console.print(f"[red]Error fetching sitemap:[/red] {exc}")
        return []

    # Parse as XML
    soup = BeautifulSoup(resp.content, "lxml-xml")

    # ── Sitemap index? ────────────────────────────────────────────────────────
    child_sitemaps = soup.find_all("sitemap")
    if child_sitemaps:
        pages: list[str] = []
        for child in child_sitemaps:
            loc = child.find("loc")
            if loc and loc.text:
                pages.extend(fetch_sitemap(loc.text.strip(), _visited))
        return _dedup(pages)

    # ── Regular sitemap ───────────────────────────────────────────────────────
    urls = soup.find_all("url")
    pages = []
    for url_tag in urls:
        loc = url_tag.find("loc")
        if loc and loc.text:
            pages.append(loc.text.strip())

    # Fallback: plain-text sitemap (one URL per line)
    if not pages:
        for line in resp.text.splitlines():
            line = line.strip()
            if line.startswith("http"):
                pages.append(line)

    return _dedup(pages)


def _dedup(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            result.append(url)
    return result
