from corporatefailurelab.data_loader import compute_year_metrics
from corporatefailurelab.models import RawYear
from corporatefailurelab.narrative import generate_narrative

IMPROVING = RawYear(
    fiscal_year="FY2022",
    total_assets=1000, total_liabilities=400, total_equity=600,
    current_assets=500, current_liabilities=400, inventory=100,
    receivables=100, retained_earnings=350,
    revenue=800, cogs=400, operating_income=150, interest_expense=20,
    net_income=100, cfo=130, capex=40,
)
WORSENING = RawYear(
    fiscal_year="FY2024",
    total_assets=1000, total_liabilities=950, total_equity=50,
    current_assets=200, current_liabilities=300, inventory=50,
    receivables=150, retained_earnings=-100,
    revenue=800, cogs=750, operating_income=-10, interest_expense=40,
    net_income=-60, cfo=-20, capex=30,
)
NO_RETAINED_EARNINGS = RawYear(
    fiscal_year="FY2022",
    total_assets=1000, total_liabilities=400, total_equity=600,
    current_assets=500, current_liabilities=400,
    receivables=100,
    revenue=800, cogs=400, operating_income=150, interest_expense=20,
    net_income=100, cfo=130, capex=40,
)


def test_narrative_mentions_company_and_years():
    years = [compute_year_metrics(IMPROVING), compute_year_metrics(WORSENING)]
    text = generate_narrative("Acme Corp", years)
    assert "Acme Corp" in text
    assert "FY2022-FY2024" in text


def test_narrative_quotes_real_numbers_not_generic_text():
    years = [compute_year_metrics(IMPROVING), compute_year_metrics(WORSENING)]
    text = generate_narrative("Acme Corp", years)
    # Debt-to-equity goes from 400/600=0.67x to 950/50=19.00x -- both should appear.
    assert "0.67x" in text
    assert "19.00x" in text


def test_narrative_flags_missing_retained_earnings():
    years = [compute_year_metrics(NO_RETAINED_EARNINGS)]
    text = generate_narrative("Acme Corp", years)
    assert "could not be computed" in text


def test_narrative_empty_years_returns_empty_string():
    assert generate_narrative("Acme Corp", []) == ""
