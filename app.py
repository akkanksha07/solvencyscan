"""SolvencyScan -- financial distress analysis dashboard.

Tests whether 4 companies that later failed (Carillion, Thomas Cook,
Wirecard, Enron) showed genuine financial warning signs -- liquidity,
leverage, coverage, cash-flow-quality, Altman Z''-Score -- in the 3 years
before they collapsed, versus 4 healthy comparators (Apple, Walmart,
Microsoft, Unilever). This is a DISTRESS-signal check, not a fraud check:
it asks whether the numbers as reported already pointed to trouble, not
whether the numbers were fabricated.
"""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from corporatefailurelab.altman import DISTRESS_CUTOFF, SAFE_CUTOFF
from corporatefailurelab.companies import COMPANIES, Outcome
from corporatefailurelab.data_loader import (
    available_companies,
    is_populated,
    load_company_metrics,
)
from corporatefailurelab.narrative import generate_narrative
from corporatefailurelab.thresholds import ALTMAN_ZONE_FLAG, BANDS, GREEN, GREY, ORANGE, RED
from corporatefailurelab.validation import build_confusion_matrix

st.set_page_config(page_title="SolvencyScan", layout="wide")

# ---------------------------------------------------------------------------
# Palette. Risk/status colours are semantic and reused everywhere a company's
# state is shown (chart bands, markers, flag dots, note boxes) -- crimson
# always means distress, amber always means grey-zone/caution, emerald
# always means safe, regardless of which widget is drawing it. These are
# fixed and deliberately NOT reused for the accent below, even though both
# land in the amber/gold family, so a heading is never mistaken for a
# caution flag: the accent is a brighter, more saturated gold than the
# muted risk-amber, and only ever appears on text/chrome, never on a data
# point. Structural colours (surfaces, text, the gold accent) never carry
# risk meaning.
# ---------------------------------------------------------------------------
BG_MAIN = "#0A0A0A"
BG_SIDEBAR = "#0d0d0d"
BG_CARD = "#111111"
BORDER_SUBTLE = "#262626"

TEXT_PRIMARY = "#ececec"
TEXT_MUTED = "#9a9a9a"

ACCENT = "#FFB800"    # vivid amber-gold -- headers, title, sidebar highlights
NEUTRAL = "#5a5a5a"   # neutral grey -- chart connector lines, neutral note borders

FLAG_COLOR_HEX = {
    RED: "#c8384f",      # crimson -- distress
    ORANGE: "#e0a52e",   # amber -- grey-zone / caution
    GREEN: "#1fbf7a",    # emerald -- safe / healthy
    GREY: "#7a8291",     # neutral slate -- insufficient data
}

st.markdown(
    f"""
    <style>
    h1, h2, h3 {{
        color: {ACCENT} !important;
        font-weight: 700 !important;
        letter-spacing: -0.01em;
    }}
    hr {{
        border-color: {BORDER_SUBTLE} !important;
    }}
    [data-testid="stSidebar"] {{
        border-right: 1px solid {BORDER_SUBTLE};
    }}
    [data-testid="stMetricValue"] {{
        color: {TEXT_PRIMARY};
    }}
    [data-testid="stExpander"] {{
        border: 1px solid {BORDER_SUBTLE} !important;
        border-radius: 8px !important;
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

METRIC_GROUPS: list[tuple[str, list[tuple[str, str, str]]]] = [
    # (group title, [(metric key, display label, value format)])
    ("Liquidity", [
        ("current_ratio", "Current ratio", "x"),
        ("quick_ratio", "Quick ratio", "x"),
    ]),
    ("Profitability", [
        ("gross_margin", "Gross margin", "%"),
        ("operating_margin", "Operating margin", "%"),
        ("net_margin", "Net margin", "%"),
        ("roa", "Return on assets", "%"),
        ("roe", "Return on equity", "%"),
    ]),
    ("Leverage", [
        ("debt_to_equity", "Debt-to-equity", "x"),
        ("interest_coverage", "Interest coverage", "x"),
    ]),
    ("Efficiency", [
        ("asset_turnover", "Asset turnover", "x"),
        ("receivables_days", "Receivables days", "days"),
    ]),
    ("Cash flow quality", [
        ("cfo_to_net_income", "CFO / net income", "x"),
        ("fcf_margin", "Free cash flow margin", "%"),
    ]),
]

_NOTE_STYLE = {
    "info": (NEUTRAL, NEUTRAL, "ℹ"),              # neutral grey -- disclosure, distinct from the amber warning box
    "success": (FLAG_COLOR_HEX[GREEN], FLAG_COLOR_HEX[GREEN], "✓"),
    "warning": (FLAG_COLOR_HEX[ORANGE], FLAG_COLOR_HEX[ORANGE], "⚠"),
    "error": (FLAG_COLOR_HEX[RED], FLAG_COLOR_HEX[RED], "✕"),
}


def render_note(text: str, kind: str = "info") -> None:
    """Palette-matched replacement for st.info/warning/success/error, so
    note boxes use the same crimson/amber/emerald/neutral system as the
    charts and flags rather than Streamlit's unrelated default blue/yellow/green."""
    border, tint, icon = _NOTE_STYLE[kind]
    st.markdown(
        f'<div style="border-left: 4px solid {border}; background: {tint}1f; '
        f'padding: 0.7rem 1rem; border-radius: 6px; margin: 0.5rem 0 1rem 0; '
        f'color: {TEXT_PRIMARY}; font-size: 0.95rem; line-height: 1.5;">'
        f'{icon}&ensp;{text}</div>',
        unsafe_allow_html=True,
    )


def flag_dot(key: str) -> str:
    """Inline coloured dot matching the exact palette hex -- used instead of
    platform emoji circles, whose colours are fixed by the OS and can't be
    made to match crimson/amber/emerald."""
    return f'<span style="color:{FLAG_COLOR_HEX[key]}; font-size:1.05em;">●</span>'


def stat_tile(label: str, value: str, color: str, help_text: str = "") -> None:
    """Small coloured stat card -- used for the confusion-matrix counts so
    the number itself is crimson (missed/wrongly-flagged) or emerald
    (correct), not just the surrounding chrome."""
    help_html = f'<div style="font-size:0.72rem; color:{TEXT_MUTED}; margin-top:0.2rem;">{help_text}</div>' if help_text else ""
    st.markdown(
        f'<div style="background:{BG_CARD}; border:1px solid {BORDER_SUBTLE}; '
        f'border-top: 3px solid {color}; border-radius:8px; padding:0.9rem 1rem; margin-bottom:0.5rem;">'
        f'<div style="font-size:0.78rem; color:{TEXT_MUTED}; text-transform:uppercase; letter-spacing:0.04em;">{label}</div>'
        f'<div style="font-size:1.9rem; font-weight:700; color:{color};">{value}</div>'
        f'{help_html}</div>',
        unsafe_allow_html=True,
    )


def _is_num(v: float | None) -> bool:
    """False for None, +/-inf, and NaN -- the values a chart can't place on an axis."""
    return v is not None and v == v and v not in (float("inf"), float("-inf"))


def fmt(value: float, kind: str) -> str:
    if value != value:  # NaN
        return "n/a"
    if value == float("inf"):
        return "∞"
    if kind == "%":
        return f"{value * 100:.1f}%"
    if kind == "days":
        return f"{value:.0f}d"
    return f"{value:.2f}x"


def _base_layout(fig: go.Figure, height: int, title: str = "") -> None:
    fig.update_layout(
        title=title, height=height, margin=dict(l=40, r=20, t=40 if title else 20, b=30),
        showlegend=False, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_MUTED, size=12),
        title_font=dict(color=TEXT_PRIMARY, size=13),
        xaxis=dict(gridcolor=BORDER_SUBTLE, zerolinecolor=BORDER_SUBTLE, color=TEXT_MUTED),
        yaxis=dict(gridcolor=BORDER_SUBTLE, zerolinecolor=BORDER_SUBTLE, color=TEXT_MUTED),
        hoverlabel=dict(bgcolor=BG_CARD, bordercolor=BORDER_SUBTLE, font=dict(color=TEXT_PRIMARY)),
    )


def metric_chart(years: list[str], values: list[float], label: str, kind: str, metric_key: str) -> go.Figure:
    band = BANDS.get(metric_key)
    fig = go.Figure()

    if band is not None:
        finite_vals = [v for v in values if _is_num(v)]
        lo = min(finite_vals + [band.red_cutoff, band.orange_cutoff])
        hi = max(finite_vals + [band.red_cutoff, band.orange_cutoff])
        pad = (hi - lo) * 0.15 or abs(hi) * 0.15 or 1
        y_min, y_max = lo - pad, hi + pad

        if band.higher_is_better:
            fig.add_hrect(y0=y_min, y1=band.red_cutoff, fillcolor=FLAG_COLOR_HEX[RED], opacity=0.16, line_width=0)
            fig.add_hrect(y0=band.red_cutoff, y1=band.orange_cutoff, fillcolor=FLAG_COLOR_HEX[ORANGE], opacity=0.16, line_width=0)
            fig.add_hrect(y0=band.orange_cutoff, y1=y_max, fillcolor=FLAG_COLOR_HEX[GREEN], opacity=0.16, line_width=0)
        else:
            fig.add_hrect(y0=band.red_cutoff, y1=y_max, fillcolor=FLAG_COLOR_HEX[RED], opacity=0.16, line_width=0)
            fig.add_hrect(y0=band.orange_cutoff, y1=band.red_cutoff, fillcolor=FLAG_COLOR_HEX[ORANGE], opacity=0.16, line_width=0)
            fig.add_hrect(y0=y_min, y1=band.orange_cutoff, fillcolor=FLAG_COLOR_HEX[GREEN], opacity=0.16, line_width=0)
        fig.update_yaxes(range=[y_min, y_max])

    plot_values = [v if _is_num(v) else None for v in values]
    marker_colors = [FLAG_COLOR_HEX[band.flag(v)] if band and v is not None else FLAG_COLOR_HEX[GREY] for v in plot_values]

    fig.add_trace(go.Scatter(
        x=years, y=plot_values, mode="lines+markers",
        marker=dict(size=12, color=marker_colors, line=dict(width=1.5, color=BG_MAIN)),
        line=dict(color=NEUTRAL, width=2),
        hovertemplate="%{x}: %{y:.3f}<extra></extra>",
    ))
    _base_layout(fig, height=260, title=label)
    return fig


def render_metrics_body(name: str, years_metrics: list) -> None:
    """Shared body (Summary / Altman Z'' / metric groups) for both a
    pre-loaded company and an ad-hoc PDF upload."""
    with st.container(border=True):
        st.subheader("Summary")
        st.markdown(generate_narrative(name, years_metrics))

    fy = [y.fiscal_year for y in years_metrics]
    latest = years_metrics[-1]

    with st.container(border=True):
        st.subheader("Altman Z''-Score (distress model)")
        known_years = [y for y in years_metrics if y.altman_zone != "unknown"]
        if not known_years:
            render_note(
                "Distress-model score unavailable for every analysed year: retained "
                "earnings (needed for the X2 term) wasn't part of the collected data "
                "for this company. All other ratios below are unaffected.",
                kind="warning",
            )
        else:
            z_values = [y.altman_z if y.altman_zone != "unknown" else None for y in years_metrics]
            zone_colors = [FLAG_COLOR_HEX[ALTMAN_ZONE_FLAG[y.altman_zone]] for y in years_metrics]
            known_z = [y.altman_z for y in known_years]
            zfig = go.Figure()
            ymin = min(known_z + [DISTRESS_CUTOFF]) - 1
            ymax = max(known_z + [SAFE_CUTOFF]) + 1
            zfig.add_hrect(y0=ymin, y1=DISTRESS_CUTOFF, fillcolor=FLAG_COLOR_HEX[RED], opacity=0.16, line_width=0)
            zfig.add_hrect(y0=DISTRESS_CUTOFF, y1=SAFE_CUTOFF, fillcolor=FLAG_COLOR_HEX[ORANGE], opacity=0.16, line_width=0)
            zfig.add_hrect(y0=SAFE_CUTOFF, y1=ymax, fillcolor=FLAG_COLOR_HEX[GREEN], opacity=0.16, line_width=0)
            zfig.add_trace(go.Scatter(
                x=fy, y=z_values, mode="lines+markers+text",
                text=[f"{v:.2f}" if v is not None else "n/a" for v in z_values], textposition="top center",
                textfont=dict(color=TEXT_PRIMARY, size=12),
                marker=dict(size=14, color=zone_colors, line=dict(width=1.5, color=BG_MAIN)),
                line=dict(color=NEUTRAL, width=2),
            ))
            _base_layout(zfig, height=300)
            zfig.update_yaxes(range=[ymin, ymax], title="Z''")
            st.plotly_chart(zfig, use_container_width=True, theme=None)
            if latest.altman_zone == "unknown":
                st.markdown(
                    f"Latest ({latest.fiscal_year}): {flag_dot(GREY)} score unavailable "
                    f"(retained earnings not collected for this year).",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"Latest ({latest.fiscal_year}): {flag_dot(ALTMAN_ZONE_FLAG[latest.altman_zone])} "
                    f"**{latest.altman_zone.upper()}** zone (Z''={latest.altman_z:.2f}). "
                    f"Distress < {DISTRESS_CUTOFF}, Grey {DISTRESS_CUTOFF}-{SAFE_CUTOFF}, Safe > {SAFE_CUTOFF}.",
                    unsafe_allow_html=True,
                )

        notes_to_years: dict[str, list[str]] = {}
        for y in years_metrics:
            if y.retained_earnings_note:
                notes_to_years.setdefault(y.retained_earnings_note, []).append(y.fiscal_year)
        for note, note_years in notes_to_years.items():
            render_note(f"<b>Retained earnings data quality note</b> ({', '.join(note_years)}): {note}", kind="info")

    for group_title, metrics in METRIC_GROUPS:
        with st.container(border=True):
            st.subheader(group_title)
            cols = st.columns(len(metrics))
            for col, (key, label, kind) in zip(cols, metrics):
                values = [getattr(y, key) for y in years_metrics]
                with col:
                    st.plotly_chart(metric_chart(fy, values, label, kind, key), use_container_width=True, theme=None)
                    latest_val = getattr(latest, key)
                    band = BANDS.get(key)
                    if not _is_num(latest_val):
                        flag = GREY
                    elif band:
                        flag = band.flag(latest_val)
                    else:
                        flag = ORANGE
                    st.markdown(f"{flag_dot(flag)} Latest: {fmt(latest_val, kind)}", unsafe_allow_html=True)


def render_company_view() -> None:
    populated = available_companies()
    if not populated:
        render_note(
            "No company data yet. Drop the annual-report figures into "
            "<code>data/raw/&lt;company_slug&gt;.json</code> (see <code>DATA_SCHEMA.md</code>), then reload.",
            kind="info",
        )
        st.subheader("Companies awaiting data")
        cols = st.columns(4)
        for i, (slug, meta) in enumerate(COMPANIES.items()):
            with cols[i % 4]:
                tag = "FAILED" if meta.outcome == Outcome.FAILED else "healthy"
                st.markdown(f"**{meta.name}**  \n`{slug}.json` -- {tag}")
        return

    labels = {m.slug: f"{m.name} ({'failed' if m.outcome == Outcome.FAILED else 'healthy'})" for m in populated}
    slug = st.sidebar.selectbox("Company", options=[m.slug for m in populated], format_func=lambda s: labels[s])
    meta = COMPANIES[slug]
    years_metrics = load_company_metrics(slug)

    st.title(meta.name)
    sub = f"{meta.sector} · {'Failed ' + str(meta.collapse_year) if meta.collapse_year else 'Healthy comparator'}"
    st.caption(sub)
    if meta.notes:
        st.caption(meta.notes)

    render_metrics_body(meta.name, years_metrics)


def render_upload_view() -> None:
    from corporatefailurelab.data_loader import compute_year_metrics
    from corporatefailurelab.extraction.extractor import extract_years
    from corporatefailurelab.extraction.llm import LLMError
    from corporatefailurelab.extraction.pdf_reader import read_pdf_bytes

    st.title("Upload a company's annual report")
    st.caption(
        "Runs any uploaded PDF through the same ratio engine, Altman Z'', and "
        "summary as the 8 pre-loaded companies. Uses Claude to read the PDF -- "
        "the 8 pre-loaded companies and the rest of the app work without this."
    )

    uploaded = st.file_uploader("Annual report / 10-K (PDF)", type=["pdf"])
    if uploaded is None:
        render_note("Upload a PDF to extract its financials.", kind="info")
        return

    if st.button("Extract financials", type="primary"):
        with st.spinner("Reading PDF and extracting financials..."):
            try:
                content = read_pdf_bytes(uploaded.getvalue())
                extracted = extract_years(content.financial_text)
            except LLMError as e:
                render_note(str(e), kind="error")
                return
            except Exception as e:
                render_note(f"Extraction failed: {e}", kind="error")
                return
        st.session_state["upload_extracted"] = extracted

    extracted = st.session_state.get("upload_extracted")
    if not extracted:
        return

    all_warnings = [w for e in extracted for w in e.warnings]
    if all_warnings:
        with st.expander(f"⚠ {len(all_warnings)} extraction note(s) -- review before trusting the numbers", expanded=True):
            for w in all_warnings:
                st.markdown(f"- {w}")

    ok_years = [e for e in extracted if e.raw_year is not None]
    if not ok_years:
        render_note("No usable fiscal year could be extracted from this PDF.", kind="error")
        return

    company_name = ok_years[0].company_name
    render_note(f"Extracted {len(ok_years)} fiscal year(s) for <b>{company_name}</b> ({ok_years[0].currency}).", kind="success")

    years_metrics = [compute_year_metrics(e.raw_year) for e in sorted(ok_years, key=lambda e: e.raw_year.fiscal_year)]
    render_metrics_body(company_name, years_metrics)

    with st.expander("Extracted source figures (for verification)"):
        for e in ok_years:
            st.json({k: getattr(e.raw_year, k) for k in (
                "fiscal_year", "total_assets", "total_liabilities", "total_equity",
                "current_assets", "current_liabilities", "receivables", "inventory",
                "retained_earnings", "revenue", "cogs", "operating_income",
                "interest_expense", "net_income", "cfo", "capex", "source",
            )})


def render_validation_view() -> None:
    st.title("Validation: would the warning system have caught them?")
    st.caption(
        "Confusion matrix: for the 4 failed companies, was the Altman Z'' "
        "score in the DISTRESS zone before collapse? For the 4 healthy "
        "companies, was it wrongly flagged as distress (false positive)?"
    )

    rule = st.radio(
        "Flagging rule",
        options=["final_year", "any_year"],
        format_func=lambda r: "Final year only (strict)" if r == "final_year" else "Any of the 3 years (lenient)",
        horizontal=True,
    )
    cm = build_confusion_matrix(rule=rule)

    total_populated = sum(1 for slug in COMPANIES if is_populated(slug))
    if total_populated == 0:
        render_note("No company data yet -- populate `data/raw/*.json` first.", kind="info")
        return

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_tile("True positives", str(len(cm.true_positives)), FLAG_COLOR_HEX[GREEN], "Failed companies correctly flagged distress")
    with c2:
        stat_tile("False negatives", str(len(cm.false_negatives)), FLAG_COLOR_HEX[RED], "Failed companies NOT flagged (missed)")
    with c3:
        stat_tile("False positives", str(len(cm.false_positives)), FLAG_COLOR_HEX[RED], "Healthy companies wrongly flagged distress")
    with c4:
        stat_tile("True negatives", str(len(cm.true_negatives)), FLAG_COLOR_HEX[GREEN], "Healthy companies correctly not flagged")

    sens = cm.sensitivity
    spec = cm.specificity
    c5, c6 = st.columns(2)
    with c5:
        stat_tile("Sensitivity (recall on failures)", f"{sens*100:.0f}%" if sens is not None else "n/a", ACCENT)
    with c6:
        stat_tile("Specificity (correct on healthy)", f"{spec*100:.0f}%" if spec is not None else "n/a", ACCENT)

    if cm.excluded:
        names = ", ".join(p.name for p in cm.excluded)
        render_note(
            f"{len(cm.excluded)} of {len(cm.excluded) + len(cm.true_positives) + len(cm.false_negatives) + len(cm.false_positives) + len(cm.true_negatives)} "
            f"companies excluded from the matrix above (not counted as either a positive or negative "
            f"prediction): their Altman Z'' couldn't be computed under this rule because retained "
            f"earnings wasn't collected for the relevant year(s). Affected: {names}. Sensitivity/"
            f"specificity above are computed only over the remaining companies, if any.",
            kind="warning",
        )

    st.subheader("Detail")
    rows = []
    for group_name, group in [
        ("True positive", cm.true_positives), ("False negative", cm.false_negatives),
        ("False positive", cm.false_positives), ("True negative", cm.true_negatives),
        ("Excluded (Z'' unavailable)", cm.excluded),
    ]:
        for p in group:
            zone_path = " → ".join(y.altman_zone for y in p.years)
            final_z = p.years[-1].altman_z
            rows.append({
                "Result": group_name,
                "Company": p.name,
                "Outcome": p.outcome.value,
                "Z'' zone path (oldest→latest)": zone_path,
                "Final-year Z''": f"{final_z:.2f}" if final_z == final_z else "n/a",
            })
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
    else:
        render_note("No companies with data yet.", kind="info")


st.sidebar.title("SolvencyScan")
view = st.sidebar.radio(
    "View", ["Company analysis", "Validation / confusion matrix", "Upload a PDF"]
)
st.sidebar.markdown("---")
st.sidebar.caption(
    "Financial distress analysis, not fraud detection: tests whether ratios "
    "and Altman Z'' showed genuine warning signs before failure."
)
st.sidebar.markdown(
    f'<div style="display:flex; gap:0.4rem; align-items:center; font-size:0.75rem; color:{TEXT_MUTED}; margin-top:1rem;">'
    f'{flag_dot(RED)}&nbsp;Distress&emsp;{flag_dot(ORANGE)}&nbsp;Grey zone&emsp;{flag_dot(GREEN)}&nbsp;Safe&emsp;{flag_dot(GREY)}&nbsp;No data'
    f'</div>',
    unsafe_allow_html=True,
)

if view == "Company analysis":
    render_company_view()
elif view == "Validation / confusion matrix":
    render_validation_view()
else:
    render_upload_view()
