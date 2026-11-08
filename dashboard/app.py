"""Streamlit dashboard for a reproducible, synthetic SaaS onboarding experiment.

Launch with: streamlit run dashboard/app.py
All data in this UI are generated locally from a fictional model. No customer data.
"""
import csv
import io
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from saas_analytics.simulate import generate
from dashboard.data import (
    VARIANTS, FUNNEL_STEPS, aggregate_kpis, arm_summary, cohort_rows,
    compare_metric, experiment_summary, exploratory_segments, funnel_rows,
    load_verified_users, select_users,
)

st.set_page_config(
    page_title="Onboard Lab | SaaS Product Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

INK = "#EDF3FF"
MUTED = "#91A4C4"
ACCENT = "#6EE7DD"
BLUE = "#7599FF"
AMBER = "#FBBF72"
COLOR = {"control": BLUE, "treatment": ACCENT}
NAV = ["Overview", "Onboarding funnel", "Retention & cohorts", "Experiment lab"]

st.markdown(
    """
    <style>
    .stApp { background: #0A1020; color: #EDF3FF; }
    [data-testid="stSidebar"] { background: #0E172A; border-right: 1px solid #26334D; }
    .block-container { max-width: 1380px; padding-top: 2.1rem; padding-bottom: 3rem; }
    h1, h2, h3 { letter-spacing: -0.045em; }
    h1 { font-size: 2.45rem !important; font-weight: 780 !important; }
    h2 { font-size: 1.5rem !important; margin-top: .45rem; }
    [data-testid="stMetric"] {
        padding: 1.1rem 1.18rem; background: #111D32;
        border: 1px solid #263955; border-radius: 15px;
    }
    [data-testid="stMetricLabel"] { color: #A1B3D0 !important; }
    [data-testid="stMetricValue"] { color: #EEF5FF !important; }
    .hero-eyebrow { letter-spacing: .2em; color: #6EE7DD; font-size: .72rem; font-weight: 750; }
    .hero-lede { color: #A5B4CD; font-size: 1.01rem; margin-top: -.4rem; }
    .eyebrow { font-size: .77rem; text-transform: uppercase; color: #91A4C4; letter-spacing: .13em; }
    .small-notice { color: #C6D6F0; font-size: .9rem; line-height: 1.6; }
    div[data-testid="stDataFrame"] { border: 1px solid #283954; border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Generating and validating the synthetic dataset…")
def get_demo(seed, n):
    """Auto-materialize a reproducible demo DB on first launch, including cloud."""
    dest = ROOT / "data" / "generated" / f"dashboard_s{seed}_n{n}"
    database = dest / "saas.db"
    if not database.exists():
        generate(users=n, seed=seed, output_dir=dest)
    return load_verified_users(database)


def styled_chart(fig, height=370):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=12, t=30, b=15),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=12, color=INK),
        legend=dict(orientation="h", y=1.13, x=0, title=None),
        xaxis=dict(gridcolor="#24344D", zerolinecolor="#24344D", linecolor="#24344D"),
        yaxis=dict(gridcolor="#24344D", zerolinecolor="#24344D", linecolor="#24344D"),
        hoverlabel=dict(bgcolor="#1D304A", font_color=INK),
    )
    return fig


def pct(p):
    return f"{p:.1%}"


def pp(p):
    return f"{p:+.2f} pp"


def metric_line(label, number, detail=None):
    st.metric(label, number, delta=detail, delta_color="off")


def headline(title, description):
    st.markdown(f'<div class="eyebrow">{title}</div>', unsafe_allow_html=True)
    st.caption(description)


def funnel_figure(rows):
    fig = go.Figure()
    labels = [s[0] for s in FUNNEL_STEPS][::-1]
    for v in VARIANTS:
        values = {r["step"]: r["rate_pct"] for r in rows if r["variant"] == v}
        fig.add_trace(go.Bar(
            name=v.title(), y=labels, x=[values[x] for x in labels],
            orientation="h", marker_color=COLOR[v],
            text=[f"{values[x]:.1f}%" for x in labels],
            textposition="outside", cliponaxis=False, offsetgroup=v,
            hovertemplate="%{y}<br>%{x:.1f}% of assigned users<extra>%{fullData.name}</extra>",
        ))
    fig.update_layout(barmode="group", bargap=.29, bargroupgap=.08)
    fig.update_xaxes(range=[0, 113], ticksuffix="%")
    fig.update_yaxes(showgrid=False)
    return styled_chart(fig, height=360)


def cohort_figure(rows, metric="retention_d28_pct"):
    fig = go.Figure()
    for v in VARIANTS:
        part = [r for r in rows if r["variant"] == v]
        fig.add_trace(go.Scatter(
            x=[r["signup_month"] for r in part],
            y=[r[metric] for r in part],
            mode="lines+markers",
            name=v.title(),
            line=dict(width=3, color=COLOR[v]),
            marker=dict(size=10),
            customdata=[r["users"] for r in part],
            hovertemplate="%{x}<br>%{y:.2f}%<br>n=%{customdata}<extra>%{fullData.name}</extra>",
        ))
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    fig.update_xaxes(type="category")
    return styled_chart(fig, height=345)


def group_breakdown(records):
    rows = []
    for segment in ("solo", "team"):
        subset = [u for u in records if u["segment"] == segment]
        if not subset:
            continue
        k = aggregate_kpis(subset)
        rows.append({
            "User type": segment.title(), "Signups": k["users"],
            "D7 activation": pct(k["activated_d7"]),
            "D28 retention": pct(k["returned_d28"]),
            "Error rate": pct(k["onboarding_error_d7"]),
        })
    return rows


def effect_figure(comparisons):
    fields = [
        ("Day-28 retention", "returned_d28"),
        ("D7 activation", "activated_d7"),
        ("Onboarding errors", "onboarding_error_d7"),
        ("Support tickets", "support_ticket_d7"),
    ]
    fig = go.Figure()
    for label, field in reversed(fields):
        c = comparisons[field]
        if c is None:
            continue
        low, high = c["confidence_interval_95_pp"]
        mid = c["absolute_lift_pp"]
        fig.add_trace(go.Scatter(
            x=[mid], y=[label], mode="markers", showlegend=False,
            marker=dict(size=13, color=AMBER if field in
                        ("onboarding_error_d7", "support_ticket_d7") else ACCENT),
            error_x=dict(
                type="data", symmetric=False,
                array=[max(0, high - mid)],
                arrayminus=[max(0, mid - low)],
                color=MUTED, thickness=2.1, width=5,
            ),
            hovertemplate=f"{label}<br>Difference: %{{x:+.2f}} pp<extra>95% CI</extra>",
        ))
    fig.add_vline(x=0, line_dash="dash", line_color="#677A98")
    fig.update_xaxes(title_text="Treatment − control (percentage points)")
    fig.update_yaxes(showgrid=False)
    return styled_chart(fig, height=350)


def export_csv(rows):
    if not rows:
        return ""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()


with st.sidebar:
    st.markdown("### ◈ ONBOARD LAB")
    st.caption("PRODUCT ANALYTICS WORKSPACE")
    st.divider()
    view = st.radio("Workspace", NAV, index=0)
    st.divider()
    st.markdown("##### Scenario controls")
    seed = st.number_input("Synthetic seed", min_value=0, max_value=10000, value=42, step=1)
    user_count = st.selectbox("Simulated users", options=(2000, 4000, 8000), index=1)
    st.caption("Changing either value regenerates a different fictional sample.")
    st.divider()

try:
    all_users, quality = get_demo(int(seed), int(user_count))
except (OSError, ValueError, sqlite3.Error) as exc:
    st.error(f"Unable to load a validated dataset: {exc}")
    st.stop()

months = sorted({u["signup_month"] for u in all_users})
with st.sidebar:
    segment = st.selectbox("User segment", options=("All users", "solo", "team"))
    selected_months = st.multiselect("Signup cohorts", options=months, default=months)
    st.caption("Filters use only signup metadata. Effects are recomputed on the selected population.")
    st.divider()
    st.success(f"Data audit passed · {quality['users_checked']:,} users")
    st.caption("Synthetic / educational · No real customers")
    st.download_button(
        "Export filtered users (.csv)",
        data=export_csv(select_users(all_users, segment, selected_months)),
        file_name="synthetic_saas_users_filtered.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.markdown("[View source on GitHub](https://github.com/ricoxvl/saas-onboarding-experiment-analytics)")

users = select_users(all_users, segment=segment, months=selected_months)
st.markdown('<div class="hero-eyebrow">EXPERIMENTATION · GROWTH · RETENTION</div>', unsafe_allow_html=True)
st.title("SaaS Onboarding Analytics")
st.markdown(
    '<div class="hero-lede">From signup to activation to sustained usage — a portfolio-grade product decision workspace.</div>',
    unsafe_allow_html=True,
)
st.warning(
    "DEMONSTRATION DATA ONLY — all users and outcomes are simulated. "
    "These visualizations are not evidence of an actual SaaS experiment or customer impact.",
    icon="🧪",
)

if not users:
    st.info("No users match your filters. Select at least one signup cohort.")
    st.stop()

kpi = aggregate_kpis(users)
effect = experiment_summary(users)
if view == "Overview":
    headline("01 / Executive overview", "Core acquisition, activation, retention, and experience health.")
    a, b, c, d = st.columns(4)
    with a: metric_line("New signups", f"{kpi['users']:,}")
    with b: metric_line("D7 activation", pct(kpi["activated_d7"]))
    with c: metric_line("D28 retention", pct(kpi["returned_d28"]))
    with d: metric_line("Onboarding errors", pct(kpi["onboarding_error_d7"]))
    st.markdown("")
    left, right = st.columns([1.05, .95], gap="large")
    with left:
        st.subheader("Retention by signup cohort")
        st.plotly_chart(cohort_figure(cohort_rows(users)), use_container_width=True)
    with right:
        st.subheader("Activation funnel")
        st.plotly_chart(funnel_figure(funnel_rows(users)), use_container_width=True)
    st.subheader("Where performance differs")
    st.dataframe(pd.DataFrame(group_breakdown(users)), hide_index=True, use_container_width=True)
    if effect is not None:
        primary = effect["comparisons"]["returned_d28"]
        st.info(
            f"In this simulated selection, guided onboarding has a "
            f"{primary['absolute_lift_pp']:+.2f} pp D28 return-rate difference. "
            "Evaluate uncertainty and error guardrails in the Experiment lab before drawing conclusions."
        )

elif view == "Onboarding funnel":
    headline("02 / Onboarding funnel", "Counts and conversion from the full assigned-user denominator.")
    st.subheader("How far do users progress?")
    rows = funnel_rows(users)
    st.plotly_chart(funnel_figure(rows), use_container_width=True)
    st.caption(
        "Funnel steps are monotonic. Teammate invites are a separate optional behavior "
        "and are deliberately excluded from this funnel."
    )
    st.subheader("Conversion by assigned experience")
    frame = pd.DataFrame(rows)
    frame = frame.rename(columns={
        "variant": "Experience", "step": "Step",
        "users": "Users", "rate_pct": "Conversion (%)",
    })
    st.dataframe(frame, hide_index=True, use_container_width=True)
    st.markdown("#### Experience friction")
    a, b = st.columns(2)
    with a:
        st.metric("Users with onboarding errors (D7)", pct(kpi["onboarding_error_d7"]))
    with b:
        st.metric("Users with support tickets (D7)", pct(kpi["support_ticket_d7"]))
    st.caption("Both are user-level binary rates, not a count of error or ticket events.")

elif view == "Retention & cohorts":
    headline("03 / Retention intelligence", "Compare fully observed day-28 return activity by signup month.")
    metric_label = st.radio(
        "Cohort measure", ["D28 retention", "D7 activation"], horizontal=True
    )
    metric_col = ("retention_d28_pct" if metric_label == "D28 retention" else "activation_pct")
    cohort_data = cohort_rows(users)
    st.plotly_chart(cohort_figure(cohort_data, metric_col), use_container_width=True)
    st.subheader("Cohort performance table")
    data = pd.DataFrame(cohort_data).rename(columns={
        "signup_month": "Signup cohort", "variant": "Assigned experience",
        "users": "Users", "activation_pct": "D7 activation (%)",
        "retention_d28_pct": "D28 retention (%)",
    })
    st.dataframe(data, hide_index=True, use_container_width=True)
    st.subheader("Exploratory treatment differences")
    exploratory = exploratory_segments(users)
    if exploratory:
        st.dataframe(
            pd.DataFrame(exploratory).rename(columns={
                "dimension": "Dimension", "level": "Group",
                "control_n": "Control n", "treatment_n": "Treatment n",
                "control_pct": "Control D28 (%)", "treatment_pct": "Treatment D28 (%)",
                "lift_pp": "Lift (pp)", "p_value": "Raw p", "bh_fdr_q_value": "BH q",
            }),
            hide_index=True, use_container_width=True,
        )
    st.caption(
        "Subgroup contrasts are exploratory; BH q-values adjust the shown retention "
        "contrasts as one family. Significance in one group does not establish a "
        "treatment-by-segment interaction."
    )

else:
    headline("04 / Experiment lab", "Primary inference, sample allocation, negative-outcome guardrails, and design sensitivity.")
    if effect is None:
        st.warning("Both control and treatment users are required. Widen your cohort filters.")
        st.stop()
    primary = effect["comparisons"]["returned_d28"]
    p_value = primary["p_value_two_sided"]
    low, high = primary["confidence_interval_95_pp"]
    a, b, c, d = st.columns(4)
    with a: metric_line("Standard D28", pct(primary["control_rate"]))
    with b: metric_line("Guided D28", pct(primary["treatment_rate"]))
    with c: metric_line("Absolute lift", pp(primary["absolute_lift_pp"]))
    with d: metric_line("Two-sided p-value", f"{p_value:.4f}")
    st.caption(
        f"95% unpooled Wald CI: [{low:+.2f}, {high:+.2f}] pp · "
        f"Control n={primary['control_n']:,} · Treatment n={primary['treatment_n']:,}. "
        "All analyses are intention-to-treat within the selected signup population."
    )
    st.subheader("Effects and confidence intervals")
    st.plotly_chart(effect_figure(effect["comparisons"]), use_container_width=True)

    left, right = st.columns([1.08, .92], gap="large")
    with left:
        st.subheader("Guardrail risk review")
        tolerance = st.slider(
            "Illustrative maximum tolerable increase (pp)",
            min_value=0.0, max_value=5.0, value=2.0, step=0.5,
            help="Exploratory sensitivity slider, not a pre-registered launch threshold.",
        )
        revised = experiment_summary(users, tolerance_pp=tolerance)
        table = []
        for key, title in (
            ("onboarding_error_d7", "Onboarding errors"),
            ("support_ticket_d7", "Support tickets"),
        ):
            comp = revised["comparisons"][key]
            status = revised["guardrails"][key]
            table.append({
                "Guardrail": title,
                "Control (%)": round(comp["control_rate"] * 100, 2),
                "Treatment (%)": round(comp["treatment_rate"] * 100, 2),
                "Change (pp)": comp["absolute_lift_pp"],
                "Upper 95% CI (pp)": status["upper_confidence_bound_pp"],
                "Under tolerance?": "Yes" if status["upper_bound_within_tolerance"] else "Not established",
            })
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True)
        st.caption("Positive changes indicate more negative outcomes. These are unadjusted marginal intervals, not joint safety guarantees.")

    with right:
        st.subheader("Design sensitivity")
        planning = effect["planning"]
        mde = planning["mde_absolute_pp_approx"]
        st.metric("Approx. 80%-power MDE", f"{mde:.2f} pp" if mde is not None else "Not estimable")
        st.caption("Prospective planning formula using the observed synthetic control rate as a reference, not post-hoc observed power.")
        st.dataframe(
            pd.DataFrame(planning["required_total_n_balanced_by_effect"]).rename(columns={
                "effect_pp": "Target lift (pp)",
                "required_n_per_arm": "Users / arm",
                "required_total_n": "Total sample",
            }),
            hide_index=True, use_container_width=True,
        )
        allocation = effect["allocation"]
        st.caption(
            f"Filtered assignment counts: control {allocation['control_n']:,}, "
            f"treatment {allocation['treatment_n']:,}; 50/50 SRM p={allocation['srm_p_value']:.4f}. "
            "After subsetting, this is a diagnostic only."
        )
    st.divider()
    st.subheader("Product decision interpretation")
    significant = p_value < .05
    enough = all(x["upper_bound_within_tolerance"] for x in revised["guardrails"].values())
    if significant and primary["absolute_lift_pp"] > 0 and enough:
        st.success(
            "In this simulated scenario, the primary result is directionally positive, "
            "statistically detectable, and the illustrative guardrail interval thresholds are met. "
            "This only supports proposing a properly planned real-world validation experiment."
        )
    else:
        st.warning(
            "In this simulated scenario, the primary-effect and guardrail evidence is insufficient "
            "to recommend rolling out the change. Examine uncertainty, practical lift, and "
            "the consequences of extra onboarding friction."
        )
    st.caption(
        "A significant p-value alone never establishes business value. "
        "These are synthetic estimates, guardrail bounds are unadjusted, "
        "and changes to the tolerance slider are post-hoc exploration."
    )

st.divider()
st.caption(
    "ONBOARD LAB · Synthetic demonstration only · Python / SQLite / Streamlit / Plotly · "
    "All computations are from reproducible seeded events · "
    "See docs/analysis_guide.md for assumptions and limitations."
)
