"""
scanner/scans/seo/__init__.py

SEO Scan — entry point.
Fetches each selected page, runs all check modules, and renders results.
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ._types import PageSeoResult, SeoIssue
from .headings import check_headings
from .images import check_images
from .meta import check_meta

__all__ = ["run", "SeoIssue", "PageSeoResult"]

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15

_ICONS = {
    "error": "[bold red]✗ error[/bold red]",
    "warning": "[bold yellow]⚠ warn[/bold yellow]",
    "info": "[dim]ℹ info[/dim]",
}
_ORDER = {"error": 0, "warning": 1, "info": 2}


# ── Public API ────────────────────────────────────────────────────────────────


def run(pages: list[str], console: Console, config: dict) -> list[PageSeoResult]:
    """Run all SEO checks on every selected page."""
    results: list[PageSeoResult] = []

    for url in pages:
        with console.status(f"[dim]SEO scan: {url}…[/dim]"):
            result = _scan_page(url)
        results.append(result)
        _render_page(result, console)

    _render_summary(results, console)
    return results


# ── Internals ─────────────────────────────────────────────────────────────────


def _scan_page(url: str) -> PageSeoResult:
    result = PageSeoResult(url=url)

    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        result.fetch_error = str(exc)
        return result

    soup = BeautifulSoup(resp.content, "lxml")
    result.issues.extend(check_images(soup))
    result.issues.extend(check_headings(soup))
    result.issues.extend(check_meta(soup))
    return result


def _render_page(result: PageSeoResult, console: Console) -> None:
    if result.fetch_error:
        console.print(f"[red]✗[/red] [bold]{result.url}[/bold] — {result.fetch_error}")
        return

    errors = sum(1 for i in result.issues if i.severity == "error")
    warnings = sum(1 for i in result.issues if i.severity == "warning")

    if not result.issues:
        console.print(f"[green]✓[/green] {result.url}  [dim]No SEO issues[/dim]")
        return

    status_color = "red" if errors else "yellow" if warnings else "blue"
    status = f"[{status_color}]{errors} error(s) · {warnings} warning(s)[/{status_color}]"

    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold", padding=(0, 1))
    table.add_column("Severity", width=9)
    table.add_column("Check", min_width=24)
    table.add_column("Detail")

    for issue in sorted(result.issues, key=lambda i: _ORDER.get(i.severity, 9)):
        detail = issue.detail
        if issue.element:
            detail += f"\n[dim]→ {issue.element}[/dim]"
        table.add_row(_ICONS.get(issue.severity, issue.severity), issue.check, detail)

    console.print(
        Panel(
            table,
            title=f"[bold]{result.url}[/bold]  {status}",
            border_style=status_color,
            padding=(0, 1),
        )
    )


def _render_summary(results: list[PageSeoResult], console: Console) -> None:
    total_errors = sum(sum(1 for i in r.issues if i.severity == "error") for r in results)
    total_warnings = sum(sum(1 for i in r.issues if i.severity == "warning") for r in results)
    pages_with_issues = sum(1 for r in results if r.issues)

    color = "red" if total_errors else "yellow" if total_warnings else "green"
    console.print(
        f"\n[{color}]SEO: {len(results)} page(s) · "
        f"{pages_with_issues} with issues · "
        f"{total_errors} error(s) · {total_warnings} warning(s)[/{color}]\n"
    )
