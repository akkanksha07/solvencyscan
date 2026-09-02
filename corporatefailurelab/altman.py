"""Altman Z''-Score (non-manufacturing / emerging-markets variant, Altman 1995).

Chosen over the original 1968 Z-Score because the 8 companies span
construction, travel, payments, energy trading, retail, tech and consumer
goods -- the original model's asset-turnover term (X5) and its reliance on
market value of equity don't transfer cleanly across such different capital
structures. Z'' drops X5 entirely and uses *book* value of equity, so one
formula applies uniformly to every company here.

    Z'' = 6.56*X1 + 3.26*X2 + 6.72*X3 + 1.05*X4

    X1 = Working Capital / Total Assets            = (CA - CL) / TA
    X2 = Retained Earnings / Total Assets
    X3 = EBIT / Total Assets
    X4 = Book Value of Equity / Total Liabilities

Zone cutoffs (Altman's published thresholds for this model, no market-cap
constant added):
    Z'' < 1.1              -> "distress"  (red)
    1.1 <= Z'' <= 2.6       -> "grey"      (orange)
    Z'' > 2.6               -> "safe"      (green)
"""

from __future__ import annotations

from .models import RawYear

DISTRESS_CUTOFF = 1.1
SAFE_CUTOFF = 2.6


def altman_z(y: RawYear) -> float:
    """NaN if retained_earnings is unknown -- X2 can't be silently zeroed,
    that would materially overstate the score (X2 carries the 2nd-highest
    weight, 3.26)."""
    if y.retained_earnings is None:
        return float("nan")
    x1 = (y.current_assets - y.current_liabilities) / y.total_assets
    x2 = y.retained_earnings / y.total_assets
    x3 = y.operating_income / y.total_assets
    x4 = y.total_equity / y.total_liabilities
    return 6.56 * x1 + 3.26 * x2 + 6.72 * x3 + 1.05 * x4


def altman_zone(z: float) -> str:
    if z != z:  # NaN guard (NaN != NaN is the portable check)
        return "unknown"
    if z < DISTRESS_CUTOFF:
        return "distress"
    if z <= SAFE_CUTOFF:
        return "grey"
    return "safe"
