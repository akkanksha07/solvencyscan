import math

from corporatefailurelab import altman, ratios
from corporatefailurelab.models import RawYear
from corporatefailurelab.thresholds import GREEN, ORANGE, RED, flag_for

HEALTHY = RawYear(
    fiscal_year="FY2024",
    total_assets=1000, total_liabilities=400, total_equity=600,
    current_assets=500, current_liabilities=200, inventory=100,
    cash_and_equivalents=300, receivables=100, retained_earnings=350,
    revenue=800, cogs=400, operating_income=150, interest_expense=20,
    net_income=100, cfo=130, capex=40,
)

DISTRESSED = RawYear(
    fiscal_year="FY2017",
    total_assets=1000, total_liabilities=950, total_equity=50,
    current_assets=200, current_liabilities=300, inventory=50,
    cash_and_equivalents=20, receivables=150, retained_earnings=-100,
    revenue=800, cogs=750, operating_income=-10, interest_expense=40,
    net_income=-60, cfo=-20, capex=30,
)


def test_current_ratio():
    assert ratios.current_ratio(HEALTHY) == 2.5
    assert math.isclose(ratios.current_ratio(DISTRESSED), 200 / 300)


def test_quick_ratio():
    assert ratios.quick_ratio(HEALTHY) == (500 - 100) / 200


def test_margins():
    assert ratios.gross_margin(HEALTHY) == (800 - 400) / 800
    assert ratios.operating_margin(HEALTHY) == 150 / 800
    assert ratios.net_margin(HEALTHY) == 100 / 800


def test_roa_roe_no_prior_balance_falls_back_to_closing():
    assert ratios.roa(HEALTHY) == 100 / 1000
    assert ratios.roe(HEALTHY) == 100 / 600


def test_roa_averages_when_prior_given():
    y = RawYear(**{**HEALTHY.__dict__, "prior_total_assets": 800})
    assert ratios.roa(y) == 100 / ((1000 + 800) / 2)


def test_debt_to_equity_and_interest_coverage():
    assert ratios.debt_to_equity(HEALTHY) == 400 / 600
    assert ratios.interest_coverage(HEALTHY) == 150 / 20
    assert ratios.interest_coverage(DISTRESSED) == -10 / 40


def test_interest_coverage_zero_interest_is_inf():
    y = RawYear(**{**HEALTHY.__dict__, "interest_expense": 0})
    assert ratios.interest_coverage(y) == float("inf")


def test_receivables_days():
    assert math.isclose(ratios.receivables_days(HEALTHY), (100 / 800) * 365)


def test_cfo_to_net_income_and_fcf_margin():
    assert ratios.cfo_to_net_income(HEALTHY) == 130 / 100
    assert ratios.free_cash_flow(HEALTHY) == 130 - 40
    assert ratios.fcf_margin(HEALTHY) == (130 - 40) / 800


def test_altman_z_healthy_is_safe_zone():
    z = altman.altman_z(HEALTHY)
    assert altman.altman_zone(z) == "safe"


def test_altman_z_distressed_is_distress_zone():
    z = altman.altman_z(DISTRESSED)
    assert altman.altman_zone(z) == "distress"


def test_thresholds_flag_direction():
    assert flag_for("current_ratio", 0.5) == RED
    assert flag_for("current_ratio", 1.2) == ORANGE
    assert flag_for("current_ratio", 2.0) == GREEN
    # lower-is-better metric: debt_to_equity
    assert flag_for("debt_to_equity", 3.0) == RED
    assert flag_for("debt_to_equity", 1.5) == ORANGE
    assert flag_for("debt_to_equity", 0.5) == GREEN
