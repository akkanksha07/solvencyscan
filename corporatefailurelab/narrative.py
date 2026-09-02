"""Plain-English per-company summary, built entirely from each company's own
computed metrics -- no canned text, no AI call. Every sentence quotes an
actual number and, where relevant, names the fiscal years it moved between.

Deliberately deterministic (unlike the PDF-upload extraction feature, which
does call Claude): the point of this paragraph is to be a transparent,
checkable readout of the ratio engine, not a model's opinion.
"""

from __future__ import annotations

from .models import YearMetrics
from .thresholds import BANDS, GREEN, RED

_METRIC_LABELS: dict[str, tuple[str, str]] = {
    # key -> (label, format kind)
    "current_ratio": ("current ratio", "x"),
    "quick_ratio": ("quick ratio", "x"),
    "net_margin": ("net margin", "%"),
    "operating_margin": ("operating margin", "%"),
    "debt_to_equity": ("debt-to-equity", "x"),
    "interest_coverage": ("interest coverage", "x"),
    "cfo_to_net_income": ("cash-flow-to-profit ratio (CFO/net income)", "x"),
    "fcf_margin": ("free cash flow margin", "%"),
    "roa": ("return on assets", "%"),
    "roe": ("return on equity", "%"),
}


def _fmt(value: float, kind: str) -> str:
    if value != value:  # NaN
        return "n/a"
    if value == float("inf"):
        return "effectively infinite"
    if kind == "%":
        return f"{value * 100:.1f}%"
    return f"{value:.2f}x"


def _direction(key: str, first: float, last: float) -> str | None:
    """Returns a short clause describing how a metric moved, or None if
    unchanged/not meaningfully comparable (NaN on either end)."""
    if first != first or last != last:  # NaN either side
        return None
    band = BANDS.get(key)
    if band is None:
        return None
    # Ignore moves too small to be a real trend (avoids e.g. "2.4% -> 2.4% improved").
    denom = max(abs(first), abs(last), 1e-9)
    if abs(last - first) / denom < 0.02:
        return "stayed roughly flat"
    better = last > first if band.higher_is_better else last < first
    worse = last < first if band.higher_is_better else last > first
    first_flag = band.flag(first)
    last_flag = band.flag(last)
    crossed_into_red = first_flag != RED and last_flag == RED
    crossed_out_of_red = first_flag == RED and last_flag != RED
    reached_green = last_flag == GREEN and first_flag != GREEN
    if crossed_into_red:
        return "worsened enough to cross into the red zone"
    if crossed_out_of_red:
        return "recovered out of the red zone"
    if reached_green:
        return "improved into the green zone"
    if worse:
        return "deteriorated"
    if better:
        return "improved"
    return "stayed roughly flat"


def generate_narrative(name: str, years: list[YearMetrics]) -> str:
    if not years:
        return ""
    first, last = years[0], years[-1]
    span = f"{first.fiscal_year}-{last.fiscal_year}" if len(years) > 1 else first.fiscal_year

    sentences: list[str] = []

    # Liquidity
    if first.current_ratio == first.current_ratio and last.current_ratio == last.current_ratio:
        d = _direction("current_ratio", first.current_ratio, last.current_ratio)
        sentences.append(
            f"Its current ratio {d} from {_fmt(first.current_ratio, 'x')} in {first.fiscal_year} "
            f"to {_fmt(last.current_ratio, 'x')} in {last.fiscal_year}"
            f"{', short-term liabilities now exceed short-term assets' if last.current_ratio < 1 else ''}."
        )

    # Profitability
    d = _direction("net_margin", first.net_margin, last.net_margin)
    if d:
        sentences.append(
            f"Net margin {d}, from {_fmt(first.net_margin, '%')} to {_fmt(last.net_margin, '%')}"
            f"{' (i.e. the company moved into an outright loss)' if last.net_margin < 0 <= first.net_margin else ''}."
        )

    # Leverage
    d = _direction("debt_to_equity", first.debt_to_equity, last.debt_to_equity)
    if d:
        sentences.append(
            f"Debt-to-equity {d}, from {_fmt(first.debt_to_equity, 'x')} to "
            f"{_fmt(last.debt_to_equity, 'x')}."
        )
    d = _direction("interest_coverage", first.interest_coverage, last.interest_coverage)
    if d:
        sentences.append(
            f"Interest coverage {d}, from {_fmt(first.interest_coverage, 'x')} to "
            f"{_fmt(last.interest_coverage, 'x')}"
            f"{' -- operating profit no longer covers interest payments' if last.interest_coverage < 1 else ''}."
        )

    # Cash flow quality
    d = _direction("cfo_to_net_income", first.cfo_to_net_income, last.cfo_to_net_income)
    if d:
        gap_note = ""
        if last.cfo_to_net_income < 1 and last.cfo_to_net_income == last.cfo_to_net_income:
            gap_note = " -- reported profit is running ahead of actual cash generated"
        sentences.append(
            f"The cash-flow-to-profit ratio (CFO/net income) {d}, from "
            f"{_fmt(first.cfo_to_net_income, 'x')} to {_fmt(last.cfo_to_net_income, 'x')}{gap_note}."
        )
    d = _direction("fcf_margin", first.fcf_margin, last.fcf_margin)
    if d:
        sentences.append(
            f"Free cash flow margin {d}, from {_fmt(first.fcf_margin, '%')} to "
            f"{_fmt(last.fcf_margin, '%')}"
            f"{' -- the business is burning cash after capex' if last.fcf_margin < 0 else ''}."
        )

    # Altman Z'' -- only if computable for at least one year
    known_z = [y for y in years if y.altman_zone != "unknown"]
    if known_z:
        lz = known_z[-1]
        sentences.append(
            f"Its Altman Z''-Score reached {lz.altman_z:.2f} by {lz.fiscal_year}, placing it in "
            f"the {lz.altman_zone.upper()} zone of the distress model."
        )
    else:
        sentences.append(
            "Its Altman Z''-Score (the headline distress model) could not be computed for any "
            "of these years because retained earnings wasn't part of the collected data -- this "
            "summary is based on the surviving ratio evidence above only."
        )

    red_count_first = sum(
        1 for k in _METRIC_LABELS if BANDS.get(k) and BANDS[k].flag(getattr(first, k)) == RED
    )
    red_count_last = sum(
        1 for k in _METRIC_LABELS if BANDS.get(k) and BANDS[k].flag(getattr(last, k)) == RED
    )
    was_were_last = "was" if red_count_last == 1 else "were"
    if red_count_last == 0:
        closer = f"By {last.fiscal_year}, none of the tracked ratios were in the red zone."
    elif red_count_first == 0:
        closer = (
            f"By {last.fiscal_year}, {red_count_last} of the tracked ratios had moved into "
            f"the red zone, versus none in {first.fiscal_year}."
        )
    else:
        closer = (
            f"By {last.fiscal_year}, {red_count_last} of the tracked ratios {was_were_last} in "
            f"the red zone (vs {red_count_first} in {first.fiscal_year})."
        )
    sentences.append(closer)

    return f"{name}, {span}: " + " ".join(sentences)
