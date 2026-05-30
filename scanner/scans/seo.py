"""
scanner/scans/seo.py
====================
SEO Scan — TO BE DEVELOPED

Planned checks
--------------
For each selected page:

1. **Image ALT attributes**
   - <img> without alt attribute → error
   - <img alt=""> (empty alt)    → warning (decorative images should use role="presentation")
   - <img alt="image" / alt="foto"> (generic alt) → warning

2. **Heading structure**
   - Missing <h1>                → error
   - More than one <h1>          → warning
   - Heading levels skipped (e.g. h1 → h3 with no h2) → warning

3. **Meta tags**
   - Missing <meta name="description"> → warning
   - Description too short (<50 chars) or too long (>160 chars) → warning
   - Missing <title> tag         → error
   - Title too short (<10 chars) or too long (>60 chars) → warning

4. **Canonical URL**
   - Missing <link rel="canonical"> → info

5. **Structured data (future)**
   - Detect JSON-LD / microdata presence → info

Expected output
---------------
Per-page table with check name, severity, and finding detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console


@dataclass
class SeoIssue:
    check: str
    severity: str  # "error" | "warning" | "info"
    detail: str


@dataclass
class SeoResult:
    url: str
    issues: list[SeoIssue] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run(pages: list[str], console: Console, config: dict) -> list[SeoResult]:
    """
    Run SEO checks on each page.

    TO BE DEVELOPED.
    """
    raise NotImplementedError
