"""
scanner/scans/seo/images.py

SEO check: image ALT attributes.

Checks:
  - <img> missing alt attribute entirely          → error
  - <img alt=""> without role="presentation"      → warning
  - <img alt="…"> with a non-descriptive generic  → warning
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ._types import SeoIssue

# Alt values that carry no meaning
_GENERIC_ALTS = re.compile(
    r"^(image|img|foto|bild|picture|photo|graphic|icon|banner|logo|thumbnail)\d*$",
    re.IGNORECASE,
)


def check_images(soup: BeautifulSoup) -> list[SeoIssue]:
    issues: list[SeoIssue] = []

    for img in soup.find_all("img"):
        snippet = _img_snippet(img)

        if not img.has_attr("alt"):
            issues.append(
                SeoIssue(
                    check="Missing ALT attribute",
                    severity="error",
                    detail="Image is missing the alt attribute. Required for accessibility and SEO.",
                    element=snippet,
                )
            )

        elif img["alt"].strip() == "":
            role = img.get("role", "")
            if role not in ("presentation", "none"):
                issues.append(
                    SeoIssue(
                        check="Empty ALT attribute",
                        severity="warning",
                        detail=(
                            'Image has alt="" but is not marked decorative. '
                            'Add role="presentation" to intentionally decorative images.'
                        ),
                        element=snippet,
                    )
                )

        elif _GENERIC_ALTS.match(img["alt"].strip()):
            issues.append(
                SeoIssue(
                    check="Generic ALT text",
                    severity="warning",
                    detail=f'Alt text "{img["alt"]}" is non-descriptive.',
                    element=snippet,
                )
            )

    return issues


def _img_snippet(img) -> str:
    """Return a short, readable representation of an <img> tag."""
    parts = ["<img"]
    for attr in ("src", "alt", "width", "height", "role"):
        if img.has_attr(attr):
            val = img[attr]
            if attr == "src" and len(val) > 60:
                val = val[:57] + "…"
            parts.append(f'{attr}="{val}"')
    return " ".join(parts) + ">"
