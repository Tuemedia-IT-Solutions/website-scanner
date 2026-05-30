"""
scanner/scans/link_check.py

Sitemap Link Check — verifies that every URL in the selected page list
is reachable and returns an expected HTTP status code.

For each URL:
  - 2xx → ok
  - 3xx → warning (redirect; follows and reports final destination)
  - 4xx → error
  - 5xx → error
  - Connection / timeout → error
"""

from __future__ import annotations

from dataclasses import dataclass

import requests
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15

_ICONS = {
    "ok": "[bold green]✓ ok[/bold green]",
    "redirect": "[bold yellow]↪ redirect[/bold yellow]",
    "error": "[bold red]✗ error[/bold red]",
}


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass
class LinkResult:
    url: str
    status: int | None = None  # None means connection-level failure
    final_url: str | None = None  # set when redirected
    error: str | None = None

    @property
    def severity(self) -> str:
        if self.error:
            return "error"
        if self.status is None:
            return "error"
        if self.status < 300:
            return "ok"
        if self.status < 400:
            return "redirect"
        return "error"

    @property
    def status_label(self) -> str:
        if self.status is None:
            return "—"
        return str(self.status)


# ── Public API ────────────────────────────────────────────────────────────────


def run(pages: list[str], console: Console, config: dict) -> list[LinkResult]:
    """Check HTTP reachability of every page."""
    results: list[LinkResult] = []

    for url in pages:
        with console.status(f"[dim]Checking: {url}…[/dim]"):
            results.append(_check_url(url))

    _render(results, console)
    return results


# ── Internals ─────────────────────────────────────────────────────────────────


def _check_url(url: str) -> LinkResult:
    result = LinkResult(url=url)

    try:
        resp = requests.get(
            url,
            timeout=_TIMEOUT,
            headers=_HEADERS,
            allow_redirects=True,
        )
        result.status = resp.status_code

        # Record final URL if a redirect occurred
        if resp.history:
            result.final_url = resp.url if resp.url != url else None

    except requests.exceptions.Timeout:
        result.error = "Request timed out"
    except requests.exceptions.ConnectionError as exc:
        result.error = f"Connection error: {exc}"
    except requests.RequestException as exc:
        result.error = str(exc)

    return result


def _render(results: list[LinkResult], console: Console) -> None:
    errors = sum(1 for r in results if r.severity == "error")
    redirects = sum(1 for r in results if r.severity == "redirect")
    ok_count = sum(1 for r in results if r.severity == "ok")

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Status", width=7, justify="right")
    table.add_column("Result", width=10)
    table.add_column("URL")
    table.add_column("Detail", style="dim")

    # Sort: errors first, then redirects, then ok
    _order = {"error": 0, "redirect": 1, "ok": 2}
    for r in sorted(results, key=lambda x: _order[x.severity]):
        detail = ""
        if r.error:
            detail = r.error
        elif r.final_url:
            detail = f"→ {r.final_url}"

        table.add_row(
            r.status_label,
            _ICONS.get(r.severity, r.severity),
            r.url,
            detail,
        )

    border = "red" if errors else "yellow" if redirects else "green"
    console.print(
        Panel(
            table,
            title=(
                f"[bold]Sitemap Link Check[/bold]  "
                f"[green]{ok_count} ok[/green] · "
                f"[yellow]{redirects} redirect(s)[/yellow] · "
                f"[red]{errors} error(s)[/red]"
            ),
            border_style=border,
            padding=(0, 1),
        )
    )
