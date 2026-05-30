"""
scanner/scans/accessibility.py
===============================
Accessibility Scan — TO BE DEVELOPED

Planned checks
--------------
For each selected page:

1. **Keyboard-accessible interactive elements**
   - <div> or <span> with click handlers (onclick / role="button") but no
     keyboard event handler or tabindex → error
   - <a> without href and without role → warning

2. **Form labels**
   - <input>, <select>, <textarea> without an associated <label>
     (via for/id pairing or aria-label / aria-labelledby) → error
   - <button> with no text content and no aria-label → error

3. **Images & media**
   - <img> without alt (duplicated from SEO scan for a11y context) → error
   - <video> without captions track → warning

4. **ARIA attributes**
   - Invalid aria-* attribute values → error
   - role= values that are not valid WAI-ARIA roles → error
   - aria-required / aria-invalid used without corresponding role → warning

5. **Colour contrast (future)**
   - Requires rendered CSS — placeholder for Phase 2.

6. **Language attribute**
   - <html> without lang attribute → error

Expected output
---------------
Per-page table with WCAG criterion reference, severity, element, and detail.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rich.console import Console


@dataclass
class A11yIssue:
    check: str
    wcag_ref: str  # e.g. "1.1.1", "4.1.2"
    severity: str  # "error" | "warning" | "info"
    element: str  # HTML snippet of offending element
    detail: str


@dataclass
class AccessibilityResult:
    url: str
    issues: list[A11yIssue] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def run(pages: list[str], console: Console, config: dict) -> list[AccessibilityResult]:
    """
    Run accessibility checks on each page.

    TO BE DEVELOPED.
    """
    raise NotImplementedError
