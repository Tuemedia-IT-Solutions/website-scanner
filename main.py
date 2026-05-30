"""
Website Scanning Tool — by Tuemedia IT
Entry point / main orchestrator.
"""

import argparse
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from scanner.crawler import (
    detect_imprint_url,
    fetch_sitemap,
    normalize_url,
    suggest_sitemap_url,
)
from scanner.scans import run_scans
from scanner.selector import select_pages, select_scans

console = Console()

BANNER = """[bold blue]Website Scanning Tool[/bold blue]
[dim]by Tuemedia IT[/dim]"""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Website Scanning Tool by Tuemedia IT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="Domain or URL to scan (e.g. example.com or https://example.com)",
    )
    parser.add_argument(
        "--all-pages",
        action="store_true",
        help="Skip interactive page selection and scan all discovered pages",
    )
    args = parser.parse_args()

    console.print(Panel.fit(BANNER, border_style="blue", padding=(1, 4)))

    # ── 1. Get target URL ─────────────────────────────────────────────────────
    target_raw = args.url or Prompt.ask("\n[bold]Enter domain or URL[/bold]")
    target = normalize_url(target_raw)
    console.print(f"[dim]Target:[/dim] [cyan]{target}[/cyan]")

    # ── 2. Confirm / modify sitemap URL ───────────────────────────────────────
    with console.status("[dim]Looking for sitemap in robots.txt…[/dim]"):
        suggested = suggest_sitemap_url(target)

    sitemap_url = Prompt.ask(
        "\n[bold]Sitemap URL[/bold]",
        default=suggested,
    )

    # ── 3. Fetch sitemap ──────────────────────────────────────────────────────
    with console.status("[bold green]Fetching sitemap…[/bold green]"):
        pages = fetch_sitemap(sitemap_url)

    if not pages:
        console.print(
            "\n[red]No pages could be found in the sitemap.[/red]\n"
            "[dim]Check that the URL is correct and the sitemap is publicly accessible.[/dim]"
        )
        sys.exit(1)

    console.print(f"\n[green]✓[/green] Found [bold]{len(pages)}[/bold] pages in sitemap.")

    # ── 4. Interactive page selection ─────────────────────────────────────────
    if args.all_pages:
        selected_pages = pages
        console.print(f"[dim]--all-pages flag set — scanning all {len(pages)} pages.[/dim]")
    else:
        selected_pages = select_pages(pages)

    if not selected_pages:
        console.print("\n[yellow]No pages selected. Exiting.[/yellow]")
        sys.exit(0)

    console.print(
        f"\n[green]✓[/green] [bold]{len(selected_pages)}[/bold] page(s) selected for scanning."
    )

    # ── 5. Select scans ───────────────────────────────────────────────────────
    selected_scans = select_scans()

    if not selected_scans:
        console.print("\n[yellow]No scans selected. Exiting.[/yellow]")
        sys.exit(0)

    # ── 5a. Per-scan setup prompts ────────────────────────────────────────────
    scan_config: dict = {}

    if "imprint_check" in selected_scans:
        with console.status("[dim]Auto-detecting imprint page…[/dim]"):
            detected = detect_imprint_url(target)

        if detected:
            console.print(f"\n[dim]Imprint page detected:[/dim] [cyan]{detected}[/cyan]")
        else:
            console.print("\n[yellow]Could not auto-detect imprint page.[/yellow]")

        imprint_url = Prompt.ask(
            "[bold]Imprint URL[/bold]",
            default=detected or f"{target}/impressum",
        )
        scan_config["imprint_url"] = imprint_url

    # ── 6. Run scans ──────────────────────────────────────────────────────────
    run_scans(selected_pages, selected_scans, console, scan_config)


if __name__ == "__main__":
    main()
