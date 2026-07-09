"""
Website Scanning Tool — by Tuemedia IT
Entry point / main orchestrator.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from scanner.crawler import (
    detect_imprint_url,
    fetch_sitemap,
    normalize_url,
    suggest_sitemap_url,
)
from scanner.report import generate as generate_pdf
from scanner.scans import run_scans
from scanner.selector import AVAILABLE_SCANS, select_pages, select_scans

console = Console()

BANNER = """[bold blue]Website Scanning Tool[/bold blue]
[dim]by Tuemedia IT[/dim]"""


def _is_excluded(url: str, patterns: list[str]) -> bool:
    """Return True if *url*'s path matches any of the glob *patterns*.

    A pattern ending with ``/`` is treated as a path-prefix (e.g. ``/blog/``
    excludes ``/blog/``, ``/blog/post/1``, etc.).  All other patterns are
    matched with :func:`fnmatch.fnmatch` against the URL path.
    """
    path = urlparse(url).path
    for pattern in patterns:
        if pattern.endswith("/") and path.startswith(pattern):
            return True
        if fnmatch(path, pattern):
            return True
    return False


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
    parser.add_argument(
        "--non-interactive",
        "-n",
        action="store_true",
        dest="non_interactive",
        help="Batch mode: skip all prompts, use auto-detection and defaults",
    )
    parser.add_argument(
        "--sitemap",
        metavar="URL",
        help="Sitemap URL — skips auto-detection and the sitemap prompt",
    )
    parser.add_argument(
        "--scans",
        metavar="KEYS",
        help="Comma-separated scan keys to run, e.g. imprint_check,link_check,seo",
    )
    parser.add_argument(
        "--imprint-url",
        metavar="URL",
        dest="imprint_url",
        help="Imprint page URL — skips auto-detection and the imprint prompt",
    )
    parser.add_argument(
        "--exclude",
        metavar="PATTERN",
        action="append",
        default=[],
        dest="exclude",
        help="Exclude pages whose path matches PATTERN (glob, e.g. /blog/*). "
        "Can be repeated.",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        dest="output_dir",
        help="Directory to save JSON results. A sub-folder per domain is created automatically.",
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

    if args.sitemap:
        sitemap_url = args.sitemap
        console.print(f"[dim]Sitemap:[/dim] [cyan]{sitemap_url}[/cyan]")
    elif args.non_interactive:
        sitemap_url = suggested
        console.print(f"[dim]Sitemap (auto-detected):[/dim] [cyan]{sitemap_url}[/cyan]")
    else:
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

    console.print(
        f"\n[green]✓[/green] Found [bold]{len(pages)}[/bold] pages in sitemap."
    )

    # ── 3a. Apply exclude filters ─────────────────────────────────────────
    if args.exclude:
        before = len(pages)
        pages = [p for p in pages if not _is_excluded(p, args.exclude)]
        dropped = before - len(pages)
        console.print(
            f"[dim]Excluded {dropped} page(s) via {len(args.exclude)} pattern(s).[/dim]"
        )

    # ── 4. Interactive page selection ─────────────────────────────────────────
    if args.all_pages or args.non_interactive:
        selected_pages = pages
        console.print(f"[dim]Scanning all {len(pages)} pages.[/dim]")
    else:
        selected_pages = select_pages(pages)

    if not selected_pages:
        console.print("\n[yellow]No pages selected. Exiting.[/yellow]")
        sys.exit(0)

    console.print(
        f"\n[green]✓[/green] [bold]{len(selected_pages)}[/bold] page(s) selected for scanning."
    )

    # ── 5. Select scans ───────────────────────────────────────────────────────
    if args.scans:
        selected_scans = [k.strip() for k in args.scans.split(",") if k.strip()]
        console.print(f"[dim]Scans:[/dim] {', '.join(selected_scans)}")
    elif args.non_interactive:
        selected_scans = [
            key for key, _, _, implemented in AVAILABLE_SCANS if implemented
        ]
        console.print(
            f"[dim]Running all implemented scans:[/dim] {', '.join(selected_scans)}"
        )
    else:
        selected_scans = select_scans()

    if not selected_scans:
        console.print("\n[yellow]No scans selected. Exiting.[/yellow]")
        sys.exit(0)

    # ── 5a. Per-scan setup prompts ────────────────────────────────────────────
    scan_config: dict = {}

    if "imprint_check" in selected_scans:
        if args.imprint_url:
            scan_config["imprint_url"] = args.imprint_url
            console.print(f"[dim]Imprint URL:[/dim] [cyan]{args.imprint_url}[/cyan]")
        elif args.non_interactive:
            with console.status("[dim]Auto-detecting imprint page…[/dim]"):
                detected = detect_imprint_url(target)
            imprint_url = detected or f"{target}/impressum"
            label = "(auto-detected)" if detected else "(default)"
            console.print(f"[dim]Imprint URL {label}:[/dim] [cyan]{imprint_url}[/cyan]")
            scan_config["imprint_url"] = imprint_url
        else:
            with console.status("[dim]Auto-detecting imprint page…[/dim]"):
                detected = detect_imprint_url(target)

            if detected:
                console.print(
                    f"\n[dim]Imprint page detected:[/dim] [cyan]{detected}[/cyan]"
                )
            else:
                console.print("\n[yellow]Could not auto-detect imprint page.[/yellow]")

            imprint_url = Prompt.ask(
                "[bold]Imprint URL[/bold]",
                default=detected or f"{target}/impressum",
            )
            scan_config["imprint_url"] = imprint_url

    # ── 6. Run scans ──────────────────────────────────────────────────────────
    scan_results = run_scans(selected_pages, selected_scans, console, scan_config)

    # ── 7. Save JSON results ──────────────────────────────────────────────────
    if args.output_dir:
        domain = urlparse(target).netloc or urlparse(target).path
        domain = domain.replace(":", "_")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        out_dir = Path(args.output_dir) / domain
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{timestamp}.json"

        payload = {
            "scan_date": datetime.now(timezone.utc).isoformat(),
            "target": target,
            "sitemap": sitemap_url,
            "pages_scanned": selected_pages,
            "scans_run": selected_scans,
            "results": scan_results,
        }

        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        console.print(f"\n[green]✓[/green] Results saved → [cyan]{out_file}[/cyan]")

        pdf_file = out_file.with_suffix(".pdf")
        with console.status("[dim]Generating PDF report…[/dim]"):
            generate_pdf(payload, pdf_file)
        console.print(f"[green]✓[/green] PDF report   → [cyan]{pdf_file}[/cyan]")


if __name__ == "__main__":
    main()
