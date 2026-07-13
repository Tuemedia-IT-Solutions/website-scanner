"""
scanner/fetch.py

Per-run HTTP page cache.
Each URL is fetched at most once per PageCache instance.
"""

from __future__ import annotations

import requests

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15


class PageCache:
    """
    Caches HTTP responses by URL for the duration of a single scan run.

    The cache stores any HTTP response (any status code).  Network-level
    exceptions are *not* cached - they propagate to the caller so that
    existing ``except requests.RequestException`` blocks still work unchanged.

    Usage::

        cache = PageCache()
        resp = cache.get("https://example.com/page")  # fetched
        resp = cache.get("https://example.com/page")  # returned from cache
    """

    def __init__(self) -> None:
        self._cache: dict[str, requests.Response] = {}

    def get(self, url: str) -> requests.Response:
        """Return a cached Response, or fetch and cache it first."""
        if url not in self._cache:
            self._cache[url] = requests.get(
                url,
                timeout=_TIMEOUT,
                headers=_HEADERS,
                allow_redirects=True,
            )
        return self._cache[url]
