# Contributing to Website Scanning Tool

Thanks for your interest in contributing! This document covers the setup, conventions, and workflow expected for all contributions.

## Prerequisites

- Python 3.11 or newer
- pip

## Local setup

```bash
git clone https://github.com/tuemedia/website-scanner.git
cd website-scanner

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

## Running tests

```bash
python -m pytest tests/ -v
```

All new code must be covered by tests. Tests live in `tests/` and mirror the module structure under `scanner/`. Use `unittest.mock.patch` to avoid real network calls — see `tests/test_imprint.py` as a reference.

## Linting & formatting

We use [Ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

```bash
# Check for issues
ruff check .

# Auto-fix safe issues
ruff check --fix .

# Format code
ruff format .
```

The CI pipeline will fail if either check reports errors.

## CI

GitHub Actions runs automatically on every push and pull request:

| Job      | What it does                                 |
| -------- | -------------------------------------------- |
| **Test** | Runs `pytest` on Python 3.11, 3.12, and 3.13 |
| **Lint** | Runs `ruff check` and `ruff format --check`  |

All jobs must be green before a PR can be merged.

## Adding a new scan module

1. Create `scanner/scans/<name>.py` with a `run(pages, console, config)` function.
2. Register it in `scanner/scans/__init__.py` (`_REGISTRY`).
3. Add it to `AVAILABLE_SCANS` in `scanner/selector.py` (set `implemented=True` when ready).
4. Write tests in `tests/test_<name>.py`.

## Pull request guidelines

- Keep PRs focused — one feature or fix per PR.
- Write a clear description of what changed and why.
- Ensure `pytest` and `ruff` pass locally before opening a PR.
- Reference any relevant issue numbers.
