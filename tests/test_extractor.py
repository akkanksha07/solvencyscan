import json
from unittest.mock import patch

from corporatefailurelab.extraction import extractor

GOOD_YEAR = {
    "company_name": "Acme Corp", "currency": "USD", "fiscal_year": "FY2022",
    "total_assets": 1000, "total_liabilities": 400, "total_equity": 600,
    "current_assets": 500, "current_liabilities": 200, "receivables": 100,
    "inventory": 50, "retained_earnings": 300, "cash_and_equivalents": 150,
    "revenue": 800, "cogs": 400, "operating_income": 150,
    "interest_expense": 20, "net_income": 100, "cfo": 130, "capex": 40,
    "source_note": "Test fixture",
}


def _mock_complete(payload):
    return patch.object(extractor, "complete", return_value=json.dumps(payload))


def test_extract_years_happy_path():
    with _mock_complete([GOOD_YEAR]):
        results = extractor.extract_years("dummy text")
    assert len(results) == 1
    r = results[0]
    assert r.raw_year is not None
    assert r.raw_year.fiscal_year == "FY2022"
    assert r.raw_year.total_assets == 1000.0
    assert r.warnings == []


def test_extract_years_skips_entry_missing_required_field():
    bad_year = dict(GOOD_YEAR)
    del bad_year["total_assets"]
    with _mock_complete([bad_year]):
        results = extractor.extract_years("dummy text")
    assert len(results) == 1
    assert results[0].raw_year is None
    assert "total_assets" in results[0].warnings[0]


def test_extract_years_warns_on_missing_optional_fields():
    partial = dict(GOOD_YEAR)
    partial["inventory"] = None
    partial["retained_earnings"] = None
    with _mock_complete([partial]):
        results = extractor.extract_years("dummy text")
    r = results[0]
    assert r.raw_year is not None
    joined = " ".join(r.warnings)
    assert "quick ratio" in joined.lower()
    assert "altman z" in joined.lower()


def test_extract_years_chains_prior_balances_across_years():
    year1 = dict(GOOD_YEAR, fiscal_year="FY2021", total_assets=900, total_equity=500)
    year2 = dict(GOOD_YEAR, fiscal_year="FY2022")
    with _mock_complete([year2, year1]):  # out of order on purpose
        results = extractor.extract_years("dummy text")
    by_year = {r.raw_year.fiscal_year: r.raw_year for r in results}
    assert by_year["FY2021"].prior_total_assets is None
    assert by_year["FY2022"].prior_total_assets == 900
    assert by_year["FY2022"].prior_total_equity == 500


def test_extract_years_raises_on_non_list_response():
    with _mock_complete({"not": "a list"}):
        try:
            extractor.extract_years("dummy text")
            assert False, "expected ValueError"
        except ValueError:
            pass
