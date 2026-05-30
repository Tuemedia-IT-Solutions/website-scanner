"""
scanner/scans/__init__.py

Scan orchestrator — dispatches selected scans to their modules
and renders a final results summary.
"""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import accessibility, imprint, legal, link_check, seo, tmg_check

# Maps scan keys (from selector.py) to their module.
# Each module must expose: run(pages, console, config) -> Any
_REGISTRY = {
    "imprint_check": imprint,
    "link_check": link_check,
    "legal_links": legal,
    "tmg_check": tmg_check,
    "seo": seo,
    "accessibility": accessibility,
}


def run_scans(
    pages: list[str],
    selected_scan_keys: list[str],
    console: Console,
    scan_config: dict | None = None,
) -> None:
    """
    Run each selected scan against all selected pages.

    *scan_config* is an optional dict of per-scan settings, e.g.::

        {"imprint_url": "https://example.com/impressum"}
    """
    scan_config = scan_config or {}

    console.print(
        Panel.fit(
            f"[bold]Running [cyan]{len(selected_scan_keys)}[/cyan] scan(s) "
            f"on [cyan]{len(pages)}[/cyan] page(s)[/bold]",
            border_style="yellow",
        )
    )

    for key in selected_scan_keys:
        module = _REGISTRY.get(key)
        if module is None:
            console.print(f"[red]Unknown scan key:[/red] {key}")
            continue
        try:
            module.run(pages, console, scan_config)  # type: ignore[attr-defined]
        except NotImplementedError:
            _print_not_implemented(key, console)


def _print_not_implemented(key: str, console: Console) -> None:
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="yellow")
    table.add_column()
    table.add_row("Scan:", key)
    table.add_row("Status:", "[yellow]Not yet implemented — coming soon[/yellow]")
    console.print(table)
    console.print()
