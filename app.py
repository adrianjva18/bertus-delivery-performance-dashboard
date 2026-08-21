"""
Bertus Delivery Performance Dashboard
--------------------------------------
An interactive Streamlit dashboard analyzing delivery performance for a
physical media wholesale distributor (synthetic data modeled on Bertus
Distributie's real business: vinyl/CD/DVD/merch shipped to independent
stores, retail chains, and online retailers across NL, DE, BE, FR, UK, US).

Run locally with:
    streamlit run app.py

Data cleaning steps performed here (the raw CSV deliberately ships "dirty"):
    - Parse plain string dates into real datetime objects
    - Derive is_late (bool), delay_days (int), and order_month from the
      promised vs actual delivery dates, none of which exist in the raw data
    - Handle the empty delay_reason field for on-time shipments

Analysis choices worth knowing (see README for the full reasoning, including
which techniques were deliberately left out as statistically overreaching at
this sample size -- no control charts, no forecast, no multivariate model):
    - Carrier on-time rates are shown with 95% Wilson confidence intervals,
      because a plain ranked bar chart implies far more precision than
      ~25-33 shipments per carrier actually supports
    - The carrier x destination heatmap annotates shipment counts, so small
      cells are visibly small rather than looking equally trustworthy
    - Delay spread is shown per carrier (box + individual points), not just
      a mean, since the mean hides the tail that actually hurts customers
    - Delay causes use a Pareto (cumulative %) view to answer "how many
      causes must we fix to remove most of the problem"
"""

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st
from plotly.subplots import make_subplots
from statsmodels.stats.proportion import proportion_confint

st.set_page_config(
    page_title="Bertus Delivery Performance",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Design tokens. The Plotly template is matched to the dark Streamlit theme in
# .streamlit/config.toml and applied with theme=None on every chart, because
# Streamlit's own "theme=streamlit" restyling otherwise overrides these.
# ---------------------------------------------------------------------------
BG = "#0E1117"
SURFACE = "#161A22"
GRID = "#252A34"
TEXT = "#E6E6E6"
MUTED = "#8B93A1"
ACCENT = "#4C9AFF"
GOOD = "#3FB98C"
WARN = "#E0A93B"
BAD = "#E5626E"

# One locked carrier -> colour mapping, reused on every chart on every page so
# a carrier is always the same colour everywhere in the app.
CARRIER_COLORS = {
    "PostNL": "#4C9AFF",
    "DHL": "#3FB98C",
    "DPD": "#E0A93B",
    "GLS": "#E5626E",
    "UPS": "#9D7BDB",
}

# Assumed internal service-level target. This is an assumption for the sake of
# the exercise, not a figure from the data -- always labelled as such in the UI.
SLA_TARGET = 85.0

PLOT_CONFIG = {"displayModeBar": False, "responsive": True}

pio.templates["bertus"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT, family="Inter, sans-serif", size=13),
        title=dict(font=dict(color="#FFFFFF", size=15), x=0, xanchor="left"),
        colorway=list(CARRIER_COLORS.values()),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID, showgrid=False),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, zerolinecolor=GRID),
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=-0.2),
        margin=dict(t=60, l=10, r=20, b=40),
        hoverlabel=dict(bgcolor=SURFACE, font_size=12),
    )
)
pio.templates.default = "plotly_dark+bertus"

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---- sidebar as a real left nav ---- */
section[data-testid="stSidebar"] { background-color: #10141B; border-right: 1px solid #252A34; }
.nav-brand { font-size: 1.05rem; font-weight: 700; color: #FFFFFF; letter-spacing: .02em; }
.nav-sub { font-size: .72rem; color: #8B93A1; text-transform: uppercase;
           letter-spacing: .08em; margin-bottom: 1.1rem; }
.side-label { font-size: .7rem; font-weight: 600; color: #8B93A1;
              text-transform: uppercase; letter-spacing: .09em; margin: .2rem 0 .4rem; }

section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 3px; }
/* hide the radio dot so each option reads as a nav row, not a form control */
label[data-testid="stRadioOption"] > div > div > div:first-child { display: none !important; }
label[data-testid="stRadioOption"] {
    padding: 9px 13px; border-radius: 8px; width: 100%; cursor: pointer;
    border-left: 3px solid transparent; transition: background .12s ease;
}
label[data-testid="stRadioOption"]:hover { background: #1A2029; }
label[data-testid="stRadioOption"][data-selected="true"] {
    background: #1B2534; border-left: 3px solid #4C9AFF;
}
label[data-testid="stRadioOption"] p { font-size: .92rem; font-weight: 500; color: #9BA3B1; }
label[data-testid="stRadioOption"][data-selected="true"] p { color: #FFFFFF; font-weight: 600; }

/* ---- KPI cards ---- */
div[data-testid="stMetric"] {
    background-color: #161A22; border: 1px solid #252A34; border-radius: 12px;
    padding: 16px 18px; box-shadow: 0 1px 3px rgba(0,0,0,.4);
}
div[data-testid="stMetricLabel"] {
    font-size: .72rem; font-weight: 600; text-transform: uppercase;
    letter-spacing: .07em; color: #8B93A1;
}
div[data-testid="stMetricValue"] { font-size: 1.75rem; font-weight: 700; color: #FFFFFF; }

/* ---- headings, callouts, chrome ---- */
h1 { font-size: 1.6rem !important; font-weight: 700 !important; letter-spacing: -.01em; }
.page-sub { color: #8B93A1; font-size: .88rem; margin: -.4rem 0 1.2rem; }
.insight {
    background: linear-gradient(90deg, #16202B 0%, #141A22 100%);
    border-left: 3px solid #4C9AFF; border-radius: 8px;
    padding: 14px 18px; margin-bottom: 1.4rem; color: #E6E6E6; font-size: .93rem;
    line-height: 1.55;
}
.readme { color: #8B93A1; font-size: .78rem; margin: -.6rem 0 .9rem; line-height: 1.5; }
#MainMenu, footer, header [data-testid="stToolbar"] { visibility: hidden; }
div.block-container { padding-top: 2.4rem; max-width: 1500px; }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_data():
    df = pd.read_csv("data/bertus_shipments_raw.csv")

    df["order_date"] = pd.to_datetime(df["order_date"])
    df["promised_delivery_date"] = pd.to_datetime(df["promised_delivery_date"])
    df["actual_delivery_date"] = pd.to_datetime(df["actual_delivery_date"])

    df["delay_days"] = (df["actual_delivery_date"] - df["promised_delivery_date"]).dt.days
    df["is_late"] = df["delay_days"] > 0
    df["order_month"] = df["order_date"].dt.to_period("M").astype(str)
    df["delay_reason"] = df["delay_reason"].fillna("On time")

    return df


df = load_data()

# ---------------------------------------------------------------------------
# Left navigation + filters
# ---------------------------------------------------------------------------
PAGES = [
    "Overview",
    "Carrier reliability",
    "Destinations",
    "Delay root cause",
    "Shipment data",
]

with st.sidebar:
    st.markdown(
        '<div class="nav-brand">Bertus Distributie</div>'
        '<div class="nav-sub">Delivery performance</div>',
        unsafe_allow_html=True,
    )
    page = st.radio("Navigation", PAGES, label_visibility="collapsed")

    st.markdown('<div class="side-label">Filters</div>', unsafe_allow_html=True)
    carriers = st.multiselect(
        "Carrier", sorted(df["carrier"].unique()), default=sorted(df["carrier"].unique())
    )
    customer_types = st.multiselect(
        "Customer type",
        sorted(df["customer_type"].unique()),
        default=sorted(df["customer_type"].unique()),
    )
    countries = st.multiselect(
        "Destination country",
        sorted(df["destination_country"].unique()),
        default=sorted(df["destination_country"].unique()),
    )

filtered = df[
    df["carrier"].isin(carriers)
    & df["customer_type"].isin(customer_types)
    & df["destination_country"].isin(countries)
]

if filtered.empty:
    st.title("Bertus Delivery Performance")
    st.warning("No shipments match the current filters. Widen a filter in the left panel.")
    st.stop()

# ---------------------------------------------------------------------------
# Shared aggregates
# ---------------------------------------------------------------------------
total_shipments = len(filtered)
on_time_rate = (1 - filtered["is_late"].mean()) * 100
late_count = int(filtered["is_late"].sum())
avg_delay = filtered.loc[filtered["is_late"], "delay_days"].mean() if late_count else 0.0
total_value = filtered["order_value_eur"].sum()
late_value = filtered.loc[filtered["is_late"], "order_value_eur"].sum()

monthly = (
    filtered.groupby("order_month")
    .agg(
        on_time_rate=("is_late", lambda s: (1 - s.mean()) * 100),
        shipments=("shipment_id", "count"),
        avg_delay=("delay_days", lambda s: s[s > 0].mean() if (s > 0).any() else 0),
        total_value=("order_value_eur", "sum"),
    )
    .sort_index()
)

carrier_stats = (
    filtered.groupby("carrier")
    .agg(shipments=("shipment_id", "count"), late=("is_late", "sum"))
    .assign(on_time_pct=lambda d: (1 - d["late"] / d["shipments"]) * 100)
    .sort_values("on_time_pct", ascending=False)
)


def carrier_ci_table(data):
    """On-time rate per carrier with a 95% Wilson confidence interval."""
    rows = []
    for carrier, g in data.groupby("carrier"):
        n = len(g)
        if not n:
            continue
        on_time_n = int((~g["is_late"]).sum())
        low, high = proportion_confint(on_time_n, n, method="wilson")
        rows.append(
            {
                "carrier": carrier,
                "n": n,
                "rate": on_time_n / n * 100,
                "low": low * 100,
                "high": high * 100,
            }
        )
    return pd.DataFrame(rows).sort_values("rate") if rows else pd.DataFrame()


ci_df = carrier_ci_table(filtered)


def kpi_row():
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Shipments",
        f"{total_shipments:,}",
        chart_data=monthly["shipments"].tolist() if len(monthly) > 1 else None,
        chart_type="area",
    )
    c2.metric(
        "On-time rate",
        f"{on_time_rate:.1f}%",
        delta=f"{on_time_rate - SLA_TARGET:+.1f} pp vs {SLA_TARGET:.0f}% target",
        chart_data=monthly["on_time_rate"].tolist() if len(monthly) > 1 else None,
        chart_type="line",
    )
    c3.metric(
        "Avg delay when late",
        f"{avg_delay:.1f} days",
        delta=f"{late_count} late shipments",
        delta_color="off",
        chart_data=monthly["avg_delay"].tolist() if len(monthly) > 1 else None,
        chart_type="line",
    )
    c4.metric(
        "Order value at risk",
        f"EUR {late_value:,.0f}",
        delta=f"{late_value / total_value * 100:.0f}% of EUR {total_value:,.0f} shipped",
        delta_color="off",
    )


def insight_banner():
    """Narrative 'so what' line: the finding and its caveat, before any chart."""
    bits = [
        f"<b>{on_time_rate:.1f}% of {total_shipments:,} shipments arrived on time</b> "
        f"({on_time_rate - SLA_TARGET:+.1f} pp against the assumed {SLA_TARGET:.0f}% target)."
    ]
    if len(ci_df) >= 2:
        worst = ci_df.iloc[0]
        best = ci_df.iloc[-1]
        overlap = worst["high"] >= best["low"]
        bits.append(
            f"{worst['carrier']} ranks lowest at {worst['rate']:.0f}% and {best['carrier']} highest "
            f"at {best['rate']:.0f}%, but with only {int(worst['n'])} and {int(best['n'])} shipments "
            f"their confidence intervals {'overlap, so that gap is not yet statistically reliable' if overlap else 'do not overlap, so the gap looks real'}."
        )
    if late_count:
        causes = filtered.loc[filtered["is_late"], "delay_reason"].value_counts()
        share = causes.iloc[0] / late_count * 100
        if share >= 40:
            bits.append(
                f"<b>{causes.index[0]}</b> drives {share:.0f}% of late shipments and is the "
                f"clear first lever to pull."
            )
        else:
            bits.append(
                f"No single cause dominates &mdash; the largest, <b>{causes.index[0].lower()}</b>, "
                f"accounts for only {share:.0f}% of late shipments, so there is no quick "
                f"one-fix win here."
            )
    st.markdown(f'<div class="insight">{" ".join(bits)}</div>', unsafe_allow_html=True)


def page_header(title, subtitle):
    st.title(title)
    st.markdown(f'<div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def how_to_read(text):
    st.markdown(f'<div class="readme">{text}</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
if page == "Overview":
    page_header(
        "Delivery performance overview",
        "Synthetic shipment data modelled on a physical-media wholesale distributor. "
        "Built to practise the SLA and delay reporting an operations analyst owns.",
    )
    insight_banner()
    kpi_row()
    st.write("")

    # Slim progress-to-target strip: reads at a glance, unlike a circular dial.
    fig = go.Figure(
        go.Indicator(
            mode="gauge",
            value=on_time_rate,
            gauge={
                "shape": "bullet",
                "axis": {"range": [0, 100], "tickcolor": MUTED, "tickfont": {"size": 11}},
                "bar": {"color": ACCENT, "thickness": 0.62},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 70], "color": "#2A1D24"},
                    {"range": [70, SLA_TARGET], "color": "#2C2718"},
                    {"range": [SLA_TARGET, 100], "color": "#16291F"},
                ],
                "threshold": {
                    "line": {"color": "#FFFFFF", "width": 3},
                    "thickness": 0.95,
                    "value": SLA_TARGET,
                },
            },
            domain={"x": [0.0, 1.0], "y": [0.0, 0.62]},
        )
    )
    fig.update_layout(
        height=112,
        margin=dict(t=42, l=8, r=18, b=6),
        title=(
            f"On-time rate {on_time_rate:.1f}% vs the assumed {SLA_TARGET:.0f}% target "
            f"(white line): short by {SLA_TARGET - on_time_rate:.1f} pp"
            if on_time_rate < SLA_TARGET
            else f"On-time rate {on_time_rate:.1f}% clears the assumed {SLA_TARGET:.0f}% target"
        ),
    )
    st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)

    left, right = st.columns([1.15, 1])

    with left:
        m = monthly.reset_index()
        # Insight-first title: name the movement, not the axes.
        if len(m) >= 2:
            i_max = m["on_time_rate"].idxmax()
            i_min = m["on_time_rate"].idxmin()
            if i_min > i_max:
                swing = m.loc[i_max, "on_time_rate"] - m.loc[i_min, "on_time_rate"]
                title = (
                    f"On-time rate fell {swing:.0f} pp from {m.loc[i_max, 'order_month']} "
                    f"to {m.loc[i_min, 'order_month']}"
                )
            else:
                swing = m.loc[i_max, "on_time_rate"] - m.loc[i_min, "on_time_rate"]
                title = (
                    f"On-time rate recovered {swing:.0f} pp to "
                    f"{m.loc[i_max, 'order_month']}"
                )
        else:
            title = "On-time rate by month"

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=m["order_month"],
                y=m["on_time_rate"],
                mode="lines+markers+text",
                text=[f"{v:.0f}%" for v in m["on_time_rate"]],
                textposition="top center",
                textfont=dict(size=11, color=MUTED),
                line=dict(color=ACCENT, width=3),
                marker=dict(size=9, color=ACCENT),
                hovertemplate="%{x}<br>%{y:.1f}% on time<extra></extra>",
            )
        )
        fig.add_hline(
            y=SLA_TARGET,
            line_dash="dash",
            line_color=MUTED,
            annotation_text=f"{SLA_TARGET:.0f}% target",
            annotation_position="bottom right",
            annotation_font_color=MUTED,
        )
        y_low = max(0, m["on_time_rate"].min() - 18)
        fig.update_layout(
            title=title,
            height=340,
            yaxis=dict(title="On-time rate (%)", showgrid=True, range=[y_low, 100]),
            xaxis=dict(title=None),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)

    with right:
        cs = carrier_stats.reset_index().sort_values("on_time_pct")
        title = "On-time rate by carrier"
        if len(cs) >= 2:
            title = (
                f"{cs.iloc[-1]['carrier']} leads at {cs.iloc[-1]['on_time_pct']:.0f}%, "
                f"{cs.iloc[0]['carrier']} trails at {cs.iloc[0]['on_time_pct']:.0f}%"
            )
        fig = go.Figure(
            go.Bar(
                x=cs["on_time_pct"],
                y=cs["carrier"],
                orientation="h",
                marker_color=[CARRIER_COLORS.get(c, ACCENT) for c in cs["carrier"]],
                text=[f"{v:.0f}%  (n={int(n)})" for v, n in zip(cs["on_time_pct"], cs["shipments"])],
                textposition="outside",
                textfont=dict(size=11, color=TEXT),
                hovertemplate="%{y}: %{x:.1f}% on time<extra></extra>",
            )
        )
        fig.add_vline(x=SLA_TARGET, line_dash="dash", line_color=MUTED)
        fig.update_layout(
            title=title,
            height=340,
            xaxis=dict(title="On-time rate (%)", range=[0, 108]),
            yaxis=dict(title=None),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)
        how_to_read(
            f"Dashed line marks the assumed {SLA_TARGET:.0f}% target. n = shipments behind each bar. "
            "See <b>Carrier reliability</b> for whether these gaps survive their margin of error."
        )

elif page == "Carrier reliability":
    page_header(
        "Carrier reliability",
        "Do the differences between carriers hold up statistically, or are they sample noise?",
    )
    insight_banner()

    if len(ci_df):
        all_overlap = len(ci_df) >= 2 and ci_df.iloc[0]["high"] >= ci_df.iloc[-1]["low"]
        title = (
            "Every carrier's confidence interval overlaps: this ranking is not statistically reliable"
            if all_overlap
            else "On-time rate per carrier, with 95% confidence intervals"
        )

        fig = go.Figure()
        for _, r in ci_df.iterrows():
            colour = CARRIER_COLORS.get(r["carrier"], ACCENT)
            fig.add_trace(
                go.Scatter(
                    x=[r["low"], r["high"]],
                    y=[r["carrier"], r["carrier"]],
                    mode="lines",
                    line=dict(color=colour, width=4),
                    opacity=0.5,
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=[r["rate"]],
                    y=[r["carrier"]],
                    mode="markers",
                    marker=dict(size=15, color=colour, line=dict(color=BG, width=2)),
                    showlegend=False,
                    hovertemplate=(
                        f"{r['carrier']}<br>{r['rate']:.1f}% on time"
                        f"<br>95% CI {r['low']:.0f}-{r['high']:.0f}%"
                        f"<br>n={int(r['n'])} shipments<extra></extra>"
                    ),
                )
            )
            # Value column outside the plotting area, so nothing sits on the data.
            fig.add_annotation(
                xref="paper", x=1.02, xanchor="left",
                y=r["carrier"], yref="y",
                text=(
                    f"<b>{r['rate']:.0f}%</b>"
                    f"<span style='color:{MUTED}'>  ({r['low']:.0f}–{r['high']:.0f}%)"
                    f"  n={int(r['n'])}</span>"
                ),
                showarrow=False, font=dict(size=12, color=TEXT), align="left",
            )
        fig.add_vline(
            x=SLA_TARGET, line_dash="dash", line_color=MUTED,
            annotation_text=f"{SLA_TARGET:.0f}% target",
            annotation_position="top",
            annotation_font=dict(color=MUTED, size=11),
        )
        fig.update_layout(
            title=title,
            height=360,
            xaxis=dict(title="On-time rate (%)", range=[0, 100], showgrid=True),
            yaxis=dict(title=None),
            margin=dict(t=70, l=10, r=210, b=45),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)
        how_to_read(
            "<b>How to read this:</b> the dot is the measured on-time rate; the bar is the range the "
            "true rate plausibly sits in, given how few shipments each carrier has. Where two "
            "carriers' bars overlap, the data cannot yet tell them apart -- so a ranked bar chart "
            "of these same numbers would look far more conclusive than the evidence allows."
        )

    st.write("")
    st.markdown('<div class="side-label">Carrier summary</div>', unsafe_allow_html=True)
    summary = (
        carrier_stats.reset_index()
        .rename(columns={"carrier": "Carrier", "shipments": "Shipments", "late": "Late"})
        .assign(**{"On-time %": lambda d: d["on_time_pct"].round(1)})
        .drop(columns=["on_time_pct"])
    )
    avg_delay_by_carrier = (
        filtered[filtered["is_late"]].groupby("carrier")["delay_days"].mean().round(1)
    )
    summary["Avg days late"] = summary["Carrier"].map(avg_delay_by_carrier).fillna(0)
    value_at_risk = (
        filtered[filtered["is_late"]].groupby("carrier")["order_value_eur"].sum()
    )
    summary["Value at risk"] = summary["Carrier"].map(value_at_risk).fillna(0)

    st.dataframe(
        summary,
        hide_index=True,
        use_container_width=True,
        column_config={
            "On-time %": st.column_config.ProgressColumn(
                "On-time %", format="%.1f%%", min_value=0, max_value=100
            ),
            "Value at risk": st.column_config.NumberColumn("Value at risk", format="EUR %d"),
            "Avg days late": st.column_config.NumberColumn("Avg days late", format="%.1f"),
        },
    )

elif page == "Destinations":
    page_header(
        "Destination performance",
        "Where in the network do shipments actually miss their promised date?",
    )
    insight_banner()

    country_stats = (
        filtered.groupby("destination_country")
        .agg(shipments=("shipment_id", "count"), late=("is_late", "sum"))
        .assign(on_time_pct=lambda d: (1 - d["late"] / d["shipments"]) * 100)
        .sort_values("on_time_pct")
        .reset_index()
    )

    left, right = st.columns([1, 1])
    with left:
        title = "On-time rate by destination"
        if len(country_stats) >= 2:
            title = (
                f"{country_stats.iloc[0]['destination_country']} is the weakest destination "
                f"at {country_stats.iloc[0]['on_time_pct']:.0f}%"
            )
        colours = [
            BAD if v < 70 else WARN if v < SLA_TARGET else GOOD
            for v in country_stats["on_time_pct"]
        ]
        fig = go.Figure(
            go.Bar(
                x=country_stats["on_time_pct"],
                y=country_stats["destination_country"],
                orientation="h",
                marker_color=colours,
                text=[
                    f"{v:.0f}%  (n={int(n)})"
                    for v, n in zip(country_stats["on_time_pct"], country_stats["shipments"])
                ],
                textposition="outside",
                textfont=dict(size=11, color=TEXT),
                hovertemplate="%{y}: %{x:.1f}% on time<extra></extra>",
            )
        )
        fig.add_vline(x=SLA_TARGET, line_dash="dash", line_color=MUTED)
        fig.update_layout(
            title=title,
            height=400,
            xaxis=dict(title="On-time rate (%)", range=[0, 108]),
            yaxis=dict(title=None),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)
        how_to_read(
            f"Green clears the assumed {SLA_TARGET:.0f}% target, amber sits below it, red below 70%."
        )

    with right:
        rate_pivot = filtered.pivot_table(
            index="carrier", columns="destination_country", values="is_late", aggfunc="mean"
        )
        n_pivot = filtered.pivot_table(
            index="carrier", columns="destination_country", values="is_late", aggfunc="count"
        )
        if len(rate_pivot):
            on_time_pivot = (1 - rate_pivot) * 100
            labels = []
            for r in on_time_pivot.index:
                row = []
                for c in on_time_pivot.columns:
                    n = n_pivot.loc[r, c] if c in n_pivot.columns else None
                    rate = on_time_pivot.loc[r, c]
                    row.append(
                        f"{rate:.0f}%<br><span style='font-size:9px'>n={int(n)}</span>"
                        if pd.notna(rate) and pd.notna(n)
                        else "--"
                    )
                labels.append(row)
            fig = go.Figure(
                go.Heatmap(
                    z=on_time_pivot.values,
                    x=on_time_pivot.columns,
                    y=on_time_pivot.index,
                    text=labels,
                    texttemplate="%{text}",
                    textfont=dict(size=11),
                    colorscale=[[0, BAD], [0.5, WARN], [1, GOOD]],
                    zmin=0,
                    zmax=100,
                    xgap=3,
                    ygap=3,
                    colorbar=dict(title="On-time %", thickness=12),
                    hovertemplate="%{y} to %{x}<br>%{z:.0f}% on time<extra></extra>",
                )
            )
            fig.update_layout(
                title="Carrier and destination combinations",
                height=400,
                xaxis=dict(showgrid=False),
                yaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)
            how_to_read(
                "Each cell shows the on-time rate and the shipment count behind it. Many cells rest "
                "on a handful of shipments, so treat single-cell extremes as a prompt to look "
                "closer, not as a finding."
            )

elif page == "Delay root cause":
    page_header(
        "Delay root cause",
        "Which causes matter most, and how bad is a delay when it happens?",
    )
    insight_banner()

    late = filtered[filtered["is_late"]]
    if late.empty:
        st.info("No late shipments on the current filter, so there is nothing to diagnose.")
        st.stop()

    left, right = st.columns([1, 1])

    with left:
        counts = late["delay_reason"].value_counts()
        cum_pct = counts.cumsum() / counts.sum() * 100
        n_to_80 = int((cum_pct < 80).sum() + 1)
        wrapped = [c.replace(" ", "<br>") for c in counts.index]

        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=wrapped,
                y=counts.values,
                marker_color=BAD,
                text=counts.values,
                textposition="outside",
                textfont=dict(size=11, color=TEXT),
                name="Late shipments",
                hovertemplate="%{y} late shipments<extra></extra>",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=wrapped,
                y=cum_pct.values,
                mode="lines+markers",
                line=dict(color="#FFFFFF", width=2),
                marker=dict(size=7),
                name="Cumulative %",
                hovertemplate="%{y:.0f}% of all delays<extra></extra>",
            ),
            secondary_y=True,
        )
        fig.add_hline(y=80, line_dash="dash", line_color=MUTED, secondary_y=True)
        # An honest Pareto read: if you need most categories to reach 80%, there is no
        # dominant cause, and saying so is more useful than forcing an 80/20 narrative.
        top_share = counts.iloc[0] / counts.sum() * 100
        if n_to_80 >= max(2, len(counts) - 1):
            pareto_title = (
                f"No dominant cause: delays spread evenly, needing {n_to_80} of "
                f"{len(counts)} causes to cover 80%"
            )
        else:
            pareto_title = (
                f"Fixing the top {n_to_80} causes would address ~80% of late shipments "
                f"({top_share:.0f}% sit with {counts.index[0].lower()} alone)"
            )
        fig.update_layout(
            title=pareto_title,
            height=400,
            showlegend=False,
        )
        fig.update_yaxes(title_text="Late shipments", secondary_y=False,
                          range=[0, counts.max() * 1.25], showgrid=True)
        fig.update_yaxes(title_text="Cumulative %", secondary_y=True, range=[0, 108],
                          showgrid=False)
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)
        how_to_read(
            "Bars count late shipments per cause (largest first); the white line is the running "
            "share of all delays. Where it crosses the dashed 80% line tells you how many causes "
            "you must fix to remove most of the problem."
        )

    with right:
        order = late.groupby("carrier")["delay_days"].median().sort_values().index.tolist()
        fig = go.Figure()
        for carrier in order:
            sub = late[late["carrier"] == carrier]
            fig.add_trace(
                go.Box(
                    x=sub["delay_days"],
                    name=carrier,
                    orientation="h",
                    boxpoints="all",
                    jitter=0.45,
                    pointpos=0,
                    marker=dict(color=CARRIER_COLORS.get(carrier, ACCENT), size=6),
                    line=dict(color=CARRIER_COLORS.get(carrier, ACCENT)),
                    fillcolor="rgba(0,0,0,0)",
                    hovertemplate="%{x} days late<extra></extra>",
                )
            )
        worst_tail = late.groupby("carrier")["delay_days"].max().idxmax()
        worst_tail_days = int(late["delay_days"].max())
        fig.update_layout(
            title=f"Worst single delay was {worst_tail_days} days ({worst_tail})",
            height=400,
            showlegend=False,
            xaxis=dict(title="Days late", showgrid=True),
            yaxis=dict(title=None),
        )
        st.plotly_chart(fig, use_container_width=True, theme=None, config=PLOT_CONFIG)
        how_to_read(
            "Each dot is one late shipment. The box covers the middle half of that carrier's "
            "delays and the inner line is its median, so a wide box means unpredictable delays -- "
            "which is often worse operationally than a consistently small one."
        )

    st.write("")
    st.markdown('<div class="side-label">Extreme delays</div>', unsafe_allow_html=True)
    if len(late) >= 4:
        q1, q3 = late["delay_days"].quantile([0.25, 0.75])
        upper = q3 + 1.5 * (q3 - q1)
        outliers = late[late["delay_days"] > upper][
            ["shipment_id", "carrier", "destination_country", "product_category",
             "delay_days", "delay_reason", "order_value_eur"]
        ].sort_values("delay_days", ascending=False)
        if len(outliers):
            st.dataframe(
                outliers,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "delay_days": st.column_config.NumberColumn("Days late"),
                    "order_value_eur": st.column_config.NumberColumn("Order value", format="EUR %d"),
                },
            )
        else:
            st.markdown(
                f'<div class="readme">No shipment exceeds the statistical outlier threshold of '
                f'{upper:.0f} days late on this filter, so the delays are severe but not erratic '
                f'-- there is no single rogue shipment skewing the averages.</div>',
                unsafe_allow_html=True,
            )
    else:
        how_to_read("Too few late shipments on this filter to test for outliers.")

else:  # Shipment data
    page_header(
        "Shipment data",
        "The filtered rows behind every figure in this dashboard.",
    )
    st.markdown(
        f'<div class="readme">{total_shipments:,} shipments match the current filters. '
        f'Sort any column, or use the toolbar on hover to search and download.</div>',
        unsafe_allow_html=True,
    )
    display = filtered.sort_values("order_date", ascending=False)[
        ["shipment_id", "order_date", "carrier", "destination_country", "customer_type",
         "product_category", "promised_delivery_date", "actual_delivery_date",
         "delay_days", "is_late", "delay_reason", "order_value_eur"]
    ]
    st.dataframe(
        display,
        hide_index=True,
        use_container_width=True,
        height=620,
        column_config={
            "shipment_id": st.column_config.TextColumn("Shipment"),
            "order_date": st.column_config.DateColumn("Ordered", format="DD MMM YYYY"),
            "carrier": st.column_config.TextColumn("Carrier"),
            "destination_country": st.column_config.TextColumn("Destination"),
            "customer_type": st.column_config.TextColumn("Customer type"),
            "product_category": st.column_config.TextColumn("Category"),
            "promised_delivery_date": st.column_config.DateColumn("Promised", format="DD MMM YYYY"),
            "actual_delivery_date": st.column_config.DateColumn("Delivered", format="DD MMM YYYY"),
            "delay_days": st.column_config.NumberColumn("Days late", format="%d"),
            "is_late": st.column_config.CheckboxColumn("Late"),
            "delay_reason": st.column_config.TextColumn("Delay reason"),
            "order_value_eur": st.column_config.NumberColumn("Order value", format="EUR %d"),
        },
    )
