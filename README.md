# SolvencyScan

A financial **distress** analysis tool — separate question from fraud
detection. It checks whether 4 companies that later collapsed (Carillion,
Thomas Cook, Wirecard, Enron) showed genuine warning signs — liquidity
strain, excessive leverage, weak coverage — in their reported numbers over
the 3 years before failure, against 4 healthy comparators (Apple, Walmart,
Microsoft, Unilever). All 8 companies are loaded with real, sourced data.

## Stack

Python 3.12, Streamlit, Plotly. The core dashboard (8 pre-loaded companies,
ratio engine, Altman Z'', narrative summaries) has **no AI/API dependency**
-- it's a deterministic ratio-and-Z-score engine. Only the ad-hoc "upload
any annual report PDF" feature calls Claude, and degrades to a clear
message (not a crash) with no `ANTHROPIC_API_KEY` set.

**Always use the project venv**, not system Python:

```bash
.venv/bin/streamlit run app.py
```

## Project layout

```
corporatefailurelab/
  models.py                # RawYear / CompanyFinancials / YearMetrics dataclasses
  companies.py               # registry of the 8 companies (outcome, sector, collapse year)
  ratios.py                   # liquidity / profitability / leverage / efficiency / cash-flow-quality calculators
  altman.py                    # Altman Z''-Score (non-manufacturing variant) + zone cutoffs
  thresholds.py                 # red/orange/green bands per metric
  validation.py                  # confusion matrix (TP/FN/FP/TN) across the 8 companies
  narrative.py                    # deterministic plain-English per-company summary
  data_loader.py                   # loads data/raw/*.json, computes metrics
  config.py                         # settings for the optional AI upload feature (.env)
  extraction/                        # PDF-upload feature (Claude-powered, optional)
    pdf_reader.py                     #   pdfplumber text extraction
    llm.py                             #   Anthropic client wrapper
    extractor.py                        #   prompt + RawYear-shaped parsing/validation
data/
  sources/                  # drop annual report PDFs here (gitignored)
  raw/<slug>.json            # structured financial line items per company
scripts/
  import_excel.py             # re-runnable: Data Entry tab of a workbook -> data/raw/*.json
app.py                      # Streamlit dashboard (3 views: company / validation / upload)
tests/
```

## Metrics computed, every company, every year

- **Liquidity**: current ratio, quick ratio
- **Profitability**: gross margin, operating margin, net margin, ROA, ROE
- **Leverage**: debt-to-equity, interest coverage
- **Efficiency**: asset turnover, receivables days
- **Cash flow quality**: CFO/net income, free cash flow margin
- **Distress model**: Altman Z''-Score (non-manufacturing variant — chosen
  because the 8 companies span construction, travel, payments, energy
  trading, retail, tech and consumer goods; see `altman.py` for why)

A metric shows as **n/a** (grey flag) rather than a wrong number whenever
its inputs weren't collected -- see "Known data gap" below.

## Known data gap: inventory (retained earnings resolved)

Retained earnings was added via a "Retained Earnings" sheet in the
data-collection workbook -- Altman Z'' and the Validation/confusion-matrix
view are now computed for all 8 companies. `inventory` still isn't
collected, so **quick ratio remains n/a for all 8 companies**; everything
else is computed from real, sourced figures.

Retained earnings itself isn't uniformly first-party-sourced -- three
different data-quality situations exist, and each is surfaced as an
explicit note in the dashboard next to that company's Altman Z'' chart
(not just here):

- **Carillion, Thomas Cook, Wirecard**: the true retained-earnings sub-line
  wasn't separately extractable, so total shareholders' equity is used as a
  proxy. This makes their Z''-Scores slightly **optimistic** relative to
  the true figure (equity also includes share capital/premium/other
  reserves, so it typically exceeds retained earnings).
- **Apple**: retained earnings is negative (an accumulated deficit) in all
  3 years -- share buybacks have exceeded cumulative net income. This is a
  normal capital-return pattern for a mature, cash-rich company, not a
  distress signal, and the dashboard says so explicitly.
- **Microsoft FY2024**: a calculated estimate (opening balance + net income
  - dividends - buybacks), not read directly off a published balance
  sheet like Microsoft's other two years.

To close the remaining inventory gap: add an `Inventory` column to the
workbook and re-run `scripts/import_excel.py`, or hand-edit
`data/raw/<slug>.json` directly. The **PDF upload feature** (below) asks
for the full schema including inventory on every fresh extraction, so it
doesn't have this gap for newly-uploaded companies.

## Validation

The "Validation" view builds a confusion matrix: of the 4 failed companies,
how many did the Z''-Score flag as distress before collapse (true
positives) vs miss (false negatives)? Of the 4 healthy companies, how many
were wrongly flagged (false positives) vs correctly left alone (true
negatives)? Computed two ways — final year only (strict) and any of the 3
years (lenient) — see `validation.py`. Companies whose Z'' can't be
computed are excluded from the matrix and listed separately, not silently
counted as negatives.

## Narrative summaries

Each company page has a "Summary" paragraph, generated deterministically
(no AI call) from that company's own computed metrics -- it quotes real
numbers and names which fiscal years they moved between, and calls out
threshold crossings. See `narrative.py`.

## Upload a PDF (optional, AI-powered)

The "Upload a PDF" view lets you run any annual report through the same
ratio engine and dashboard as the 8 pre-loaded companies. Requires
`ANTHROPIC_API_KEY` in a `.env` file (see `.env.example`) -- without it, the
view shows a clear message rather than failing silently. Extracted figures
are shown in an expander for verification before you trust them.

## Adding / updating data

Two paths:

1. **Workbook import** (used for the 8 pre-loaded companies): fill in the
   `Data Entry` tab of a data-collection workbook per `DATA_SCHEMA.md`, then
   run `.venv/bin/python scripts/import_excel.py /path/to/workbook.xlsx`.
   Re-running is safe -- it overwrites `data/raw/*.json` from the workbook
   each time, resolves duplicate rows (preferring `Verified: Y`), and
   prints a report of unverified rows and any conflicts.
2. **Direct JSON edit**: hand-edit `data/raw/<slug>.json` following the
   `RawYear` schema in `models.py`. The dashboard picks up any company as
   soon as its JSON has at least one populated year.

## Tests

```bash
.venv/bin/pytest
```
