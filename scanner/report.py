"""
scanner/report.py

PDF report generator.
Converts a scan-result payload dict (the same format saved as JSON) into a
formatted, multi-section PDF using fpdf2.

Public API:
    generate(payload: dict, out_path: Path) -> None
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fpdf import FPDF
from fpdf.enums import XPos, YPos

# ── Font paths ────────────────────────────────────────────────────────────────
# DejaVu Sans is available on most Linux systems and covers Latin + German chars.
_FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")
_FONT_REG = _FONT_DIR / "DejaVuSans.ttf"
_FONT_BOLD = _FONT_DIR / "DejaVuSans-Bold.ttf"
_USE_DEJAVU = _FONT_REG.exists() and _FONT_BOLD.exists()
_FONT_NAME = "DejaVu" if _USE_DEJAVU else "Helvetica"

# ── Colour palette ────────────────────────────────────────────────────────────
_WHITE = (255, 255, 255)
_BLACK = (33, 37, 41)
_DARK = (52, 58, 64)  # section / table headers
_MEDIUM = (108, 117, 125)  # muted text, secondary info
_LIGHT = (248, 249, 250)  # alternating row fill
_BORDER = (222, 226, 230)

_GREEN = (40, 167, 69)
_ORANGE = (255, 140, 0)
_RED = (220, 53, 69)
_BLUE = (0, 123, 255)

_SEV_COLOUR: dict[str, tuple[int, int, int]] = {
    "ok": _GREEN,
    "warning": _ORANGE,
    "error": _RED,
    "info": _BLUE,
}
_SEV_LABEL: dict[str, str] = {
    "ok": "OK",
    "warning": "WARN",
    "error": "ERROR",
    "info": "INFO",
}

# Shorthand kwargs to move the cursor to the next line after a cell()
_NL = {"new_x": XPos.LMARGIN, "new_y": YPos.NEXT}


# ── PDF class ─────────────────────────────────────────────────────────────────


class _ScanPDF(FPDF):
    """FPDF subclass with layout helpers for the scan report."""

    def __init__(self, target: str, scan_date: str) -> None:
        super().__init__("P", "mm", "A4")
        self._target = target
        self._scan_date = scan_date[:10]  # YYYY-MM-DD only
        self.set_margins(20, 20, 20)
        self.set_auto_page_break(auto=True, margin=18)

        if _USE_DEJAVU:
            self.add_font(_FONT_NAME, style="", fname=str(_FONT_REG))
            self.add_font(_FONT_NAME, style="B", fname=str(_FONT_BOLD))
            # fpdf2 has no separate italic for DejaVu here; use regular as fallback
            self.add_font(_FONT_NAME, style="I", fname=str(_FONT_REG))

    @property
    def _pw(self) -> float:
        """Printable / usable page width in mm."""
        return self.w - self.l_margin - self.r_margin

    # ── fpdf2 page hooks ──────────────────────────────────────────────────────

    def header(self) -> None:
        if self.page_no() == 1:
            return
        self.set_font(_FONT_NAME, "B", 7.5)
        self.set_text_color(*_MEDIUM)
        self.cell(
            self._pw * 0.65, 5, f"Website Scan Report -- {self._target}", align="L"
        )
        self.cell(
            self._pw * 0.35,
            5,
            f"{self._scan_date}   |   Page {self.page_no()}",
            align="R",
            **_NL,
        )
        self.set_draw_color(*_BORDER)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)
        self.set_text_color(*_BLACK)

    # ── Generic layout helpers ────────────────────────────────────────────────

    def section_title(self, text: str) -> None:
        self.ln(3)
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        self.set_font(_FONT_NAME, "B", 11)
        self.cell(self._pw, 8, f"  {text}", fill=True, **_NL)
        self.set_text_color(*_BLACK)
        self.ln(2)

    def summary_line(self, text: str, colour: tuple[int, int, int] = _DARK) -> None:
        self.set_font(_FONT_NAME, "B", 9)
        self.set_text_color(*colour)
        self.cell(self._pw, 5, text, **_NL)
        self.set_text_color(*_BLACK)
        self.ln(2)

    def kv_line(self, key: str, value: str, key_w: float = 38) -> None:
        self.set_font(_FONT_NAME, "B", 9)
        self.cell(key_w, 5.5, key)
        self.set_font(_FONT_NAME, "", 9)
        self.multi_cell(self._pw - key_w, 5.5, value)

    def table_header(self, labels: list[str], widths: list[float]) -> None:
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        self.set_font(_FONT_NAME, "B", 8)
        for lbl, w in zip(labels, widths):
            self.cell(w, 6, f" {lbl}", fill=True, border=1)
        self.ln()
        self.set_text_color(*_BLACK)

    def plain_cell(
        self,
        text: str,
        w: float,
        fill_colour: tuple = _WHITE,
        *,
        bold: bool = False,
        border: int = 1,
        align: str = "L",
        h: float = 6,
    ) -> None:
        self.set_fill_color(*fill_colour)
        self.set_font(_FONT_NAME, "B" if bold else "", 8)
        self.cell(w, h, f" {text}", fill=True, border=border, align=align)

    def sev_cell(
        self, severity: str, w: float, *, border: int = 1, h: float = 6
    ) -> None:
        colour = _SEV_COLOUR.get(severity, _BLUE)
        label = _SEV_LABEL.get(severity, severity.upper())
        self.set_fill_color(*colour)
        self.set_text_color(*_WHITE)
        self.set_font(_FONT_NAME, "B", 7.5)
        self.cell(w, h, label, fill=True, border=border, align="C")
        self.set_text_color(*_BLACK)

    def issue_block(
        self,
        severity: str,
        label: str,
        detail: str,
        matched: str | None = None,
        *,
        indent: float = 0,
    ) -> None:
        """
        Render one issue as a two-line block:
          [BADGE]  Label (bold)
                   Detail text (wrapped, muted)
                   Found: matched  (italic, if present)
        """
        badge_w = 18
        text_w = self._pw - badge_w - indent - 4
        x0 = self.l_margin + indent

        # Badge + label
        self.set_xy(x0, self.get_y())
        self.sev_cell(severity, badge_w, border=0, h=5.5)
        self.set_font(_FONT_NAME, "B", 9)
        self.cell(text_w, 5.5, f"  {label}", **_NL)

        # Detail (wrapped)
        if detail:
            self.set_x(x0 + badge_w + 2)
            self.set_font(_FONT_NAME, "", 8.5)
            self.set_text_color(*_MEDIUM)
            self.multi_cell(text_w - 2, 4.5, detail)
            self.set_text_color(*_BLACK)

        # Matched excerpt
        if matched:
            self.set_x(x0 + badge_w + 2)
            self.set_font(_FONT_NAME, "I", 8)
            self.set_text_color(130, 130, 130)
            self.multi_cell(text_w - 2, 4.5, f"Found: {matched}")
            self.set_text_color(*_BLACK)

        self.ln(1)


# ── Cover page ────────────────────────────────────────────────────────────────


def _cover(pdf: _ScanPDF, payload: dict) -> None:
    results = payload.get("results", {})
    pages = payload.get("pages_scanned", [])
    scans = payload.get("scans_run", [])

    # ── Title bar ─────────────────────────────────────────────────────────────
    pdf.ln(6)
    pdf.set_fill_color(*_DARK)
    pdf.set_text_color(*_WHITE)
    pdf.set_font(_FONT_NAME, "B", 22)
    pdf.cell(pdf._pw, 14, "Website Scan Report", fill=True, align="C", **_NL)
    pdf.set_text_color(*_BLACK)
    pdf.ln(6)

    # ── Metadata ──────────────────────────────────────────────────────────────
    pdf.kv_line("Target:", payload.get("target", "—"))
    pdf.kv_line("Scan date:", payload.get("scan_date", "—")[:19].replace("T", "  "))
    pdf.kv_line("Sitemap:", payload.get("sitemap", "—"))
    pdf.kv_line("Pages scanned:", str(len(pages)))
    pdf.kv_line("Scans run:", ", ".join(scans))
    pdf.ln(4)

    pdf.set_draw_color(*_BORDER)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)

    # ── Summary stats ─────────────────────────────────────────────────────────
    pdf.set_font(_FONT_NAME, "B", 9)
    pdf.set_text_color(*_MEDIUM)
    pdf.cell(pdf._pw, 5, "Summary", **_NL)
    pdf.set_text_color(*_BLACK)
    pdf.ln(2)

    imp = results.get("imprint_check", {})
    links = results.get("link_check", [])
    legal = results.get("legal_links", [])
    seo_pgs = results.get("seo", [])

    imp_errors = sum(1 for i in imp.get("issues", []) if i.get("severity") == "error")
    imp_warns = sum(1 for i in imp.get("issues", []) if i.get("severity") == "warning")

    lnk_errors = sum(
        1 for r in links if (r.get("status") or 0) >= 400 or r.get("error")
    )
    lnk_redirs = sum(1 for r in links if 300 <= (r.get("status") or 0) < 400)

    leg_issues = sum(
        1
        for r in legal
        if not r.get("errors")
        and (not r.get("has_imprint_link") or not r.get("has_privacy_link"))
    )

    seo_errors = sum(
        sum(1 for i in p.get("issues", []) if i.get("severity") == "error")
        for p in seo_pgs
    )
    seo_warns = sum(
        sum(1 for i in p.get("issues", []) if i.get("severity") == "warning")
        for p in seo_pgs
    )

    def _stat_pair(n: int, label: str, colour: tuple) -> None:
        pdf.set_fill_color(*colour)
        pdf.set_text_color(*_WHITE)
        pdf.set_font(_FONT_NAME, "B", 15)
        pdf.cell(22, 13, str(n), fill=True, align="C")
        pdf.set_fill_color(*_LIGHT)
        pdf.set_text_color(*_BLACK)
        pdf.set_font(_FONT_NAME, "", 8)
        pdf.cell(40, 13, f"  {label}", fill=True)
        pdf.cell(4, 13, "")  # spacer

    _stat_pair(imp_errors, "Imprint errors", _RED if imp_errors else _GREEN)
    _stat_pair(imp_warns, "Imprint warnings", _ORANGE if imp_warns else _GREEN)
    pdf.ln()
    pdf.ln(2)
    _stat_pair(lnk_errors, "Broken links", _RED if lnk_errors else _GREEN)
    _stat_pair(lnk_redirs, "Redirects", _ORANGE if lnk_redirs else _GREEN)
    pdf.ln()
    pdf.ln(2)
    _stat_pair(leg_issues, "Legal link issues", _RED if leg_issues else _GREEN)
    pdf.ln()
    pdf.ln(2)
    _stat_pair(seo_errors, "SEO errors", _RED if seo_errors else _GREEN)
    _stat_pair(seo_warns, "SEO warnings", _ORANGE if seo_warns else _GREEN)
    pdf.ln()
    pdf.ln(4)

    # ── Scanned pages list ────────────────────────────────────────────────────
    pdf.set_draw_color(*_BORDER)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)
    pdf.set_font(_FONT_NAME, "B", 9)
    pdf.set_text_color(*_MEDIUM)
    pdf.cell(pdf._pw, 5, f"Scanned Pages  ({len(pages)} total)", **_NL)
    pdf.set_text_color(*_BLACK)
    pdf.ln(1)

    for idx, url in enumerate(pages):
        fill = _LIGHT if idx % 2 else _WHITE
        pdf.set_fill_color(*fill)
        pdf.set_font(_FONT_NAME, "", 7.5)
        pdf.set_text_color(*_MEDIUM)
        pdf.cell(8, 5, str(idx + 1), fill=True)
        pdf.set_text_color(*_BLACK)
        pdf.cell(pdf._pw - 8, 5, url, fill=True, **_NL)


# ── Imprint section ───────────────────────────────────────────────────────────


def _imprint_section(pdf: _ScanPDF, result: dict) -> None:
    pdf.section_title("Imprint Check")

    url = result.get("imprint_url", "—")
    pdf.set_font(_FONT_NAME, "", 8.5)
    pdf.set_text_color(*_MEDIUM)
    pdf.cell(pdf._pw, 5, url, **_NL)
    pdf.set_text_color(*_BLACK)
    pdf.ln(2)

    if result.get("fetch_error"):
        pdf.issue_block("error", "Fetch error", result["fetch_error"])
        return

    issues = result.get("issues", [])
    errors = sum(1 for i in issues if i.get("severity") == "error")
    warns = sum(1 for i in issues if i.get("severity") == "warning")
    ok_cnt = sum(1 for i in issues if i.get("severity") == "ok")

    colour = _RED if errors else (_ORANGE if warns else _GREEN)
    pdf.summary_line(f"{ok_cnt} ok   {errors} error(s)   {warns} warning(s)", colour)

    for issue in issues:
        pdf.issue_block(
            issue.get("severity", "info"),
            issue.get("field", ""),
            issue.get("detail", ""),
            matched=issue.get("matched"),
        )


# ── Link check section ────────────────────────────────────────────────────────


def _link_section(pdf: _ScanPDF, results: list) -> None:
    pdf.section_title("Link Check")

    errors = sum(1 for r in results if (r.get("status") or 0) >= 400 or r.get("error"))
    redirs = sum(1 for r in results if 300 <= (r.get("status") or 0) < 400)
    ok_cnt = sum(1 for r in results if 200 <= (r.get("status") or 0) < 300)

    colour = _RED if errors else (_ORANGE if redirs else _GREEN)
    pdf.summary_line(f"{ok_cnt} ok   {errors} error(s)   {redirs} redirect(s)", colour)

    widths = [16, 20, 134]
    pdf.table_header(["Status", "Result", "URL"], widths)

    for idx, r in enumerate(results):
        status = str(r.get("status") or "—")
        url = r.get("url", "")
        error = r.get("error") or ""

        if r.get("error") or (r.get("status") or 0) >= 400:
            sev = "error"
        elif (r.get("status") or 0) >= 300:
            sev = "warning"
        else:
            sev = "ok"

        fill = _LIGHT if idx % 2 else _WHITE
        pdf.plain_cell(status, widths[0], fill_colour=fill, align="R")
        pdf.sev_cell(sev, widths[1])
        pdf.plain_cell(error or url, widths[2], fill_colour=fill)
        pdf.ln()

        if r.get("final_url"):
            pdf.plain_cell("", widths[0] + widths[1], fill_colour=fill, border=1)
            pdf.plain_cell(f"-> {r['final_url']}", widths[2], fill_colour=fill)
            pdf.ln()


# ── Legal links section ───────────────────────────────────────────────────────


def _legal_section(pdf: _ScanPDF, results: list) -> None:
    pdf.section_title("Legal Links Check")

    fetch_errors = sum(1 for r in results if r.get("errors"))
    missing = sum(
        1
        for r in results
        if not r.get("errors")
        and (not r.get("has_imprint_link") or not r.get("has_privacy_link"))
    )
    ok_cnt = len(results) - fetch_errors - missing

    colour = _RED if (missing or fetch_errors) else _GREEN
    pdf.summary_line(
        f"{ok_cnt} ok   {missing} missing link(s)   {fetch_errors} fetch error(s)",
        colour,
    )

    w_url = 86
    w_col = (pdf._pw - w_url) / 3
    widths = [w_url, w_col, w_col, w_col]
    pdf.table_header(["URL", "Imprint", "Privacy", "AGB"], widths)

    def _link_cell(w: float, has_it: bool, href: str | None, row_fill: tuple) -> None:
        if has_it:
            lbl = (href or "").replace("https://", "").replace("http://", "")
            lbl = lbl[:18] or "OK"
            pdf.set_fill_color(*_GREEN)
            pdf.set_text_color(*_WHITE)
            pdf.set_font(_FONT_NAME, "B", 7.5)
            pdf.cell(w, 6, f" {lbl}", fill=True, border=1)
            pdf.set_text_color(*_BLACK)
        else:
            pdf.set_fill_color(*row_fill)
            pdf.set_text_color(*_MEDIUM)
            pdf.set_font(_FONT_NAME, "", 7.5)
            pdf.cell(w, 6, " --", fill=True, border=1)
            pdf.set_text_color(*_BLACK)

    for idx, r in enumerate(results):
        url = r.get("url", "").replace("https://", "").replace("http://", "")
        if len(url) > 44:
            url = "..." + url[-41:]

        fill = _LIGHT if idx % 2 else _WHITE

        if r.get("errors"):
            pdf.set_fill_color(*fill)
            pdf.set_font(_FONT_NAME, "", 8)
            pdf.cell(w_url, 6, f" {url}", fill=True, border=1)
            err_msg = r["errors"][0][:38]
            pdf.set_fill_color(*_RED)
            pdf.set_text_color(*_WHITE)
            pdf.set_font(_FONT_NAME, "", 7.5)
            pdf.cell(w_col * 3, 6, f" {err_msg}", fill=True, border=1)
            pdf.set_text_color(*_BLACK)
        else:
            pdf.plain_cell(url, w_url, fill_colour=fill)
            _link_cell(
                w_col, r.get("has_imprint_link", False), r.get("imprint_href"), fill
            )
            _link_cell(
                w_col, r.get("has_privacy_link", False), r.get("privacy_href"), fill
            )
            _link_cell(w_col, r.get("has_agb_link", False), r.get("agb_href"), fill)
        pdf.ln()


# ── SEO section ───────────────────────────────────────────────────────────────


def _seo_section(pdf: _ScanPDF, pages: list) -> None:
    pdf.section_title("SEO Analysis")

    seo_errors = sum(
        sum(1 for i in p.get("issues", []) if i.get("severity") == "error")
        for p in pages
    )
    seo_warns = sum(
        sum(1 for i in p.get("issues", []) if i.get("severity") == "warning")
        for p in pages
    )
    clean_pages = sum(
        1 for p in pages if not p.get("issues") and not p.get("fetch_error")
    )

    colour = _RED if seo_errors else (_ORANGE if seo_warns else _GREEN)
    pdf.summary_line(
        f"{clean_pages} clean   {seo_errors} error(s)   {seo_warns} warning(s)"
        f"   across {len(pages)} page(s)",
        colour,
    )

    for page in pages:
        url = page.get("url", "")
        issues = page.get("issues", [])
        fetch_error = page.get("fetch_error")

        p_errors = sum(1 for i in issues if i.get("severity") == "error")
        p_warns = sum(1 for i in issues if i.get("severity") == "warning")

        if fetch_error or p_errors:
            bar_colour = _RED
        elif p_warns:
            bar_colour = _ORANGE
        else:
            bar_colour = _GREEN

        # Page URL bar
        pdf.set_fill_color(*bar_colour)
        pdf.set_text_color(*_WHITE)
        pdf.set_font(_FONT_NAME, "B", 8.5)
        pdf.cell(pdf._pw, 6, f"  {url}", fill=True, **_NL)
        pdf.set_text_color(*_BLACK)

        if fetch_error:
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font(_FONT_NAME, "", 8)
            pdf.set_text_color(*_RED)
            pdf.multi_cell(pdf._pw - 4, 4.5, f"Fetch error: {fetch_error}")
            pdf.set_text_color(*_BLACK)
        elif not issues:
            pdf.set_x(pdf.l_margin + 4)
            pdf.set_font(_FONT_NAME, "I", 8)
            pdf.set_text_color(*_GREEN)
            pdf.cell(pdf._pw - 4, 5, "No issues found.", **_NL)
            pdf.set_text_color(*_BLACK)
        else:
            for issue in issues:
                sev = issue.get("severity", "info")
                check = issue.get("check", "")
                detail = issue.get("detail", "")
                element = issue.get("element")
                full_detail = detail + (f"\n[{element}]" if element else "")
                pdf.issue_block(sev, check, full_detail, indent=4)

        pdf.ln(2)


# ── Public API ────────────────────────────────────────────────────────────────


def generate(payload: dict[str, Any], out_path: Path) -> None:
    """
    Generate a PDF report from a scan payload dict and write it to *out_path*.

    *payload* is the same dict that gets saved as JSON — keys:
        target, scan_date, sitemap, pages_scanned, scans_run, results
    """
    target = payload.get("target", "—")
    scan_date = payload.get("scan_date", "—")

    pdf = _ScanPDF(target, scan_date)

    pdf.add_page()
    _cover(pdf, payload)

    results = payload.get("results", {})

    if "imprint_check" in results:
        pdf.add_page()
        _imprint_section(pdf, results["imprint_check"])

    if "link_check" in results:
        _link_section(pdf, results["link_check"])

    if "legal_links" in results:
        pdf.add_page()
        _legal_section(pdf, results["legal_links"])

    if "seo" in results:
        pdf.add_page()
        _seo_section(pdf, results["seo"])

    pdf.output(str(out_path))
