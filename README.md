# Website Scanning Tool

**by [Tuemedia IT](https://tuemedia-it.de)**

A command-line tool that crawls a website's sitemap, lets you select the pages you want to audit, and runs a suite of automated checks — covering legal compliance, SEO, and accessibility.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Scan Modules](#scan-modules)
  - [Legal Links Check](#1-legal-links-check--implemented-soon)
  - [TMG / DDG Check](#2-tmg--ddg-check--to-be-developed)
  - [SEO Scan](#3-seo-scan--to-be-developed)
  - [Accessibility Scan](#4-accessibility-scan--to-be-developed)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Implemented

| Feature                           | Description                                                                                              |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **URL normalisation**             | Enter a bare domain (`example.com`) or a full URL — the tool handles both.                               |
| **Sitemap discovery**             | Checks `robots.txt` for a `Sitemap:` directive, falls back to `<domain>/sitemap.xml`.                    |
| **Sitemap suggestion & override** | The detected sitemap URL is shown as a pre-filled prompt; press Enter to accept or type a different URL. |
| **Sitemap index support**         | Follows `<sitemapindex>` files recursively to collect every child sitemap.                               |
| **Interactive page selection**    | Checkbox list with keyboard shortcuts — toggle individual pages, select all, invert, then confirm.       |
| **Interactive scan selection**    | Choose which scan modules to run before the scan starts.                                                 |

### Planned — see [Scan Modules](#scan-modules)

- Legal Links Check
- TMG / DDG Check
- SEO Scan
- Accessibility Scan

---

## Requirements

- Python 3.11+
- pip

Python library dependencies are listed in `requirements.txt`:

```
requests>=2.31.0
beautifulsoup4>=4.12.0
lxml>=5.0.0
rich>=13.7.0
InquirerPy>=0.3.4
```

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Tuemedia-IT-Solutions/website-scanner.git
cd website-scanner

# 2. Create and activate a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate      # Linux / macOS
.venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
# Interactive mode — prompts for URL and sitemap
python main.py

# Pass the domain directly
python main.py example.com

# Pass a full URL
python main.py https://www.example.com

# Skip the page-selection step and scan all discovered pages
python main.py example.com --all-pages
```

### Typical workflow

```
$ python main.py example.com

╭─────────────────────────────╮
│  Website Scanning Tool      │
│  by Tuemedia IT             │
╰─────────────────────────────╯

Target: https://example.com

Sitemap URL [https://example.com/sitemap.xml]:   ← press Enter or type a custom URL

✓ Found 42 pages in sitemap.

Select pages to scan  Space=toggle  a=all  i=invert  Enter=confirm
  ● https://example.com/
  ● https://example.com/about/
  ● https://example.com/contact/
  …

Select scans to run  Space=toggle  a=all  i=invert  Enter=confirm
  ● Legal Links Check (coming soon)
  ● TMG / DDG Check (coming soon)
  ● SEO Scan (coming soon)
  ● Accessibility Scan (coming soon)
```

---

## Project Structure

```
website-scanner/
├── main.py                     # Entry point & main orchestrator
├── requirements.txt
├── README.md
└── scanner/
    ├── crawler.py              # Sitemap discovery, fetching, parsing
    ├── selector.py             # Interactive page & scan selection
    └── scans/
        ├── __init__.py         # Scan orchestrator / dispatcher
        ├── legal.py            # Legal Links Check
        ├── tmg_check.py        # TMG / DDG imprint content check
        ├── seo.py              # SEO Scan
        └── accessibility.py    # Accessibility Scan
```

---

## Scan Modules

### 1. Legal Links Check _(to be developed)_

> **File:** `scanner/scans/legal.py`

Verifies that every page on the site contains visible links to:

- The **imprint** (German: _Impressum_) — required by German law (§ 5 DDG) for commercial websites.
- The **privacy policy** (German: _Datenschutzerklärung_) — required by GDPR Art. 13/14.

Detection uses a combination of URL path heuristics (e.g. `/impressum`, `/datenschutz`) and link-text matching. Pages where one or both links are missing are flagged.

**Output:** per-page table — URL · Imprint linked · Privacy linked · Notes

---

### 2. TMG / DDG Check _(to be developed)_

> **File:** `scanner/scans/tmg_check.py`

The _Telemediengesetz_ (TMG) was the German law governing online services until it was superseded:

- **2021** — TTDSG (_Telekommunikation-Telemedien-Datenschutz-Gesetz_) replaced the data-protection provisions of TMG.
- **2024** — DDG (_Digitale-Dienste-Gesetz_, implementing the EU Digital Services Act) replaced the remaining TMG provisions.

Imprint pages that still cite TMG as the legal basis are outdated. This scan:

1. Locates the imprint page.
2. Extracts visible text.
3. Flags occurrences of _"TMG"_ / _"Telemediengesetz"_ as outdated, and confirms the presence of _"DDG"_ as the current reference.

**Output:** found term · surrounding sentence excerpt · status (outdated / current)

---

### 3. SEO Scan _(to be developed)_

> **File:** `scanner/scans/seo.py`

Checks each page for common on-page SEO issues:

| Check                                     | Severity |
| ----------------------------------------- | -------- |
| `<img>` missing `alt` attribute           | Error    |
| `<img alt="">` (empty, non-decorative)    | Warning  |
| Generic alt text (`"image"`, `"foto"`, …) | Warning  |
| Missing `<h1>`                            | Error    |
| Multiple `<h1>` elements                  | Warning  |
| Skipped heading levels (e.g. h1 → h3)     | Warning  |
| Missing `<meta name="description">`       | Warning  |
| Description outside 50–160 characters     | Warning  |
| Missing or empty `<title>`                | Error    |
| Title outside 10–60 characters            | Warning  |
| Missing `<link rel="canonical">`          | Info     |

**Output:** per-page table — check · severity · finding detail

---

### 4. Accessibility Scan _(to be developed)_

> **File:** `scanner/scans/accessibility.py`

Checks each page for WCAG 2.1 AA violations:

| Check                                                    | WCAG         | Severity |
| -------------------------------------------------------- | ------------ | -------- |
| `<div>`/`<span>` used as button without keyboard support | 2.1.1, 4.1.2 | Error    |
| `<input>` / `<select>` / `<textarea>` without label      | 1.3.1, 4.1.2 | Error    |
| `<button>` without text or `aria-label`                  | 4.1.2        | Error    |
| `<img>` without `alt`                                    | 1.1.1        | Error    |
| `<video>` without captions track                         | 1.2.2        | Warning  |
| Invalid `aria-*` attribute value                         | 4.1.2        | Error    |
| `<html>` without `lang` attribute                        | 3.1.1        | Error    |

> Colour-contrast checking requires CSS rendering and is planned for a later phase.

**Output:** per-page table — WCAG criterion · severity · offending element · detail

---

## Contributing

Pull requests and issues are welcome. Please open an issue first to discuss larger changes.

---

## License

See [LICENSE.md](LICENSE.md).
