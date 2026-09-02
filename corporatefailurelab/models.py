"""Raw financial line items per company-year, and the computed metrics derived from them.

RawYear holds exactly the line items pulled from a single annual report /
10-K, in the company's reporting currency, as stated (no unit conversion
needed as long as a company is consistent year to year). `prior_total_assets`
and `prior_total_equity` are optional opening-balance figures (from the prior
year's balance sheet) used to average denominators for ROA/ROE/asset
turnover; if omitted, the calculators fall back to the closing balance.

`inventory`, `retained_earnings` and `cogs` are optional: some companies
don't disclose them (a cost-of-sales line is common to omit for services
companies; the data-collection workbook behind this project's initial 8
companies didn't capture inventory or retained earnings at all). When
missing, `quick_ratio` / `altman_z` / `gross_margin` degrade to NaN rather
than a wrong number -- see ratios.py / altman.py.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(kw_only=True)
class RawYear:
    fiscal_year: str  # e.g. "FY2016" or "2016"

    # --- Balance sheet ---
    total_assets: float
    total_liabilities: float
    total_equity: float
    current_assets: float
    current_liabilities: float
    receivables: float
    inventory: float | None = None
    retained_earnings: float | None = None
    # Free-text caveat surfaced verbatim in the UI next to the Altman Z''
    # section when retained_earnings is a proxy, an estimate, or otherwise
    # not a directly-sourced figure -- see scripts/import_excel.py.
    retained_earnings_note: str | None = None
    cash_and_equivalents: float | None = None

    # --- Income statement ---
    revenue: float
    operating_income: float  # EBIT
    interest_expense: float
    net_income: float
    cogs: float | None = None  # cost of goods sold / cost of sales

    # --- Cash flow statement ---
    cfo: float  # net cash from operating activities
    capex: float  # capital expenditure (positive number = cash spent)

    # --- Optional prior-period opening balances, for averaged ratios ---
    prior_total_assets: float | None = None
    prior_total_equity: float | None = None

    source: str = ""  # e.g. "FY2017 Annual Report, p.84"


@dataclass
class CompanyFinancials:
    slug: str
    years: list[RawYear]  # chronological order, oldest first


@dataclass
class YearMetrics:
    fiscal_year: str

    # Liquidity
    current_ratio: float
    quick_ratio: float

    # Profitability
    gross_margin: float
    operating_margin: float
    net_margin: float
    roa: float
    roe: float

    # Leverage
    debt_to_equity: float
    interest_coverage: float

    # Efficiency
    asset_turnover: float
    receivables_days: float

    # Cash flow quality
    cfo_to_net_income: float
    fcf_margin: float

    # Distress model
    altman_z: float
    altman_zone: str  # "distress" | "grey" | "safe" | "unknown"
    retained_earnings_note: str | None = None
