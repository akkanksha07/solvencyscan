"""Load raw per-company JSON files from data/raw/ and compute metrics."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from . import altman, ratios
from .companies import COMPANIES, CompanyMeta
from .models import CompanyFinancials, RawYear, YearMetrics

DATA_RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
_RAW_YEAR_FIELDS = {f.name for f in dataclasses.fields(RawYear)}


def load_raw(slug: str) -> CompanyFinancials:
    path = DATA_RAW_DIR / f"{slug}.json"
    payload = json.loads(path.read_text())
    years = [
        RawYear(**{k: v for k, v in y.items() if k in _RAW_YEAR_FIELDS})
        for y in payload["years"]
    ]
    return CompanyFinancials(slug=slug, years=years)


def is_populated(slug: str) -> bool:
    """A template file exists but has an empty `years` list until filled in."""
    try:
        raw = load_raw(slug)
    except (FileNotFoundError, json.JSONDecodeError):
        return False
    return len(raw.years) > 0


def compute_year_metrics(y: RawYear) -> YearMetrics:
    z = altman.altman_z(y)
    return YearMetrics(
        fiscal_year=y.fiscal_year,
        current_ratio=ratios.current_ratio(y),
        quick_ratio=ratios.quick_ratio(y),
        gross_margin=ratios.gross_margin(y),
        operating_margin=ratios.operating_margin(y),
        net_margin=ratios.net_margin(y),
        roa=ratios.roa(y),
        roe=ratios.roe(y),
        debt_to_equity=ratios.debt_to_equity(y),
        interest_coverage=ratios.interest_coverage(y),
        asset_turnover=ratios.asset_turnover(y),
        receivables_days=ratios.receivables_days(y),
        cfo_to_net_income=ratios.cfo_to_net_income(y),
        fcf_margin=ratios.fcf_margin(y),
        altman_z=z,
        altman_zone=altman.altman_zone(z),
        retained_earnings_note=y.retained_earnings_note,
    )


def load_company_metrics(slug: str) -> list[YearMetrics]:
    raw = load_raw(slug)
    return [compute_year_metrics(y) for y in raw.years]


def available_companies() -> list[CompanyMeta]:
    """Companies whose data/raw/<slug>.json has at least one filled-in year."""
    return [meta for slug, meta in COMPANIES.items() if is_populated(slug)]
