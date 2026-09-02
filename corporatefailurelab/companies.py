"""Registry of the 8 companies analysed: 4 failed vs 4 healthy comparators."""

from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    FAILED = "failed"
    HEALTHY = "healthy"


@dataclass(frozen=True)
class CompanyMeta:
    slug: str
    name: str
    outcome: Outcome
    sector: str
    # For FAILED companies: the calendar year collapse/insolvency occurred.
    # The 3 analysed years are normally the 3 full fiscal years immediately
    # preceding this, but see `notes` for exceptions (e.g. a company whose
    # final pre-collapse annual report was never published or is unreliable).
    collapse_year: int | None
    notes: str = ""


COMPANIES: dict[str, CompanyMeta] = {
    "carillion": CompanyMeta(
        slug="carillion",
        name="Carillion plc",
        outcome=Outcome.FAILED,
        sector="Construction & outsourcing",
        collapse_year=2018,
        notes="Compulsory liquidation announced 15 Jan 2018. No FY2017 annual "
        "report was ever published (the ~£845m contract write-down was "
        "disclosed via an RNS stock-exchange announcement in Jul 2017, not "
        "an annual report) -- uses FY2014-2016 instead, treating FY2017 as "
        "the failure event itself rather than a data year.",
    ),
    "thomas_cook": CompanyMeta(
        slug="thomas_cook",
        name="Thomas Cook Group plc",
        outcome=Outcome.FAILED,
        sector="Travel & tourism",
        collapse_year=2019,
        notes="Compulsory liquidation 23 Sep 2019. Use FY2016-2018.",
    ),
    "wirecard": CompanyMeta(
        slug="wirecard",
        name="Wirecard AG",
        outcome=Outcome.FAILED,
        sector="Payments / fintech",
        collapse_year=2020,
        notes="Insolvency filed 25 Jun 2020. Uses FY2016-2018, not FY2019: "
        "the FY2019 annual report was delayed repeatedly while auditor EY "
        "sought confirmation of EUR 1.9bn in cash that turned out not to "
        "exist, and EY ultimately refused to sign off it -- so FY2019 is "
        "excluded as unreliable rather than used. Reported figures for "
        "FY2016-2018 are the as-filed numbers, later found to be partly "
        "fabricated; this tool tests whether the DISTRESS signal was "
        "visible even in the numbers as reported, not whether fraud was "
        "detectable (that's a different, forensic question).",
    ),
    "enron": CompanyMeta(
        slug="enron",
        name="Enron Corp.",
        outcome=Outcome.FAILED,
        sector="Energy trading",
        collapse_year=2001,
        notes="Chapter 11 filed 2 Dec 2001. Use FY1998-2000.",
    ),
    "apple": CompanyMeta(
        slug="apple",
        name="Apple Inc.",
        outcome=Outcome.HEALTHY,
        sector="Technology / hardware",
        collapse_year=None,
        notes="Any recent 3 consecutive fiscal years.",
    ),
    "walmart": CompanyMeta(
        slug="walmart",
        name="Walmart Inc.",
        outcome=Outcome.HEALTHY,
        sector="Retail",
        collapse_year=None,
        notes="Any recent 3 consecutive fiscal years.",
    ),
    "microsoft": CompanyMeta(
        slug="microsoft",
        name="Microsoft Corp.",
        outcome=Outcome.HEALTHY,
        sector="Technology / software",
        collapse_year=None,
        notes="Any recent 3 consecutive fiscal years.",
    ),
    "unilever": CompanyMeta(
        slug="unilever",
        name="Unilever PLC",
        outcome=Outcome.HEALTHY,
        sector="Consumer goods",
        collapse_year=None,
        notes="Any recent 3 consecutive fiscal years.",
    ),
}


def failed_companies() -> list[CompanyMeta]:
    return [c for c in COMPANIES.values() if c.outcome == Outcome.FAILED]


def healthy_companies() -> list[CompanyMeta]:
    return [c for c in COMPANIES.values() if c.outcome == Outcome.HEALTHY]
