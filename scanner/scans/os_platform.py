"""
scanner/scans/os_platform.py
============================
Outdated EU OS-Plattform Check

The EU Online Dispute Resolution platform (ec.europa.eu/consumers/odr) was
shut down on 20 July 2025. The obligation to link to it no longer applies, and
leftover links/notices can be considered misleading (Abmahnung risk).

For each page, flag links to the platform and text mentions of it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import requests
from bs4 import BeautifulSoup
from rich import box
from rich.console import Console
from rich.table import Table

_HEADERS = {"User-Agent": "TuemediaWebsiteScanner/1.0 (+https://tuemedia.de)"}
_TIMEOUT = 15

_ODR_HREF = re.compile(
    r"ec\.europa\.eu/(consumers/odr|odr)|webgate\.ec\.europa\.eu/odr",
    re.IGNORECASE,
)
_ODR_TEXT = re.compile(
    r"\bOS[-\s]?Plattform\b|Online[-\s]Streitbeilegung|"
    r"\bOnline\s+Dispute\s+Resolution\b|\bODR[-\s]Plattform\b",
    re.IGNORECASE,
)


@dataclass
class OsPlatformResult:
    url: str
    links: list[str] = field(default_factory=list)
    text_excerpts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.links and not self.text_excerpts


def run(pages: list[str], console: Console, config: dict) -> list[OsPlatformResult]:
    """Scan each page for outdated references to the EU OS-Plattform."""
    results: list[OsPlatformResult] = []
    for url in pages:
        with console.status(f"[dim]Checking OS-Plattform references: {url}…[/dim]"):
            results.append(_check_page(url))
    _render(results, console)
    return results


def _check_page(url: str) -> OsPlatformResult:
    result = OsPlatformResult(url=url)

    try:
        resp = requests.get(url, timeout=_TIMEOUT, headers=_HEADERS, allow_redirects=True)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        result.errors.append("Request timed out")
        return result
    except requests.RequestException as exc:
        result.errors.append(str(exc))
        return result

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if _ODR_HREF.search(href) and href not in result.links:
            result.links.append(href)

    body_text = " ".join(soup.get_text(" ").split())
    for match in _ODR_TEXT.finditer(body_text):
        start = max(0, match.start() - 60)
        excerpt = body_text[start : match.end() + 60]
        if excerpt not in result.text_excerpts:
            result.text_excerpts.append(excerpt)
        if len(result.text_excerpts) >= 3:
            break

    return result


def _render(results: list[OsPlatformResult], console: Console) -> None:
    flagged = [r for r in results if not r.ok]
    errored = [r for r in results if r.errors]

    if flagged:
        table = Table(
            title="Outdated EU OS-Plattform references",
            box=box.SIMPLE_HEAD,
            show_lines=False,
        )
        table.add_column("Page", overflow="fold")
        table.add_column("Link", overflow="fold")
        table.add_column("Text excerpt", overflow="fold")
        for r in flagged:
            table.add_row(
                r.url,
                "\n".join(r.links) or "-",
                "\n".join(f"…{e}…" for e in r.text_excerpts) or "-",
            )
        console.print(table)
        console.print(
            "[yellow]The OS-Plattform was shut down on 20 July 2025. "
            "Remove these links/notices (also from AGB and e-mail signatures) "
            "to avoid Abmahnung risk.[/yellow]\n"
        )
    else:
        console.print("[green]✓[/green] No outdated OS-Plattform references found.\n")

    for r in errored:
        console.print(f"[red]Error[/red] {r.url}: {'; '.join(r.errors)}")
