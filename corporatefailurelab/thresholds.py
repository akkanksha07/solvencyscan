"""Red/orange/green risk bands for every computed metric.

These are generic, commonly-cited textbook heuristics (see comments per
metric), NOT industry-specific benchmarks. They're deliberately the same
across all 8 companies so the dashboard stays comparable, but that means
metrics like gross margin or asset turnover -- which vary a lot by industry
even for healthy firms -- should be read as rough distress signals (is it
weak/negative/declining?) rather than precise industry verdicts. This
tradeoff is called out again in the dashboard itself next to each metric.

Bands are expressed as (red_cutoff, orange_cutoff) with a `higher_is_better`
direction:
  - higher_is_better=True:  value < red_cutoff -> red
                             red_cutoff <= value < orange_cutoff -> orange
                             value >= orange_cutoff -> green
  - higher_is_better=False: value > red_cutoff -> red
                             orange_cutoff < value <= red_cutoff -> orange
                             value <= orange_cutoff -> green
"""

from __future__ import annotations

from dataclasses import dataclass

RED, ORANGE, GREEN, GREY = "red", "orange", "green", "grey"


@dataclass(frozen=True)
class Band:
    red_cutoff: float
    orange_cutoff: float
    higher_is_better: bool = True
    # Source / rationale, shown as a tooltip in the dashboard.
    rationale: str = ""

    def flag(self, value: float) -> str:
        if value != value:  # NaN guard
            return ORANGE
        if self.higher_is_better:
            if value < self.red_cutoff:
                return RED
            if value < self.orange_cutoff:
                return ORANGE
            return GREEN
        else:
            if value > self.red_cutoff:
                return RED
            if value > self.orange_cutoff:
                return ORANGE
            return GREEN


BANDS: dict[str, Band] = {
    "current_ratio": Band(
        1.0, 1.5, True,
        "Below 1.0: current liabilities exceed current assets, a classic "
        "short-term solvency red flag. 1.0-1.5 is thin cover.",
    ),
    "quick_ratio": Band(
        0.5, 1.0, True,
        "Below 0.5: can't cover half of current liabilities without selling "
        "inventory. 1.0+ is the traditional 'healthy' benchmark.",
    ),
    "gross_margin": Band(
        0.10, 0.30, True,
        "Generic band, not industry-adjusted -- persistently thin gross "
        "margin limits room to absorb cost shocks.",
    ),
    "operating_margin": Band(
        0.0, 0.10, True,
        "Negative operating margin means the core business loses money "
        "before financing costs.",
    ),
    "net_margin": Band(
        0.0, 0.05, True,
        "Negative net margin means the company is losing money overall.",
    ),
    "roa": Band(
        0.0, 0.05, True,
        "Negative ROA means assets are destroying value, not generating it.",
    ),
    "roe": Band(
        0.0, 0.10, True,
        "Negative ROE means shareholders' equity is being eroded.",
    ),
    "debt_to_equity": Band(
        2.0, 1.0, False,
        "Above 2.0x is commonly treated as high leverage; above this, small "
        "earnings shocks can breach covenants.",
    ),
    "interest_coverage": Band(
        1.5, 3.0, True,
        "Below 1.5x is a classic going-concern warning sign (earnings barely "
        "cover interest); below 1.0x means earnings don't cover interest at all.",
    ),
    "asset_turnover": Band(
        0.5, 1.0, True,
        "Generic band, not industry-adjusted -- low turnover means assets "
        "are generating little revenue relative to their size.",
    ),
    "receivables_days": Band(
        90, 45, False,
        "Rising/high days-to-collect can signal customers struggling to pay, "
        "or revenue recognition aggressiveness.",
    ),
    "cfo_to_net_income": Band(
        0.8, 1.0, True,
        "Ratio persistently below 1.0 means reported profit isn't converting "
        "to cash; below 0 means operating cash flow is negative outright.",
    ),
    "fcf_margin": Band(
        0.0, 0.05, True,
        "Negative free cash flow margin means the company burns cash after "
        "capex, even if net income is positive.",
    ),
}

# Altman Z'' zone -> flag colour (zones already computed in altman.py).
# "unknown" means retained_earnings wasn't available to compute Z'' at all --
# distinct from "grey" (Z'' computed, just in the ambiguous middle band).
ALTMAN_ZONE_FLAG = {"distress": RED, "grey": ORANGE, "safe": GREEN, "unknown": GREY}


def flag_for(metric: str, value: float) -> str:
    band = BANDS.get(metric)
    if band is None:
        return ORANGE
    return band.flag(value)
