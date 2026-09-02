"""Validation: how well would the Z''-Score/ratio warning system have flagged
the 4 failed companies as high-risk, and how many of the 4 healthy companies
would it have wrongly flagged (false positives)? Modelled as a confusion
matrix, computed two ways:

- "final_year": only the last available fiscal year before collapse (for
  failed companies) / the most recent available year (for healthy companies)
  counts as the prediction. This mirrors how the model would be used in
  practice -- one read, right before the outcome is known.
- "any_year": counts a company as flagged if ANY of its 3 analysed years
  hit the distress zone. More lenient; shows early-warning lead time but
  inflates the false-positive rate for healthy companies that had one rough
  year.

A company is "flagged high-risk" when its Altman Z'' zone is "distress"
(red). The "grey" zone is deliberately excluded from a positive flag --
matching Altman's own zone naming, grey-zone companies aren't a clear
model call either way.
"""

from __future__ import annotations

from dataclasses import dataclass

from .companies import COMPANIES, Outcome
from .data_loader import is_populated, load_company_metrics
from .models import YearMetrics


@dataclass
class CompanyPrediction:
    slug: str
    name: str
    outcome: Outcome
    years: list[YearMetrics]
    final_year_flagged: bool
    any_year_flagged: bool
    has_unknown_zone: bool  # True if any analysed year's Z'' couldn't be computed


@dataclass
class ConfusionMatrix:
    true_positives: list[CompanyPrediction]
    false_negatives: list[CompanyPrediction]
    false_positives: list[CompanyPrediction]
    true_negatives: list[CompanyPrediction]
    excluded: list[CompanyPrediction]  # Z'' unavailable (e.g. missing retained_earnings)

    @property
    def sensitivity(self) -> float | None:
        """Of the failed companies, fraction correctly flagged (recall)."""
        n = len(self.true_positives) + len(self.false_negatives)
        return len(self.true_positives) / n if n else None

    @property
    def specificity(self) -> float | None:
        """Of the healthy companies, fraction correctly NOT flagged."""
        n = len(self.true_negatives) + len(self.false_positives)
        return len(self.true_negatives) / n if n else None


def _predictions(rule: str) -> list[CompanyPrediction]:
    out = []
    for slug, meta in COMPANIES.items():
        if not is_populated(slug):
            continue
        years = load_company_metrics(slug)
        if not years:
            continue
        final_flagged = years[-1].altman_zone == "distress"
        any_flagged = any(y.altman_zone == "distress" for y in years)
        out.append(
            CompanyPrediction(
                slug=slug,
                name=meta.name,
                outcome=meta.outcome,
                years=years,
                final_year_flagged=final_flagged,
                any_year_flagged=any_flagged,
                has_unknown_zone=any(y.altman_zone == "unknown" for y in years),
            )
        )
    return out


def build_confusion_matrix(rule: str = "final_year") -> ConfusionMatrix:
    """rule: "final_year" (default) or "any_year".

    A company is excluded from the matrix (not silently counted as a
    negative) when its Z'' can't be evaluated under the chosen rule:
    "final_year" excludes it if the final year's zone is "unknown";
    "any_year" excludes it only if EVERY analysed year is "unknown" (a
    known "distress"/"grey"/"safe" year elsewhere still counts).
    """
    preds = _predictions(rule)
    tp, fn, fp, tn, excluded = [], [], [], [], []
    for p in preds:
        if rule == "final_year":
            unresolvable = p.years[-1].altman_zone == "unknown"
        else:
            unresolvable = all(y.altman_zone == "unknown" for y in p.years)
        if unresolvable:
            excluded.append(p)
            continue
        flagged = p.final_year_flagged if rule == "final_year" else p.any_year_flagged
        if p.outcome == Outcome.FAILED:
            (tp if flagged else fn).append(p)
        else:
            (fp if flagged else tn).append(p)
    return ConfusionMatrix(
        true_positives=tp, false_negatives=fn, false_positives=fp, true_negatives=tn,
        excluded=excluded,
    )
