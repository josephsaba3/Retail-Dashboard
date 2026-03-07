import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="Category Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    '<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)
with open("style.css") as _f:
    st.markdown(f"<style>{_f.read()}</style>", unsafe_allow_html=True)

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("fmcg_scan_data.csv")
    df["week_ending"] = pd.to_datetime(df["week_ending"], dayfirst=True)
    return df


df_raw = load_data()

latest_week = df_raw["week_ending"].max()
latest_year = int(df_raw["year"].max())
prior_year = latest_year - 1
latest_qtr = df_raw[df_raw["year"] == latest_year]["quarter"].max()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Filters")

    all_retailers = sorted(df_raw["retailer"].unique())
    all_categories = sorted(df_raw["category"].unique())
    all_segments = sorted(df_raw["segment"].unique())
    all_brands = sorted(df_raw["brand"].unique())

    sel_period = st.selectbox(
        "Period",
        ["Latest 4 Weeks", "Latest Quarter", "Latest Year (MAT)"],
        index=2,
        key="period",
    )
    sel_categories = [st.selectbox("Category", ["All"] + all_categories, key="cat")]
    sel_retailers = [st.selectbox("Retailer", ["All"] + all_retailers, key="ret")]
    sel_segments = [st.selectbox("Segment", ["All"] + all_segments, key="seg")]
    sel_brands = [st.selectbox("Brand", ["All"] + all_brands, key="brd")]

    # Expand "All" to full list for filtering
    sel_categories = all_categories if sel_categories == ["All"] else sel_categories
    sel_retailers = all_retailers if sel_retailers == ["All"] else sel_retailers
    sel_segments = all_segments if sel_segments == ["All"] else sel_segments
    sel_brands = all_brands if sel_brands == ["All"] else sel_brands

# ── Date range from period selection ─────────────────────────────────────────
W52 = pd.Timedelta(weeks=52)

if sel_period == "Latest 4 Weeks":
    curr_end = latest_week
    curr_start = latest_week - pd.Timedelta(weeks=4) + pd.Timedelta(days=1)
    period_label = "L4W"
    prior_label = "L4W YA"
elif sel_period == "Latest Quarter":
    qtr_weeks = df_raw[(df_raw["year"] == latest_year) & (df_raw["quarter"] == latest_qtr)]["week_ending"]
    curr_start = qtr_weeks.min()
    curr_end = qtr_weeks.max()
    period_label = f"{latest_qtr} {latest_year}"
    prior_label = f"{latest_qtr} {prior_year}"
else:  # Latest Year (MAT)
    curr_start = df_raw[df_raw["year"] == latest_year]["week_ending"].min()
    curr_end = latest_week
    period_label = f"MAT {latest_year}"
    prior_label = f"MAT {prior_year}"

prior_start = curr_start - W52
prior_end = curr_end - W52

# ── Filtered datasets ─────────────────────────────────────────────────────────
universe = df_raw[
    df_raw["retailer"].isin(sel_retailers)
    & df_raw["category"].isin(sel_categories)
    & df_raw["segment"].isin(sel_segments)
]
selection = universe[universe["brand"].isin(sel_brands)]


def in_period(data, start, end):
    return data[(data["week_ending"] >= start) & (data["week_ending"] <= end)]


curr_univ = in_period(universe, curr_start, curr_end)
prior_univ = in_period(universe, prior_start, prior_end)
curr_sel = in_period(selection, curr_start, curr_end)
prior_sel = in_period(selection, prior_start, prior_end)

# ── KPI helpers ───────────────────────────────────────────────────────────────
def pct_growth(curr, prior):
    if prior == 0 or pd.isna(prior):
        return None
    return (curr / prior - 1) * 100


def share_pct(part, total):
    return (part / total * 100) if total > 0 else 0.0


def fmt_pct(v, dec=1):
    if v is None:
        return "N/A"
    return f"+{v:.{dec}f}%" if v > 0 else f"{v:.{dec}f}%"


def fmt_pp(v, dec=1):
    if v is None:
        return "N/A"
    return f"+{v:.{dec}f}pp" if v > 0 else f"{v:.{dec}f}pp"


def fmt_dollars(v):
    if v >= 1e6:
        return f"${v/1e6:.1f}M"
    if v >= 1e3:
        return f"${v/1e3:.0f}K"
    return f"${v:.0f}"


def css_color(v):
    if v is None:
        return "neu"
    return "pos" if v >= 0 else "neg"


rev_c   = curr_sel["revenue"].sum()
rev_p   = prior_sel["revenue"].sum()
units_c = curr_sel["units"].sum()
units_p = prior_sel["units"].sum()
tot_c   = curr_univ["revenue"].sum()
tot_p   = prior_univ["revenue"].sum()
shr_c   = share_pct(rev_c, tot_c)
shr_p   = share_pct(rev_p, tot_p)

sales_g  = pct_growth(rev_c, rev_p)
units_g  = pct_growth(units_c, units_p)
shr_chg  = shr_c - shr_p

# BrandA share change
def brand_shr(data, brand):
    total = data["revenue"].sum()
    part = data[data["brand"] == brand]["revenue"].sum()
    return share_pct(part, total)

branda_shr_c = brand_shr(curr_univ, "BrandA")
branda_shr_p = brand_shr(prior_univ, "BrandA")
branda_shr_chg = branda_shr_c - branda_shr_p

# ── Chart constants ───────────────────────────────────────────────────────────
BRAND_COLORS = {
    "BrandA": "#2D2D2D",
    "BrandB": "#D46422",
    "BrandC": "#2A9D6E",
    "BrandD": "#1a6b8a",
    "Private Label": "#7B4F8A",
}

CHART_SERIES = ["#D46422", "#2A9D6E", "#1a6b8a", "#8B6914", "#7B4F8A", "#C94444"]

CHART_BASE = dict(
    paper_bgcolor="#FFFFFF",
    plot_bgcolor="#FFFFFF",
    font=dict(family="DM Sans, Arial, sans-serif", size=12, color="#2D2D2D"),
)


def hdr(text):
    st.markdown(f'<div class="section-hdr">{text}</div>', unsafe_allow_html=True)


# ── Page header ───────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div class="topbar">
        <div>
            <div class="topbar-title">Category Dashboard</div>
            <div class="topbar-sub">
                {period_label} vs {prior_label} &nbsp;|&nbsp;
                {curr_start.strftime('%d %b %Y')} – {curr_end.strftime('%d %b %Y')} &nbsp;|&nbsp;
                Values in AUD
            </div>
        </div>
        <div>
            <div class="topbar-rev-label">{period_label} Revenue</div>
            <div class="topbar-rev-val">{fmt_dollars(rev_c)}</div>
        </div>
    </div>""",
    unsafe_allow_html=True,
)

# ── KPI Cards ─────────────────────────────────────────────────────────────────
k1, k2, k3 = st.columns(3)


def render_kpi(col, accent, label, val, fmt_v, sub):
    c = css_color(val)
    col.markdown(
        f"""
        <div class="kpi-card" style="--accent:{accent};">
            <div class="kpi-label">{label}</div>
            <div class="kpi-period" style="text-align:center;">{period_label} vs {prior_label}</div>
            <div class="kpi-val {c}">{fmt_v}</div>
            <div class="kpi-sub">{sub}</div>
        </div>""",
        unsafe_allow_html=True,
    )


render_kpi(k1, "#D46422", "Sales % Growth vs YA", sales_g,
           fmt_pct(sales_g), f"{fmt_dollars(rev_c)} vs {fmt_dollars(rev_p)}")
render_kpi(k2, "#D46422", "Units % Growth vs YA", units_g,
           fmt_pct(units_g), f"{units_c:,.0f} vs {units_p:,.0f} units")
render_kpi(k3, "#D46422", "BrandA Share vs YA", branda_shr_chg,
           fmt_pp(branda_shr_chg), f"{branda_shr_c:.1f}% share vs {branda_shr_p:.1f}% YA")

st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

# ── Row 1: Category share + Segment growth ────────────────────────────────────
r1c1, r1c2 = st.columns(2)

with r1c1:
    hdr(f"Share of Category ({period_label})")
    cat_rev = curr_univ.groupby("category")["revenue"].sum().reset_index()
    fig = px.pie(
        cat_rev, values="revenue", names="category",
        color_discrete_sequence=["#2D2D2D", "#D46422"],
        hole=0.45,
    )
    fig.update_traces(textposition="outside", textinfo="percent+label", textfont_size=12)
    fig.update_layout(**CHART_BASE, height=310, showlegend=False,
                      margin=dict(t=10, b=10, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with r1c2:
    hdr(f"Segment Sales Growth vs YA ({period_label})")
    seg_c = curr_univ.groupby("segment")["revenue"].sum()
    seg_p = prior_univ.groupby("segment")["revenue"].sum()
    seg_g = ((seg_c - seg_p) / seg_p * 100).dropna().reset_index()
    seg_g.columns = ["segment", "growth"]
    seg_g = seg_g.sort_values("growth")

    fig = go.Figure(go.Bar(
        y=seg_g["segment"], x=seg_g["growth"], orientation="h",
        marker_color=["#2A9D6E" if v >= 0 else "#C94444" for v in seg_g["growth"]],
        text=[f"{v:+.1f}%" for v in seg_g["growth"]],
        textposition="outside", cliponaxis=False,
    ))
    fig.add_vline(x=0, line_width=1.5, line_color="#E8E3DC")
    fig.update_layout(**CHART_BASE, height=310,
                      xaxis=dict(title="% Growth vs YA", showgrid=True, gridcolor="#E8E3DC", zeroline=False),
                      yaxis=dict(showgrid=False),
                      margin=dict(t=10, b=10, l=10, r=80))
    st.plotly_chart(fig, use_container_width=True)

# ── Row 2: Brand share + Brand share change ───────────────────────────────────
r2c1, r2c2 = st.columns(2)

with r2c1:
    hdr(f"Share by Brand ({period_label})")
    brand_rev = curr_univ.groupby("brand")["revenue"].sum().reset_index()
    fig = px.pie(
        brand_rev, values="revenue", names="brand",
        color="brand", color_discrete_map=BRAND_COLORS,
        hole=0.45,
    )
    fig.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
    fig.update_layout(**CHART_BASE, height=340,
                      legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
                      margin=dict(t=10, b=50, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with r2c2:
    hdr(f"Brand Share Change vs Same Period YA")
    def brand_share(data):
        total = data["revenue"].sum()
        s = data.groupby("brand")["revenue"].sum()
        return (s / total * 100) if total > 0 else s * 0

    bs_c = brand_share(curr_univ)
    bs_p = brand_share(prior_univ)
    delta = (bs_c - bs_p).dropna().reset_index()
    delta.columns = ["brand", "change"]
    delta = delta.sort_values("change")

    fig = go.Figure(go.Bar(
        y=delta["brand"], x=delta["change"], orientation="h",
        marker_color=[BRAND_COLORS.get(b, "#6B6B6B") for b in delta["brand"]],
        marker_line_color=["#2A9D6E" if v >= 0 else "#C94444" for v in delta["change"]],
        marker_line_width=2,
        text=[f"{v:+.2f}pp" for v in delta["change"]],
        textposition="outside", cliponaxis=False,
    ))
    fig.add_vline(x=0, line_width=1.5, line_color="#E8E3DC")
    fig.update_layout(**CHART_BASE, height=320,
                      xaxis=dict(title="Share change vs. YA", showgrid=True, gridcolor="#E8E3DC", zeroline=False),
                      yaxis=dict(showgrid=False),
                      margin=dict(t=10, b=10, l=10, r=80))
    st.plotly_chart(fig, use_container_width=True)

# ── Row 3: Segment YA comparison + Revenue trend ──────────────────────────────
r3c1, r3c2 = st.columns(2)

with r3c1:
    hdr("Revenue by Segment: YA Comparison")
    seg_curr_df = curr_univ.groupby("segment")["revenue"].sum().reset_index()
    seg_curr_df["period"] = period_label
    seg_prior_df = prior_univ.groupby("segment")["revenue"].sum().reset_index()
    seg_prior_df["period"] = prior_label
    seg_yoy = pd.concat([seg_prior_df, seg_curr_df])

    fig = px.bar(
        seg_yoy, x="segment", y="revenue", color="period", barmode="group",
        color_discrete_map={period_label: "#D46422", prior_label: "#C0C0C0"},
        labels={"revenue": "Revenue ($)", "segment": "", "period": ""},
    )

    # Add % change annotations above each current-period bar
    segments = seg_curr_df["segment"].tolist()
    curr_by_seg = seg_curr_df.set_index("segment")["revenue"]
    prior_by_seg = seg_prior_df.set_index("segment")["revenue"]
    for seg in segments:
        c, p = curr_by_seg.get(seg, 0), prior_by_seg.get(seg, 0)
        if p > 0:
            chg = (c / p - 1) * 100
            fig.add_annotation(
                x=seg,
                y=max(c, p),
                text=f"<b>{chg:+.1f}%</b>",
                showarrow=False,
                yshift=10,
                font=dict(size=11, color="#2A9D6E" if chg >= 0 else "#C94444"),
                xref="x", yref="y",
            )

    fig.update_layout(**CHART_BASE, height=350,
                      legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, x=0),
                      xaxis_tickangle=-20,
                      yaxis=dict(showgrid=True, gridcolor="#E8E3DC", title="Revenue ($)"),
                      xaxis=dict(showgrid=False),
                      margin=dict(t=30, b=60, l=10, r=10))
    st.plotly_chart(fig, use_container_width=True)

with r3c2:
    if sel_period == "Latest 4 Weeks":
        hdr("Weekly Revenue Trend (L4W vs YA)")
        # Align by week number within the 4-week window
        curr_weekly = (
            in_period(selection, curr_start, curr_end)
            .groupby("week_ending")["revenue"].sum().reset_index().sort_values("week_ending")
        )
        curr_weekly["week"] = range(1, len(curr_weekly) + 1)

        prior_weekly = (
            in_period(selection, prior_start, prior_end)
            .groupby("week_ending")["revenue"].sum().reset_index().sort_values("week_ending")
        )
        prior_weekly["week"] = range(1, len(prior_weekly) + 1)

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=prior_weekly["week"], y=prior_weekly["revenue"],
            mode="lines+markers", name=prior_label,
            line=dict(color="#C0C0C0", width=2.5, dash="dot"),
            marker=dict(size=8, color="#C0C0C0"),
        ))
        fig.add_trace(go.Scatter(
            x=curr_weekly["week"], y=curr_weekly["revenue"],
            mode="lines+markers", name=period_label,
            line=dict(color="#D46422", width=2.5),
            marker=dict(size=8, color="#D46422"),
        ))
        fig.update_layout(**CHART_BASE, height=330,
                          legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, x=0),
                          xaxis=dict(title="Week", showgrid=True, gridcolor="#E8E3DC", dtick=1),
                          yaxis=dict(title="Revenue ($)", showgrid=True, gridcolor="#E8E3DC"),
                          margin=dict(t=10, b=30, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

    else:
        hdr("Quarterly Revenue Trend")
        trend = (
            selection[selection["year"].isin([prior_year, latest_year])]
            .groupby(["year", "quarter"])["revenue"].sum().reset_index()
            .sort_values(["year", "quarter"])
        )
        fig = go.Figure()
        for yr, color, dash in [(prior_year, "#C0C0C0", "dot"), (latest_year, "#D46422", "solid")]:
            t = trend[trend["year"] == yr]
            fig.add_trace(go.Scatter(
                x=t["quarter"], y=t["revenue"],
                mode="lines+markers", name=str(yr),
                line=dict(color=color, width=2.5, dash=dash),
                marker=dict(size=8, color=color),
            ))
        fig.update_layout(**CHART_BASE, height=330,
                          legend=dict(title="", orientation="h", yanchor="bottom", y=1.02, x=0),
                          xaxis=dict(title="", showgrid=True, gridcolor="#E8E3DC"),
                          yaxis=dict(title="Revenue ($)", showgrid=True, gridcolor="#E8E3DC"),
                          margin=dict(t=10, b=30, l=10, r=10))
        st.plotly_chart(fig, use_container_width=True)

# ── Row 4: Promo % + Distribution ─────────────────────────────────────────────
r4c1, r4c2 = st.columns(2)

with r4c1:
    hdr(f"Promo % of Sales by Brand ({period_label})")
    promo_summary = (
        curr_univ.groupby("brand")
        .apply(lambda x: x[x["on_promo"] == 1]["revenue"].sum() / x["revenue"].sum() * 100)
        .reset_index()
    )
    promo_summary.columns = ["brand", "promo_pct"]
    promo_summary = promo_summary.sort_values("promo_pct", ascending=True)

    fig = go.Figure(go.Bar(
        y=promo_summary["brand"], x=promo_summary["promo_pct"], orientation="h",
        marker_color=[BRAND_COLORS.get(b, "#6B6B6B") for b in promo_summary["brand"]],
        text=[f"{v:.1f}%" for v in promo_summary["promo_pct"]],
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(**CHART_BASE, height=300,
                      xaxis=dict(title="% Revenue on Promo", showgrid=True, gridcolor="#E8E3DC",
                                 zeroline=False, range=[0, max(promo_summary["promo_pct"]) * 1.25]),
                      yaxis=dict(showgrid=False),
                      margin=dict(t=10, b=30, l=10, r=60))
    st.plotly_chart(fig, use_container_width=True)

with r4c2:
    hdr(f"Avg Distribution % by Brand ({period_label})")
    distrib = (
        curr_univ.groupby("brand")["distribution_pct"].mean()
        .reset_index().sort_values("distribution_pct", ascending=True)
    )
    distrib.columns = ["brand", "dist_pct"]

    fig = go.Figure(go.Bar(
        y=distrib["brand"], x=distrib["dist_pct"], orientation="h",
        marker_color=[BRAND_COLORS.get(b, "#6B6B6B") for b in distrib["brand"]],
        text=[f"{v:.1f}%" for v in distrib["dist_pct"]],
        textposition="outside", cliponaxis=False,
    ))
    fig.update_layout(**CHART_BASE, height=300,
                      xaxis=dict(title="Avg Distribution %", showgrid=True, gridcolor="#E8E3DC",
                                 zeroline=False, range=[0, 115]),
                      yaxis=dict(showgrid=False),
                      margin=dict(t=10, b=30, l=10, r=60))
    st.plotly_chart(fig, use_container_width=True)
