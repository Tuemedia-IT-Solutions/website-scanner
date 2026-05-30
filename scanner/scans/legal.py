"""
scanner/scans/legal.py
======================
Legal Links Check — TO BE DEVELOPED

Planned behaviour
-----------------
For each scanned page, verify that:

1. A link to the **imprint** (German: Impressum) is present.
   Common paths: /impressum, /imprint, /legal/impressum
2. A link to the **privacy policy** (German: Datenschutz) is present.
   Common paths: /datenschutz, /datenschutzerklaerung, /privacy-policy

The scan will:
- Fetch each page and extract all <a href="…"> elements.
- Check whether any href or link text matches known imprint/privacy patterns.
- Report pages where one or both links are missing.

Expected output
---------------
A per-page table showing:
  URL | Imprint linked | Privacy linked | Notes
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console


@dataclass
class LegalLinksResult:
    url: str
    has_imprint_link: bool = False
    has_privacy_link: bool = False
    imprint_href: str | None = None
    privacy_href: str | None = None
    errors: list[str] = field(default_factory=list)


def run(pages: list[str], console: Console, config: dict) -> list[LegalLinksResult]:
    """
    Scan each page for imprint and privacy policy links.

    TO BE DEVELOPED.
    """
    raise NotImplementedError
