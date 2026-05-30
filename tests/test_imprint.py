"""
tests/test_imprint.py
=====================
Tests for scanner/scans/imprint.py

Each test calls the internal _validate() function directly (no network),
by patching requests.get so we can feed arbitrary HTML page content.

Coverage:
  - All required fields present → all ok
  - Each individual required field missing → correct severity + field name
  - Law references: DDG (ok), TMG (warning), TTDSG (info), none (info)
  - Company-type check: GmbH without Handelsregister → error
  - Company-type check: GmbH with Handelsregister → no error
  - HTTP fetch failure → fetch_error set, no issues
  - Imprint content with street suffix variants
  - Phone detected via label prefix ("Tel.:") and via bare number (+49…)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import requests

from scanner.scans.imprint import ImprintResult, _validate

# ── HTML helpers ──────────────────────────────────────────────────────────────

_BASE = "https://example.com/impressum"

# A minimal but fully valid imprint (sole trader, no GmbH).
_VALID_IMPRINT = """
<html><body>
<h1>Impressum</h1>
<p>Angaben gemäß § 5 DDG</p>
<p>Inhaber: Max Mustermann</p>
<p>Musterstraße 12</p>
<p>12345 Musterstadt</p>
<p>Deutschland</p>
<p>Tel.: +49 30 123456</p>
<p>E-Mail: max@example.com</p>
</body></html>
"""

# GmbH imprint with Handelsregister entry.
_VALID_GMBH_IMPRINT = """
<html><body>
<h1>Impressum</h1>
<p>Angaben gemäß § 5 DDG</p>
<p>Muster GmbH</p>
<p>Musterstraße 12, 12345 Musterstadt</p>
<p>Handelsregister: HRB 123456, Amtsgericht Musterstadt</p>
<p>Geschäftsführer: Max Mustermann</p>
<p>Tel.: +49 30 123456</p>
<p>E-Mail: info@muster-gmbh.de</p>
</body></html>
"""


def _mock_response(html: str, status: int = 200) -> MagicMock:
    """Return a mock requests.Response for the given HTML."""
    mock = MagicMock()
    mock.status_code = status
    mock.content = html.encode()
    if status >= 400:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError(f"HTTP {status}")
    else:
        mock.raise_for_status = MagicMock()  # no-op
    return mock


def _issues_by_field(result: ImprintResult) -> dict[str, str]:
    """Return {field_label: severity} for easy assertions."""
    return {i.field: i.severity for i in result.issues}


def _matched_by_field(result: ImprintResult) -> dict[str, str | None]:
    return {i.field: i.matched for i in result.issues}


# ── Happy path ────────────────────────────────────────────────────────────────


class TestFullyValidImprint:
    @pytest.fixture(autouse=True)
    def _patch(self):
        with patch(
            "scanner.scans.imprint.requests.get",
            return_value=_mock_response(_VALID_IMPRINT),
        ):
            self.result = _validate(_BASE)

    def test_no_fetch_error(self):
        assert self.result.fetch_error is None

    def test_name_ok(self):
        assert _issues_by_field(self.result)["Name / company"] == "ok"

    def test_street_ok(self):
        assert _issues_by_field(self.result)["Street address"] == "ok"

    def test_postal_code_ok(self):
        assert _issues_by_field(self.result)["Postal code"] == "ok"

    def test_email_ok(self):
        assert _issues_by_field(self.result)["E-mail address"] == "ok"

    def test_phone_ok(self):
        assert _issues_by_field(self.result)["Phone number"] == "ok"

    def test_ddg_ok(self):
        assert _issues_by_field(self.result)["Law reference: DDG"] == "ok"

    def test_no_errors(self):
        errors = [i for i in self.result.issues if i.severity == "error"]
        assert errors == [], f"Unexpected errors: {errors}"


# ── Missing required fields ───────────────────────────────────────────────────


class TestMissingFields:
    def _validate_html(self, html: str) -> ImprintResult:
        with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
            return _validate(_BASE)

    def test_missing_name_is_warning(self):
        html = _VALID_IMPRINT.replace("Inhaber: Max Mustermann", "")
        result = self._validate_html(html)
        assert _issues_by_field(result)["Name / company"] == "warning"

    def test_missing_street_is_error(self):
        html = _VALID_IMPRINT.replace("Musterstraße 12", "")
        result = self._validate_html(html)
        assert _issues_by_field(result)["Street address"] == "error"

    def test_missing_postal_code_is_error(self):
        html = _VALID_IMPRINT.replace("12345 Musterstadt", "Musterstadt")
        result = self._validate_html(html)
        assert _issues_by_field(result)["Postal code"] == "error"

    def test_missing_email_is_error(self):
        html = _VALID_IMPRINT.replace("E-Mail: max@example.com", "")
        result = self._validate_html(html)
        assert _issues_by_field(result)["E-mail address"] == "error"

    def test_missing_phone_is_warning(self):
        html = _VALID_IMPRINT.replace("Tel.: +49 30 123456", "")
        result = self._validate_html(html)
        assert _issues_by_field(result)["Phone number"] == "warning"


# ── Street address variants ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "street",
    [
        "Hauptstraße 1",
        "Bahnhofstrasse 22b",
        "Kirchgasse 5",
        "Lindenweg 8",
        "Rathausplatz 3",
        "Bundesallee 12",
        "Schillerring 7",
        "Elbdamm 99",
    ],
)
def test_street_variants_detected(street: str):
    html = _VALID_IMPRINT.replace("Musterstraße 12", street)
    with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
        result = _validate(_BASE)
    assert _issues_by_field(result)["Street address"] == "ok", f"Not detected: {street!r}"


# ── Phone number variants ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "phone",
    [
        "Tel.: +49 30 123456",
        "Telefon: 030 123456",
        "Tel: 0221/9876543",
        "+49 1573 3356316",
        "0800 123 4567",
    ],
)
def test_phone_variants_detected(phone: str):
    html = _VALID_IMPRINT.replace("Tel.: +49 30 123456", phone)
    with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
        result = _validate(_BASE)
    assert _issues_by_field(result)["Phone number"] == "ok", f"Not detected: {phone!r}"


# ── Law reference checks ──────────────────────────────────────────────────────


class TestLawReferences:
    def _validate_html(self, html: str) -> ImprintResult:
        with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
            return _validate(_BASE)

    def test_ddg_detected_as_ok(self):
        result = self._validate_html(_VALID_IMPRINT)  # already contains DDG
        assert _issues_by_field(result).get("Law reference: DDG") == "ok"

    def test_tmg_detected_as_warning(self):
        html = _VALID_IMPRINT.replace("§ 5 DDG", "§ 5 TMG")
        result = self._validate_html(html)
        assert _issues_by_field(result).get("Law reference: TMG") == "warning"

    def test_ttdsg_detected_as_info(self):
        html = _VALID_IMPRINT + "<p>Datenschutz gemäß TTDSG</p>"
        result = self._validate_html(html)
        assert _issues_by_field(result).get("Law reference: TTDSG") == "info"

    def test_no_law_reference_is_info(self):
        html = _VALID_IMPRINT.replace("§ 5 DDG", "")
        result = self._validate_html(html)
        assert _issues_by_field(result).get("Law reference") == "info"

    def test_matched_value_for_ddg(self):
        result = self._validate_html(_VALID_IMPRINT)
        matched = _matched_by_field(result).get("Law reference: DDG")
        assert matched == "DDG"

    def test_matched_value_for_tmg(self):
        html = _VALID_IMPRINT.replace("§ 5 DDG", "§ 5 TMG")
        result = self._validate_html(html)
        matched = _matched_by_field(result).get("Law reference: TMG")
        assert matched == "TMG"


# ── Company-type (GmbH) checks ────────────────────────────────────────────────


class TestGmbhChecks:
    def _validate_html(self, html: str) -> ImprintResult:
        with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
            return _validate(_BASE)

    def test_gmbh_without_handelsregister_is_error(self):
        html = _VALID_GMBH_IMPRINT.replace(
            "Handelsregister: HRB 123456, Amtsgericht Musterstadt", ""
        )
        result = self._validate_html(html)
        assert _issues_by_field(result).get("Handelsregister number") == "error"

    def test_gmbh_with_handelsregister_no_error(self):
        result = self._validate_html(_VALID_GMBH_IMPRINT)
        assert "Handelsregister number" not in _issues_by_field(result)

    def test_sole_trader_no_handelsregister_check(self):
        # Sole trader (no GmbH/AG/UG) should not trigger the Handelsregister check at all.
        result = self._validate_html(_VALID_IMPRINT)
        assert "Handelsregister number" not in _issues_by_field(result)


# ── Fetch failure ─────────────────────────────────────────────────────────────


class TestFetchFailure:
    def test_http_error_sets_fetch_error(self):
        with patch(
            "scanner.scans.imprint.requests.get",
            return_value=_mock_response("", status=404),
        ):
            result = _validate(_BASE)
        assert result.fetch_error is not None

    def test_connection_error_sets_fetch_error(self):
        with patch(
            "scanner.scans.imprint.requests.get",
            side_effect=requests.exceptions.ConnectionError("Connection refused"),
        ):
            result = _validate(_BASE)
        assert result.fetch_error is not None

    def test_fetch_error_produces_no_issues(self):
        with patch(
            "scanner.scans.imprint.requests.get",
            side_effect=requests.exceptions.Timeout("Timeout"),
        ):
            result = _validate(_BASE)
        assert result.issues == []


# ── Matched value extraction ──────────────────────────────────────────────────


class TestMatchedValues:
    @pytest.fixture(autouse=True)
    def _patch(self):
        with patch(
            "scanner.scans.imprint.requests.get",
            return_value=_mock_response(_VALID_IMPRINT),
        ):
            self.result = _validate(_BASE)
            self.matched = _matched_by_field(self.result)

    def test_email_matched_is_exact_address(self):
        assert self.matched["E-mail address"] == "max@example.com"

    def test_postal_code_matched_is_five_digits(self):
        assert self.matched["Postal code"] == "12345"

    def test_name_matched_includes_context(self):
        # Should include "Inhaber:" and the name that follows
        assert "Inhaber" in self.matched["Name / company"]

    def test_no_matched_on_missing_field(self):
        html = _VALID_IMPRINT.replace("E-Mail: max@example.com", "")
        with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
            result = _validate(_BASE)
        assert _matched_by_field(result)["E-mail address"] is None
