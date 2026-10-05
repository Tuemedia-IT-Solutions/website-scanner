"""
tests/test_imprint.py
=====================
Tests for scanner/scans/imprint.py

Each test calls the internal _validate() function directly (no network),
by patching requests.get so we can feed arbitrary HTML page content.

Coverage:
  - All required fields present → all ok
  - Each individual required field missing → correct severity + field name
  - Law references: DDG (ok), TMG (error), TTDSG (info), none (info)
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

_VALID_IMPRINT_2 = """
<html><body>
<section class="hero" data-v-cb728d0d=""><div class="container" data-v-cb728d0d=""><div class="hero-content" data-v-cb728d0d=""><h1 class="hero-title" data-v-cb728d0d="">Impressum</h1><p class="hero-subtitle" data-v-cb728d0d="">Angaben gemäß § 5 DDG</p></div></div></section><section class="imprint-content" data-v-cb728d0d=""><div class="container" data-v-cb728d0d=""><div class="content-grid" data-v-cb728d0d=""><div class="info-section" data-v-cb728d0d=""><h2 data-v-cb728d0d="">Firmeninformationen</h2><div class="company-card" data-v-cb728d0d=""><h3 data-v-cb728d0d="">Tuemedia IT Solutions</h3><p class="owner" data-v-cb728d0d="">Inhaber: Max Mustermann</p><div class="address" data-v-cb728d0d=""><p data-v-cb728d0d="">Vogelhof 22</p><p data-v-cb728d0d="">45555 Musterort</p><p data-v-cb728d0d="">Deutschland</p></div></div></div><div class="info-section" data-v-cb728d0d=""><h2 data-v-cb728d0d="">Kontakt</h2><div class="contact-card" data-v-cb728d0d=""><div class="contact-item" data-v-cb728d0d=""><div class="contact-icon" data-v-cb728d0d=""><span class="iconify i-mdi:phone" aria-hidden="true" style="" data-v-cb728d0d=""></span></div><div class="contact-details" data-v-cb728d0d=""><span class="contact-label" data-v-cb728d0d="">Telefon:</span><a href="tel:+4911112222333" class="contact-link" data-v-cb728d0d="">+49 1573 3356316</a></div></div><div class="contact-item" data-v-cb728d0d=""><div class="contact-icon" data-v-cb728d0d=""><span class="iconify i-mdi:email" aria-hidden="true" style="" data-v-cb728d0d=""></span></div><div class="contact-details" data-v-cb728d0d=""><span class="contact-label" data-v-cb728d0d="">E-Mail:</span><a href="mailto:info@tuemedia-it.de" class="contact-link" data-v-cb728d0d="">info@tuemedia-it.de</a></div></div><div class="contact-item" data-v-cb728d0d=""><div class="contact-icon" data-v-cb728d0d=""><span class="iconify i-mdi:web" aria-hidden="true" style="" data-v-cb728d0d=""></span></div><div class="contact-details" data-v-cb728d0d=""><span class="contact-label" data-v-cb728d0d="">Website:</span><a href="https://www.tuemedia.de" class="contact-link" data-v-cb728d0d="">www.tuemedia-it.de</a></div></div></div></div><div class="info-section" data-v-cb728d0d=""><h2 data-v-cb728d0d="">Umsatzsteuer-Identifikationsnummer</h2><div class="vat-card" data-v-cb728d0d=""><div class="vat-number" data-v-cb728d0d="">DE352918460</div><p class="vat-description" data-v-cb728d0d="">Umsatzsteuer-Identifikationsnummer gemäß § 27 a Umsatzsteuergesetz</p></div></div><div class="info-section" data-v-cb728d0d=""><h2 data-v-cb728d0d="">Verantwortlich für den Inhalt nach § 55 Abs. 2 RStV</h2><div class="responsibility-card" data-v-cb728d0d=""><p class="responsible-name" data-v-cb728d0d="">Max Mustermann</p><p class="responsible-address" data-v-cb728d0d="">Vogelhof 22, 45555 Musterort</p></div></div><div class="info-section disclaimer-section" data-v-cb728d0d=""><h2 data-v-cb728d0d="">Haftungsausschluss</h2><div class="disclaimer-item" data-v-cb728d0d=""><h3 data-v-cb728d0d="">Haftung für Inhalte</h3><p data-v-cb728d0d="">Als Diensteanbieter sind wir gemäß § 7 Abs.1 DDG für eigene Inhalte auf diesen Seiten nach den allgemeinen Gesetzen verantwortlich. Nach §§ 8 bis 10 DDG sind wir als Diensteanbieter jedoch nicht unter der Verpflichtung, übermittelte oder gespeicherte fremde Informationen zu überwachen oder nach Umständen zu forschen, die auf eine rechtswidrige Tätigkeit hinweisen.</p></div><div class="disclaimer-item" data-v-cb728d0d=""><h3 data-v-cb728d0d="">Haftung für Links</h3><p data-v-cb728d0d="">Unser Angebot enthält Links zu externen Webseiten Dritter, auf deren Inhalte wir keinen Einfluss haben. Deshalb können wir für diese fremden Inhalte auch keine Gewähr übernehmen. Für die Inhalte der verlinkten Seiten ist stets der jeweilige Anbieter oder Betreiber der Seiten verantwortlich.</p></div><div class="disclaimer-item" data-v-cb728d0d=""><h3 data-v-cb728d0d="">Urheberrecht</h3><p data-v-cb728d0d="">Die durch die Seitenbetreiber erstellten Inhalte und Werke auf diesen Seiten unterliegen dem deutschen Urheberrecht. Die Vervielfältigung, Bearbeitung, Verbreitung und jede Art der Verwertung außerhalb der Grenzen des Urheberrechtes bedürfen der schriftlichen Zustimmung des jeweiligen Autors bzw. Erstellers.</p></div></div></div></div></section>
</body></html>
"""


def _mock_response(html: str, status: int = 200) -> MagicMock:
    """Return a mock requests.Response for the given HTML."""
    mock = MagicMock()
    mock.status_code = status
    mock.content = html.encode()
    if status >= 400:
        mock.raise_for_status.side_effect = requests.exceptions.HTTPError(
            f"HTTP {status}"
        )
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


class TestFullyValidImprint2:
    """Happy-path tests using the real-world Tuemedia IT Solutions imprint."""

    @pytest.fixture(autouse=True)
    def _patch(self):
        with patch(
            "scanner.scans.imprint.requests.get",
            return_value=_mock_response(_VALID_IMPRINT_2),
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
        with patch(
            "scanner.scans.imprint.requests.get", return_value=_mock_response(html)
        ):
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
        "Vogelhof 22",
    ],
)
def test_street_variants_detected(street: str):
    html = _VALID_IMPRINT.replace("Musterstraße 12", street)
    with patch("scanner.scans.imprint.requests.get", return_value=_mock_response(html)):
        result = _validate(_BASE)
    assert (
        _issues_by_field(result)["Street address"] == "ok"
    ), f"Not detected: {street!r}"


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
        with patch(
            "scanner.scans.imprint.requests.get", return_value=_mock_response(html)
        ):
            return _validate(_BASE)

    def test_ddg_detected_as_ok(self):
        result = self._validate_html(_VALID_IMPRINT)  # already contains DDG
        assert _issues_by_field(result).get("Law reference: DDG") == "ok"

    def test_tmg_detected_as_error(self):
        html = _VALID_IMPRINT.replace("§ 5 DDG", "§ 5 TMG")
        result = self._validate_html(html)
        assert _issues_by_field(result).get("Law reference: TMG") == "error"

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
        with patch(
            "scanner.scans.imprint.requests.get", return_value=_mock_response(html)
        ):
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
        with patch(
            "scanner.scans.imprint.requests.get", return_value=_mock_response(html)
        ):
            result = _validate(_BASE)
        assert _matched_by_field(result)["E-mail address"] is None
