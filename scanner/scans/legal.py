"""
scanner/scans/legal.py
======================
Legal Links Check

For each scanned page, verify that:

1. A link to the **imprint** (German: Impressum) is present.
   Matched by href path or visible link text.
2. A link to the **privacy policy** (German: Datenschutz) is present.
   Matched by href path or visible link text.

Reports per-page whether both links are reachable from that page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15

# ── Link-detection patterns ───────────────────────────────────────────────────
# Matched against href (path portion) OR the stripped visible text of <a>.

_IMPRINT_HREF = re.compile(
    r"/(impressum|imprint|legal[-/]?impressum|legal[-/]?notice)",
    re.IGNORECASE,
)
_IMPRINT_TEXT = re.compile(
    r"\b(impressum|imprint|legal\s+notice)\b",
    re.IGNORECASE,
)

_PRIVACY_HREF = re.compile(
    r"/(datenschutz(erkl[äa]rung)?|privacy[-_]?policy|privacy|privacypolicy)",
    re.IGNORECASE,
)
_PRIVACY_TEXT = re.compile(
    r"\b(datenschutz(erkl[äa]rung)?|privacy\s+policy|privacy)\b",
    re.IGNORECASE,
)

_AGB_HREF = re.compile(
    r"/(agb|terms[-_]?(and[-_])?conditions?|terms[-_]?of[-_]?(service|use)|tos)",
    re.IGNORECASE,
)
_AGB_TEXT = re.compile(
    r"\b(agb|allgemeine\s+gesch[äa]ftsbedingungen|terms\s+(and\s+)?conditions?|terms\s+of\s+(service|use))\b",
    re.IGNORECASE,
)


# ── Result type ───────────────────────────────────────────────────────────────


@dataclass
class LegalLinksResult:
    url: str
    has_imprint_link: bool = False
    has_privacy_link: bool = False
    has_agb_link: bool = False
    imprint_href: str | None = None
    privacy_href: str | None = None
    agb_href: str | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.has_imprint_link and self.has_privacy_link


# ── Public API ────────────────────────────────────────────────────────────────


def run(pages: list[str], console: Console, config: dict) -> list[LegalLinksResult]:
    """Scan each page for imprint and privacy policy links."""
    results: list[LegalLinksResult] = []

    for url in pages:
        with console.status(f"[dim]Checking legal links: {url}…[/dim]"):
            results.append(_check_page(url))

    _render(results, console)
    return results


# ── Internals ─────────────────────────────────────────────────────────────────


def _check_page(url: str) -> LegalLinksResult:
    result = LegalLinksResult(url=url)

    try:
        resp = requests.get(
            url, timeout=_TIMEOUT, headers=_HEADERS, allow_redirects=True
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        result.errors.append("Request timed out")
        return result
    except requests.exceptions.ConnectionError as exc:
        result.errors.append(f"Connection error: {exc}")
        return result
    except requests.RequestException as exc:
        result.errors.append(str(exc))
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup.find_all("a", href=True):
        href: str = tag["href"].strip()
        text: str = tag.get_text(strip=True)

        if not result.has_imprint_link:
            if _IMPRINT_HREF.search(href) or _IMPRINT_TEXT.search(text):
                result.has_imprint_link = True
                result.imprint_href = href

        if not result.has_privacy_link:
            if _PRIVACY_HREF.search(href) or _PRIVACY_TEXT.search(text):
                result.has_privacy_link = True
                result.privacy_href = href

        if not result.has_agb_link:
            if _AGB_HREF.search(href) or _AGB_TEXT.search(text):
                result.has_agb_link = True
                result.agb_href = href

        if result.has_imprint_link and result.has_privacy_link and result.has_agb_link:
            break

    return result


def _render(results: list[LegalLinksResult], console: Console) -> None:
    missing_both = sum(
        1
        for r in results
        if not r.has_imprint_link and not r.has_privacy_link and not r.errors
    )
    missing_one = sum(
        1 for r in results if (r.has_imprint_link ^ r.has_privacy_link) and not r.errors
    )
    errors = sum(1 for r in results if r.errors)
    ok_count = sum(1 for r in results if r.ok)

    def _link_cell(found: bool, href: str | None) -> str:
        if found and href:
            return f"[green]✓[/green] [dim]{href}[/dim]"
        if found:
            return "[green]✓[/green]"
        return "[red]✗ missing[/red]"

    table = Table(
        box=box.SIMPLE_HEAD, show_header=True, header_style="bold", padding=(0, 1)
    )
    table.add_column("Page URL")
    table.add_column("Imprint", width=30)
    table.add_column("Privacy", width=30)
    table.add_column("AGB", width=20)
    table.add_column("Notes", style="dim")

    # Sort: errors first, then pages missing links, then ok
    def _sort_key(r: LegalLinksResult) -> int:
        if r.errors:
            return 0
        if not r.ok:
            return 1
        return 2

    for r in sorted(results, key=_sort_key):
        notes = "; ".join(r.errors) if r.errors else ""
        if r.errors:
            table.add_row(
                r.url,
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                "[dim]—[/dim]",
                f"[red]{notes}[/red]",
            )
        else:
            agb_cell = (
                _link_cell(r.has_agb_link, r.agb_href)
                if r.has_agb_link
                else "[dim]—[/dim]"
            )
            table.add_row(
                r.url,
                _link_cell(r.has_imprint_link, r.imprint_href),
                _link_cell(r.has_privacy_link, r.privacy_href),
                agb_cell,
                notes,
            )

    issues = missing_both + missing_one
    border = "red" if issues or errors else "green"
    console.print(
        Panel(
            table,
            title=(
                f"[bold]Legal Links Check[/bold]  "
                f"[green]{ok_count} ok[/green] · "
                f"[red]{issues} missing[/red] · "
                f"[yellow]{errors} error(s)[/yellow]"
            ),
            border_style=border,
            padding=(0, 1),
        )
    )
