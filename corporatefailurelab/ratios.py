"""Ratio calculators. Each takes a RawYear and returns a single float.

Where a ratio conventionally uses an *average* denominator (ROA, ROE, asset
turnover), we average opening and closing balance when the prior-period
balance is available on the RawYear (`prior_total_assets`/`prior_total_equity`),
and fall back to the closing balance alone otherwise (documented per-function).
"""

from __future__ import annotations

from .models import RawYear

DAYS_IN_YEAR = 365.0


def _avg(closing: float, opening: float | None) -> float:
    return (closing + opening) / 2 if opening is not None else closing


def current_ratio(y: RawYear) -> float:
    return y.current_assets / y.current_liabilities


def quick_ratio(y: RawYear) -> float:
    """(Current assets - inventory) / current liabilities. NaN if inventory unknown."""
    if y.inventory is None:
        return float("nan")
    return (y.current_assets - y.inventory) / y.current_liabilities


def gross_margin(y: RawYear) -> float:
    """NaN if COGS isn't disclosed (common for services companies)."""
    if y.cogs is None:
        return float("nan")
    return (y.revenue - y.cogs) / y.revenue


def operating_margin(y: RawYear) -> float:
    return y.operating_income / y.revenue


def net_margin(y: RawYear) -> float:
    return y.net_income / y.revenue


def roa(y: RawYear) -> float:
    """Net income / average total assets (closing only if no prior-year balance)."""
    return y.net_income / _avg(y.total_assets, y.prior_total_assets)


def roe(y: RawYear) -> float:
    """Net income / average total equity (closing only if no prior-year balance)."""
    return y.net_income / _avg(y.total_equity, y.prior_total_equity)


def debt_to_equity(y: RawYear) -> float:
    return y.total_liabilities / y.total_equity


def interest_coverage(y: RawYear) -> float:
    """EBIT / interest expense. Returns +inf if interest expense is ~0 (no debt burden)."""
    if y.interest_expense == 0:
        return float("inf")
    return y.operating_income / y.interest_expense


def asset_turnover(y: RawYear) -> float:
    """Revenue / average total assets (closing only if no prior-year balance)."""
    return y.revenue / _avg(y.total_assets, y.prior_total_assets)


def receivables_days(y: RawYear) -> float:
    return (y.receivables / y.revenue) * DAYS_IN_YEAR


def cfo_to_net_income(y: RawYear) -> float:
    """Cash-flow-quality check: operating cash flow vs reported profit.

    Returns +inf if net income is ~0 and CFO is positive (undefined ratio,
    treated as strong); returns 0 if both are ~0.
    """
    if y.net_income == 0:
        return float("inf") if y.cfo > 0 else 0.0
    return y.cfo / y.net_income


def free_cash_flow(y: RawYear) -> float:
    return y.cfo - y.capex


def fcf_margin(y: RawYear) -> float:
    return free_cash_flow(y) / y.revenue
