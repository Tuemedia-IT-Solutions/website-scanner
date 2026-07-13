"""
scanner/scans/performance.py

Performance scan - measures HTTP response time and content size per page.

Uses the shared PageCache so no extra network requests are made when other
scans have already fetched the page in the same run.  The timings come
directly from requests.Response.elapsed (time from sending the request to
receiving the last byte of the response body).
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from rich import box
from rich.console import Console
from rich.table import Table

__all__ = ["run", "PagePerformance"]

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15

# Response-time thresholds in milliseconds
_FAST_MS = 500
_SLOW_MS = 2_000


@dataclass
class PagePerformance:
    url: str
    response_time_ms: float | None
    content_size_bytes: int | None
    status_code: int | None
    error: str | None = None


# ── Public API ────────────────────────────────────────────────────────────────


def run(pages: list[str], console: Console, config: dict) -> list[PagePerformance]:
    """Measure response time and content size for each page."""
    cache = config.get("page_cache")
    results: list[PagePerformance] = []

    for url in pages:
        with console.status(f"[dim]Performance: {url}…[/dim]"):
            results.append(_measure(url, cache))

    _render(results, console)
    return results


# ── Internals ─────────────────────────────────────────────────────────────────


def _measure(url: str, cache=None) -> PagePerformance:
    try:
        resp = (
            cache.get(url)
            if cache is not None
            else requests.get(
                url, timeout=_TIMEOUT, headers=_HEADERS, allow_redirects=True
            )
        )
    except requests.RequestException as exc:
        return PagePerformance(
            url=url,
            response_time_ms=None,
            content_size_bytes=None,
            status_code=None,
            error=str(exc),
        )

    elapsed_ms = round(resp.elapsed.total_seconds() * 1000, 1) if resp.elapsed else None
    return PagePerformance(
        url=url,
        response_time_ms=elapsed_ms,
        content_size_bytes=len(resp.content),
        status_code=resp.status_code,
    )


def _rating(ms: float | None) -> tuple[str, str]:
    """Return (rich-colour, label) for a response time."""
    if ms is None:
        return "red", "ERROR"
    if ms < _FAST_MS:
        return "green", "FAST"
    if ms < _SLOW_MS:
        return "yellow", "SLOW"
    return "red", "VERY SLOW"


def _render(results: list[PagePerformance], console: Console) -> None:
    table = Table(
        box=box.SIMPLE_HEAD, show_header=True, header_style="bold", padding=(0, 1)
    )
    table.add_column("URL", min_width=40)
    table.add_column("Time (ms)", width=10, justify="right")
    table.add_column("Size (KB)", width=10, justify="right")
    table.add_column("Rating", width=10)

    for r in results:
        colour, label = _rating(r.response_time_ms)
        time_str = (
            f"[{colour}]{r.response_time_ms:.0f}[/{colour}]"
            if r.response_time_ms is not None
            else "[red]-[/red]"
        )
        size_str = (
            f"{r.content_size_bytes / 1024:.1f}"
            if r.content_size_bytes is not None
            else "-"
        )
        table.add_row(r.url, time_str, size_str, f"[{colour}]{label}[/{colour}]")

    console.print(table)

    timed = [r for r in results if r.response_time_ms is not None]
    slow = sum(1 for r in timed if r.response_time_ms >= _FAST_MS)
    avg_ms = sum(r.response_time_ms for r in timed) / len(timed) if timed else 0
    colour = "red" if slow > len(results) // 2 else "yellow" if slow else "green"
    console.print(
        f"[{colour}]Performance: {len(results)} page(s) · "
        f"avg {avg_ms:.0f} ms · {slow} slow (≥{_FAST_MS} ms)[/{colour}]\n"
    )
