# Data schema

Each company's data lives at `data/raw/<slug>.json`, populated by
`scripts/import_excel.py` from a data-collection workbook's two tabs:
`Data Entry` (core financials) and `Retained Earnings` (optional, for the
Altman Z''-Score). You can also hand-edit `data/raw/<slug>.json` directly,
or use the "Upload a PDF" view for a one-off company outside the 8.

## Slugs and analysed years

| slug | company | outcome | years used | note |
|---|---|---|---|---|
| `carillion` | Carillion plc | failed (2018) | FY2014-2016 | no FY2017 report was ever published |
| `thomas_cook` | Thomas Cook Group plc | failed (2019) | FY2016-2018 | |
| `wirecard` | Wirecard AG | failed (2020) | FY2016-2018 | FY2019 excluded -- EY refused to sign off |
| `enron` | Enron Corp. | failed (2001) | FY1998-2000 | as-filed, pre-restatement |
| `apple` | Apple Inc. | healthy | FY2022-2024 | |
| `walmart` | Walmart Inc. | healthy | FY2022-2024 | |
| `microsoft` | Microsoft Corp. | healthy | FY2022-2024 | |
| `unilever` | Unilever PLC | healthy | FY2022-2024 | |

## `Data Entry` tab columns

One row per (company, fiscal year) -- 24 rows for the 8 companies above.
Columns: `Company`, `Status`, `Fiscal Year`, `Currency`, `Revenue`, `EBIT`,
`Net Income`, `Total Assets`, `Current Assets`, `Current Liabilities`,
`Total Debt`, `Equity`, `Operating Cash Flow`, `Capex`, `Interest Expense`,
`Receivables`, `COGS`, `Source URL`, `Source Page / Note`, `Verified (Y/N)`.

Mapping notes:
- `total_liabilities` isn't a column -- the importer derives it as
  `Total Assets - Equity` (more robust than `Total Debt`, which several
  companies' source notes say excludes lease liabilities).
- `COGS` may be blank for companies that don't disclose cost of sales
  separately (flagged in the workbook's Data Dictionary tab) -- gross
  margin comes out as n/a for those rows.
- `inventory` and `cash_and_equivalents` aren't columns at all yet --
  quick ratio is n/a for every company until an `Inventory` column is added.
- Duplicate (company, year) rows are resolved by preferring `Verified: Y`;
  an unresolved conflict causes both rows to be skipped with a warning.

## `Retained Earnings` tab columns (optional)

`Company`, `Status`, `Fiscal Year`, `Currency`, `Retained Earnings`,
`Source / Notes`, `Verified (Y/N)`. Matched to `Data Entry` rows by
(company, fiscal year). If this sheet is absent, `retained_earnings` stays
null and Altman Z'' comes out as n/a (same for quick ratio/inventory).

The `Verified` column drives a `retained_earnings_note` that the importer
attaches to the row and the dashboard shows verbatim next to that company's
Altman Z'' chart:
- **`PROXY`**: total equity was used as a stand-in for the true
  retained-earnings sub-line -- flagged as making Z'' slightly optimistic.
- Notes text containing **"approx"**: treated as a calculated estimate,
  not a directly-sourced figure.
- **Negative value**: flagged as an accumulated deficit and explained as a
  normal capital-return pattern (buybacks/dividends > cumulative net
  income), not automatically a distress signal.

## `RawYear` JSON shape (what ends up in `data/raw/<slug>.json`)

```json
{
  "fiscal_year": "FY2016",
  "total_assets": 0,
  "total_liabilities": 0,
  "total_equity": 0,
  "current_assets": 0,
  "current_liabilities": 0,
  "receivables": 0,
  "inventory": null,
  "retained_earnings": null,
  "retained_earnings_note": null,
  "cash_and_equivalents": null,
  "revenue": 0,
  "cogs": null,
  "operating_income": 0,
  "interest_expense": 0,
  "net_income": 0,
  "cfo": 0,
  "capex": 0,
  "prior_total_assets": null,
  "prior_total_equity": null,
  "source": "FY2016 Annual Report, p.XX"
}
```

`prior_total_assets`/`prior_total_equity` are chained automatically by the
importer from each company's own earlier analysed year (not a workbook
column), to average ROA/ROE/asset-turnover denominators for the 2nd and
3rd year of each company's window.

## Notes on specific companies

- **Wirecard, Enron**: figures are *as reported* at the time, even where
  later found fabricated (Wirecard) or since restated (Enron). This project
  tests whether the reported numbers already showed distress, not whether
  the fraud was detectable -- a different, forensic question.
- Some companies report `operating_income` inclusive/exclusive of certain
  items (impairments, exceptionals) -- see each row's `source` for the
  judgment call made.

## After updating the workbook

```bash
.venv/bin/python scripts/import_excel.py /path/to/workbook.xlsx
```

Re-running is safe: it overwrites `data/raw/*.json` from the workbook every
time and prints a report of duplicate-row resolutions, unverified rows, and
retained-earnings caveats. `app.py` reads `data/raw/*.json` fresh on every
page load -- no other wiring needed, no restart required.
