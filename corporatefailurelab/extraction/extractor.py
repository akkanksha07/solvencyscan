"""Claude-powered extraction of RawYear-shaped financials from annual report text.

Unlike the 8 pre-loaded companies (loaded from a data-collection workbook
that didn't capture every field), a fresh extraction asks for the FULL
RawYear schema including inventory and retained earnings, so ad-hoc uploads
can produce a complete quick_ratio and Altman Z'' out of the box.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..models import RawYear
from .llm import complete, extract_json

_REQUIRED_FIELDS = (
    "fiscal_year", "total_assets", "total_liabilities", "total_equity",
    "current_assets", "current_liabilities", "receivables",
    "revenue", "operating_income", "interest_expense", "net_income",
    "cfo", "capex",
)
_OPTIONAL_FIELDS = ("inventory", "retained_earnings", "cash_and_equivalents", "cogs")
_ALL_FIELDS = _REQUIRED_FIELDS + _OPTIONAL_FIELDS

_PROMPT = """You are a financial analyst extracting structured data from an annual report / 10-K.

Return ONLY a valid JSON array -- no markdown, no backticks, no commentary. One object per fiscal
year found in the primary financial statements (most annual reports show 2-3 years of
comparatives on the face of the balance sheet and income statement -- extract every year you can
find, not just the latest). Use null for any figure genuinely not disclosed. All monetary values
as plain numbers in the report's own reporting currency and scale (e.g. if the report is in
millions, give millions) -- do not convert currency or scale. Use negative numbers for losses.

Each object's schema:
{{
  "company_name": string,
  "currency": string,
  "fiscal_year": string,          // e.g. "FY2023" or "2023"
  "total_assets": number,
  "total_liabilities": number,     // if not stated directly, use Total Assets - Total Equity
  "total_equity": number,
  "current_assets": number,
  "current_liabilities": number,
  "receivables": number,           // trade receivables, net
  "inventory": number | null,
  "retained_earnings": number | null,
  "cash_and_equivalents": number | null,
  "revenue": number,
  "cogs": number | null,           // cost of goods sold / cost of sales, null if not disclosed separately
  "operating_income": number,      // EBIT -- operating profit before interest and tax
  "interest_expense": number,      // gross interest expense/finance costs before netting interest income
  "net_income": number,            // profit attributable to shareholders
  "cfo": number,                   // net cash from operating activities
  "capex": number,                 // capital expenditure, positive number
  "source_note": string            // which statement/page each figure came from, and any judgment calls
}}

Annual report text:
{text}"""


@dataclass
class ExtractedYear:
    raw_year: RawYear
    company_name: str
    currency: str
    warnings: list[str]


def _to_float(v) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_years(text: str) -> list[ExtractedYear]:
    """Runs one Claude extraction call and returns one ExtractedYear per
    fiscal year found. Years missing a required field are skipped, with a
    warning explaining what was missing."""
    prompt = _PROMPT.format(text=text[:60000])
    raw = complete(prompt, max_tokens=4000)
    data = extract_json(raw)
    if not isinstance(data, list):
        raise ValueError("Extraction did not return a JSON array of years.")

    results: list[ExtractedYear] = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        warnings = []
        missing = [f for f in _REQUIRED_FIELDS if _to_float(entry.get(f)) is None and f != "fiscal_year"]
        if missing:
            warnings.append(
                f"Skipped {entry.get('fiscal_year', '?')}: missing required field(s) {', '.join(missing)}."
            )
            results.append(ExtractedYear(
                raw_year=None, company_name=entry.get("company_name", "?"),
                currency=entry.get("currency", "?"), warnings=warnings,
            ))
            continue

        kwargs = {f: _to_float(entry.get(f)) for f in _ALL_FIELDS if f != "fiscal_year"}
        kwargs["fiscal_year"] = str(entry.get("fiscal_year", "?"))
        kwargs["source"] = str(entry.get("source_note", "AI-extracted from uploaded PDF"))
        raw_year = RawYear(**kwargs)
        if raw_year.inventory is None:
            warnings.append("Inventory not disclosed -- quick ratio will show n/a.")
        if raw_year.retained_earnings is None:
            warnings.append("Retained earnings not disclosed -- Altman Z'' will show n/a.")
        if raw_year.cogs is None:
            warnings.append("COGS not disclosed -- gross margin will show n/a.")

        results.append(ExtractedYear(
            raw_year=raw_year, company_name=entry.get("company_name", "?"),
            currency=entry.get("currency", "?"), warnings=warnings,
        ))

    _chain_prior_balances(results)
    return results


def _year_sort_key(fiscal_year: str) -> str:
    match = re.search(r"\d{4}", fiscal_year)
    return match.group(0) if match else fiscal_year


def _chain_prior_balances(results: list[ExtractedYear]) -> None:
    """Sorts successfully-extracted years chronologically and fills in each
    year's prior_total_assets/prior_total_equity from the previous year, so
    ROA/ROE/asset-turnover can average balances instead of falling back to
    closing-only."""
    ok = [r for r in results if r.raw_year is not None]
    ok.sort(key=lambda r: _year_sort_key(r.raw_year.fiscal_year))
    prior: RawYear | None = None
    for r in ok:
        if prior is not None:
            r.raw_year.prior_total_assets = prior.total_assets
            r.raw_year.prior_total_equity = prior.total_equity
        prior = r.raw_year
