"""
scanner/scans/imprint.py
========================
Imprint Validation Scan

Detects the imprint page and checks it for the fields required by German law
(§ 5 DDG — Digitale-Dienste-Gesetz, formerly TMG).

Required fields (§ 5 DDG):
  - Name / company name
  - Physical address (street, postal code, city)
  - E-mail address
  - Rapid electronic or phone contact means
  - For GmbH/AG/UG: Handelsregisternummer + Registergericht
  - For regulated professions: supervisory authority

Additional check:
  - Legal reference should be DDG (current), not TMG (outdated since 2024).
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


# ── Required-field checks ─────────────────────────────────────────────────────
# Each entry:  (field_key, label, compiled_regex, severity, hint)
_FIELD_CHECKS: list[tuple[str, str, re.Pattern, str, str]] = [
    (
        "name",
        "Name / company",
        re.compile(
            r"(GmbH|AG|UG|OHG|KG|e\.K\.|GbR|e\.V\.|Inc\.|Ltd\.)"  # legal form
            r"|(?:Inhaber|Geschäftsführer|Vertreten durch|Einzelunternehmen)",
            re.IGNORECASE,
        ),
        "warning",
        "Could not detect a company/legal form or owner designation. "
        "The name of the provider must be stated clearly.",
    ),
    (
        "street",
        "Street address",
        re.compile(
            r"[A-ZÄÖÜ][a-zäöüß]+"
            r"(?:straße|strasse|gasse|weg|allee|ring|platz|damm|berg|park|chaussee|steig|pfad)"
            r"\s+\d+",
            re.IGNORECASE,
        ),
        "error",
        "No street address detected. A physical postal address is required by § 5 DDG.",
    ),
    (
        "postal_code",
        "Postal code",
        re.compile(r"\b\d{5}\b"),
        "error",
        "No German 5-digit postal code found.",
    ),
    (
        "email",
        "E-mail address",
        re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"),
        "error",
        "No e-mail address found. Required by § 5 Abs. 1 Nr. 2 DDG.",
    ),
    (
        "phone",
        "Phone number",
        re.compile(
            r"(?:Tel\.?|Telefon|Fon|Phone|Fax)[\s:]*[\+\d]"
            r"|(?:\+49|00\s?49|0\d{2,5})[\s\-/()]*\d{3,}[\d\s\-/()]*",
            re.IGNORECASE,
        ),
        "warning",
        "No phone number detected. A rapid contact means (phone or equivalent) "
        "is required by § 5 Abs. 1 Nr. 2 DDG.",
    ),
]

# ── Legal reference checks ────────────────────────────────────────────────────
_LAW_PATTERNS: list[tuple[str, re.Pattern, str, str]] = [
    (
        "tmg",
        re.compile(r"\bTMG\b|\bTelemediengesetz\b", re.IGNORECASE),
        "warning",
        "Reference to TMG found. TMG was replaced by DDG in 2024 — please update.",
    ),
    (
        "ttdsg",
        re.compile(r"\bTTDSG\b", re.IGNORECASE),
        "info",
        "Reference to TTDSG found. TTDSG governs cookie consent; "
        "the imprint obligation now falls under DDG.",
    ),
    (
        "ddg",
        re.compile(r"\bDDG\b|\bDigitale-?Dienste-?Gesetz\b", re.IGNORECASE),
        "ok",
        "DDG reference found — up to date.",
    ),
]

# ── Optional / company-type checks ───────────────────────────────────────────
_COMPANY_CHECKS: list[tuple[re.Pattern, re.Pattern, str, str]] = [
    # (trigger pattern, required pattern, label, hint)
    (
        re.compile(r"\b(GmbH|AG|UG)\b"),
        re.compile(r"\bHR[AB]\b\s*\d+|\bHandelsregister\b", re.IGNORECASE),
        "Handelsregister number",
        "GmbH/AG/UG detected but no Handelsregisternummer (HRB/HRA) found. "
        "Required by § 5 Abs. 1 Nr. 3 DDG.",
    ),
]


# How many extra characters to grab to the right of the match, per field.
# All other fields show only match.group(0).
_FIELD_CONTEXT_RIGHT: dict[str, int] = {
    "name": 40,  # show the actual name that follows "Inhaber:" / "GmbH" etc.
    "phone": 20,  # capture digits that follow the label (e.g. "Telefon: ")
}


# ── Result types ──────────────────────────────────────────────────────────────


@dataclass
class ImprintIssue:
    severity: str  # "error" | "warning" | "info" | "ok"
    field: str
    detail: str
    matched: str | None = None  # actual text found by the regex (for ok checks)


@dataclass
class ImprintResult:
    imprint_url: str
    issues: list[ImprintIssue] = field(default_factory=list)
    fetch_error: str | None = None


# ── Public API ────────────────────────────────────────────────────────────────


def run(pages: list[str], console: Console, config: dict) -> ImprintResult:
    """
    Validate the imprint page.

    *pages* is ignored — the imprint URL comes from ``config["imprint_url"]``.
    """
    imprint_url: str = config["imprint_url"]

    console.print(
        Panel.fit(
            f"[bold]Imprint Check[/bold]\n[dim]{imprint_url}[/dim]",
            border_style="cyan",
        )
    )

    with console.status("[dim]Fetching imprint page…[/dim]"):
        result = _validate(imprint_url)

    _render(result, console)
    return result


# ── Internals ─────────────────────────────────────────────────────────────────


def _validate(imprint_url: str) -> ImprintResult:
    result = ImprintResult(imprint_url=imprint_url)

    try:
        resp = requests.get(imprint_url, timeout=_TIMEOUT, headers=_HEADERS)
        resp.raise_for_status()
    except requests.RequestException as exc:
        result.fetch_error = str(exc)
        return result

    soup = BeautifulSoup(resp.content, "lxml")

    # Strip navigation, header, footer noise — focus on the main content area.
    for tag in soup(["nav", "header", "footer", "script", "style"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)

    # ── Required field checks ─────────────────────────────────────────────────
    for key, label, pattern, severity, hint in _FIELD_CHECKS:
        m = pattern.search(text)
        if m:
            matched = _snippet(text, m, context_right=_FIELD_CONTEXT_RIGHT.get(key, 0))
            result.issues.append(ImprintIssue("ok", label, f"{label} detected.", matched=matched))
        else:
            result.issues.append(ImprintIssue(severity, label, hint))

    # ── Legal reference checks ────────────────────────────────────────────────
    found_law_refs: list[str] = []
    for key, pattern, severity, hint in _LAW_PATTERNS:
        m = pattern.search(text)
        if m:
            found_law_refs.append(key)
            result.issues.append(
                ImprintIssue(
                    severity,
                    f"Law reference: {key.upper()}",
                    hint,
                    matched=m.group(0).strip(),
                )
            )

    if not found_law_refs:
        result.issues.append(
            ImprintIssue(
                "info",
                "Law reference",
                "No DDG/TMG/TTDSG reference found. Consider adding a reference to § 5 DDG.",
            )
        )

    # ── Company-type checks ───────────────────────────────────────────────────
    for trigger, required, label, hint in _COMPANY_CHECKS:
        if trigger.search(text) and not required.search(text):
            result.issues.append(ImprintIssue("error", label, hint))

    return result


def _snippet(text: str, match: re.Match, context_right: int = 0) -> str:
    """Return the matched text, optionally extended to the right for context."""
    end = min(len(text), match.end() + context_right)
    raw = text[match.start() : end].strip()
    return re.sub(r"\s+", " ", raw)


def _render(result: ImprintResult, console: Console) -> None:
    if result.fetch_error:
        console.print(f"[red]Could not fetch imprint page:[/red] {result.fetch_error}")
        return

    # Severity order for sorting: errors first, then warnings, then info, then ok
    _order = {"error": 0, "warning": 1, "info": 2, "ok": 3}
    issues = sorted(result.issues, key=lambda i: _order.get(i.severity, 9))

    table = Table(
        box=box.SIMPLE_HEAD,
        show_header=True,
        header_style="bold",
        padding=(0, 1),
    )
    table.add_column("Severity", width=9)
    table.add_column("Field", min_width=24)
    table.add_column("Detail")

    _icons = {
        "error": "[bold red]✗ error[/bold red]",
        "warning": "[bold yellow]⚠ warn[/bold yellow]",
        "info": "[dim]ℹ info[/dim]",
        "ok": "[green]✓ ok[/green]",
    }

    for issue in issues:
        detail = issue.detail
        if issue.matched:
            detail = f"{detail}\n[dim]→ {issue.matched}[/dim]"
        table.add_row(
            _icons.get(issue.severity, issue.severity),
            issue.field,
            detail,
        )

    console.print(table)

    errors = sum(1 for i in result.issues if i.severity == "error")
    warnings = sum(1 for i in result.issues if i.severity == "warning")
    oks = sum(1 for i in result.issues if i.severity == "ok")

    summary_color = "red" if errors else "yellow" if warnings else "green"
    console.print(
        f"[{summary_color}]Imprint: {oks} ok · {errors} error(s) · {warnings} warning(s)[/{summary_color}]\n"
        "[dim]Note: this is a heuristic check, not legal advice.[/dim]\n"
    )
