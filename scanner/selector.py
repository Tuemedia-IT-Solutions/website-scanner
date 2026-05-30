"""
scanner/selector.py

Interactive selection helpers:
  - select_pages()  — checkbox list of pages to scan
  - select_scans()  — checkbox list of scans to run
"""

from __future__ import annotations

from InquirerPy import inquirer
from InquirerPy.base.control import Choice
from rich.console import Console

console = Console()

# ── Available scans ───────────────────────────────────────────────────────────
# Each entry: (key, label, description, implemented)
AVAILABLE_SCANS: list[tuple[str, str, str, bool]] = [
    (
        "imprint_check",
        "Imprint Check",
        "Validate the imprint page: required DDG §5 fields, TMG/DDG law reference",
        True,
    ),
    (
        "link_check",
        "Sitemap Link Check",
        "Verify every sitemap URL is reachable (detect 404s, 5xx errors, redirects)",
        True,
    ),
    (
        "legal_links",
        "Legal Links Check",
        "Verify imprint & privacy policy are linked on every page",
        False,
    ),
    (
        "tmg_check",
        "TMG / DDG Check (standalone)",
        "Detect outdated TMG references in the imprint (covered by Imprint Check)",
        False,
    ),
    (
        "seo",
        "SEO Scan",
        "Check image ALTs, heading structure, meta descriptions, and more",
        True,
    ),
    (
        "accessibility",
        "Accessibility Scan",
        "Detect <div>-buttons, missing form labels, and other ARIA issues",
        False,
    ),
]


def select_pages(pages: list[str]) -> list[str]:
    """
    Ask whether to scan all pages or select manually.

    When choosing manually, an interactive checkbox is shown:
      Space   — toggle current item
      a       — select / deselect all
      i       — invert selection
      Enter   — confirm
    """
    console.print(f"\n[bold]Found {len(pages)} page(s)[/bold]\n")

    mode: str = inquirer.select(
        message="Which pages should be scanned?",
        choices=[
            Choice(value="all", name=f"All pages  ({len(pages)} total)"),
            Choice(value="manual", name="Select manually…"),
        ],
        default="all",
    ).execute()

    if mode == "all":
        return pages

    # ── Manual selection ──────────────────────────────────────────────────────
    console.print("\n[dim]Space=toggle  a=select all  A=deselect all  Enter=confirm[/dim]\n")

    choices = [Choice(value=page, name=page, enabled=True) for page in pages]

    selected: list[str] = inquirer.checkbox(
        message="Pages:",
        choices=choices,
        cycle=True,
        keybindings={
            "toggle-all-true": [{"key": "a"}],
            "toggle-all-false": [{"key": "A"}],
        },
        transformer=lambda result: f"{len(result)} page(s) selected",
        validate=lambda result: len(result) > 0 or "Select at least one page.",
        invalid_message="Please select at least one page.",
    ).execute()

    return selected


def select_scans() -> list[str]:
    """
    Present an interactive checkbox list of available scans.
    Returns the list of selected scan keys.
    """
    console.print(
        "\n[bold]Select scans to run[/bold]  "
        "[dim]Space=toggle  a=select all  A=deselect all  Enter=confirm[/dim]\n"
    )

    choices = []
    for key, label, description, implemented in AVAILABLE_SCANS:
        status = "" if implemented else " [dim](coming soon)[/dim]"
        choices.append(
            Choice(
                value=key,
                name=f"{label}{status} — {description}",
                enabled=True,
            )
        )

    selected: list[str] = inquirer.checkbox(
        message="Scans:",
        choices=choices,
        cycle=True,
        keybindings={
            "toggle-all-true": [{"key": "a"}],
            "toggle-all-false": [{"key": "A"}],
        },
        transformer=lambda result: f"{len(result)} scan(s) selected",
        validate=lambda result: len(result) > 0 or "Select at least one scan.",
        invalid_message="Please select at least one scan.",
    ).execute()

    return selected
