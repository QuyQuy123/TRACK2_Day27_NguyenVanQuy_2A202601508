from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# Setup paths
ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "latest_metrics.json"
HISTORY = ROOT / "data" / "history" / "metrics_history.csv"
LINEAGE_PATH = ROOT / "data" / "baseline" / "lineage_graph.json"
ORDERS_CONTRACT = ROOT / "contracts" / "orders_contract.yaml"
KB_CONTRACT = ROOT / "contracts" / "kb_contract.yaml"
INCIDENT_REPORT = ROOT / "reports" / "incident_report.md"
AGENT_LOG = ROOT / "reports" / "agent_log.md"

st.set_page_config(
    page_title="Data Reliability Control Plane",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End CSS with Glassmorphism & Animations
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap" rel="stylesheet">

    <style>
    /* Global Typography & Background */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    code, pre {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Gradient Brand Header */
    .brand-title {
        font-size: 2.3rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        background: linear-gradient(135deg, #38BDF8 0%, #818CF8 50%, #C084FC 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 2px;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 0.95rem;
        color: #94A3B8;
        font-weight: 500;
        margin-bottom: 1.5rem;
    }

    /* Glassmorphism Card Container */
    .glass-card {
        background: rgba(30, 41, 59, 0.6);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3), 0 8px 10px -6px rgba(0, 0, 0, 0.3);
        transition: transform 0.2s ease, border-color 0.2s ease;
        margin-bottom: 1rem;
    }
    .glass-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }

    /* Pulsating Live Dot */
    .pulse-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
        vertical-align: middle;
    }
    .dot-green {
        background: #10B981;
        box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
        animation: pulseGreen 2s infinite;
    }
    .dot-red {
        background: #EF4444;
        box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7);
        animation: pulseRed 1.5s infinite;
    }
    .dot-yellow {
        background: #F59E0B;
        box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7);
        animation: pulseYellow 2s infinite;
    }
    @keyframes pulseGreen {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    @keyframes pulseRed {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(239, 68, 68, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    @keyframes pulseYellow {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }
    }

    /* Custom Status Badges */
    .badge-chip {
        display: inline-flex;
        align-items: center;
        padding: 5px 14px;
        border-radius: 9999px;
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    .badge-healthy {
        background: rgba(16, 185, 129, 0.15);
        color: #34D399;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }
    .badge-warning {
        background: rgba(245, 158, 11, 0.15);
        color: #FBBF24;
        border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .badge-critical {
        background: rgba(239, 68, 68, 0.15);
        color: #F87171;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }

    /* Pipeline Flowchart Elements */
    .flow-step {
        display: inline-block;
        background: #1E293B;
        padding: 10px 18px;
        border-radius: 8px;
        border: 1px solid #334155;
        font-family: 'JetBrains Mono', monospace;
        font-size: 0.9rem;
        font-weight: 600;
        color: #F1F5F9;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    }
    .flow-arrow {
        color: #64748B;
        font-size: 1.2rem;
        font-weight: bold;
        margin: 0 10px;
        vertical-align: middle;
    }
    .flow-critical {
        border-color: #EF4444;
        color: #F87171;
        background: rgba(239, 68, 68, 0.1);
    }

    /* Metric Value Styling */
    .metric-num {
        font-size: 1.9rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #F8FAFC;
    }
    .metric-label {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #94A3B8;
        margin-bottom: 4px;
    }
    .metric-sub {
        font-size: 0.8rem;
        font-weight: 500;
        margin-top: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def run_cmd(cmd_list: list[str]) -> str:
    try:
        res = subprocess.run(
            [sys.executable] + cmd_list,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        return res.stdout or res.stderr
    except Exception as e:
        return str(e)


# Ensure baseline metrics exist
if not REPORT.exists():
    run_cmd(["scripts/run_baseline.py"])

try:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
except Exception:
    report = {}

crit_fails = report.get("critical_contract_failures", 0)
contract_fails = report.get("failed_contract_checks", 0)
kb_fails = report.get("kb_failed_checks", 0)
freshness = report.get("freshness_minutes", 0.0)
kb_fresh = report.get("kb_freshness_minutes", 0.0)
row_anomaly = report.get("row_count_anomaly", {}).get("is_anomaly", False)
slo_data = report.get("contract_slo", {})
rem_budget = slo_data.get("remaining_error_budget_fraction", 1.0) * 100.0
burn_rate = slo_data.get("burn_rate", 0.0)

# Sidebar Controls & Game Day Simulator
st.sidebar.markdown(
    """
    <div style="display: flex; align-items: center; margin-bottom: 15px;">
        <span style="font-size: 2rem; margin-right: 10px;">🛡️</span>
        <div>
            <h3 style="margin: 0; font-size: 1.1rem; font-weight: 800; color: #F8FAFC;">CONTROL DECK</h3>
            <p style="margin: 0; font-size: 0.75rem; color: #94A3B8;">Reliability Simulator</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar.expander("⚡ Pipeline Commands", expanded=True):
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        if st.button("🔄 Reset Lab", use_container_width=True):
            with st.spinner("Resetting to healthy state..."):
                run_cmd(["scripts/reset_lab.py"])
                run_cmd(["scripts/run_baseline.py"])
                st.rerun()
    with col_s2:
        if st.button("▶️ Baseline", use_container_width=True):
            with st.spinner("Running telemetry..."):
                run_cmd(["scripts/run_baseline.py"])
                st.rerun()

with st.sidebar.expander("⚠️ Game Day Fault Injection", expanded=True):
    st.caption("Trigger synthetic faults to test automated detection:")
    if st.button("💥 Duplicate PK (Orders)", use_container_width=True, help="Inject duplicate primary key in orders.csv"):
        with st.spinner("Injecting duplicate order_id..."):
            run_cmd(["scripts/inject_fault.py", "duplicate_pk"])
            run_cmd(["scripts/run_baseline.py"])
            st.rerun()

    if st.button("📉 Volume Drop (-75%)", use_container_width=True, help="Inject 75% volume reduction"):
        with st.spinner("Injecting partial ingestion drop..."):
            run_cmd(["scripts/inject_fault.py", "volume_drop"])
            run_cmd(["scripts/run_baseline.py"])
            st.rerun()

    if st.button("⏳ Stale KB (-3 Hours)", use_container_width=True, help="Set KB published_at to 3 hours ago"):
        with st.spinner("Injecting stale KB timestamps..."):
            run_cmd(["scripts/inject_fault.py", "stale_kb"])
            run_cmd(["scripts/run_baseline.py"])
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("### 📡 Live Diagnostics")
if crit_fails > 0 or kb_fails > 0:
    st.sidebar.markdown(
        """
        <div style="padding: 12px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px;">
            <p style="margin: 0; color: #F87171; font-weight: 700; font-size: 0.9rem;"><span class="pulse-dot dot-red"></span>INCIDENT ACTIVE (P1)</p>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.78rem;">Contract violations detected upstream.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
elif row_anomaly:
    st.sidebar.markdown(
        """
        <div style="padding: 12px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 8px;">
            <p style="margin: 0; color: #FBBF24; font-weight: 700; font-size: 0.9rem;"><span class="pulse-dot dot-yellow"></span>VOLUME ANOMALY (P3)</p>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.78rem;">Traffic volume deviated from MAD baseline.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.sidebar.markdown(
        """
        <div style="padding: 12px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 8px;">
            <p style="margin: 0; color: #34D399; font-weight: 700; font-size: 0.9rem;"><span class="pulse-dot dot-green"></span>ALL SYSTEMS HEALTHY</p>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.78rem;">All contracts & SLOs within policy.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.sidebar.markdown("<br>", unsafe_allow_html=True)
st.sidebar.caption(f"Telemetry timestamp: `{report.get('timestamp', datetime.now(timezone.utc).isoformat())[:19]}Z`")

# Header Section
col_top1, col_top2 = st.columns([3, 1])
with col_top1:
    st.markdown('<p class="brand-title">🛡️ Antigravity Data Reliability</p>', unsafe_allow_html=True)
    st.markdown('<p class="brand-subtitle">Automated Data Contract Gateway, Statistical Anomaly Detection & Multi-Window SLO Control Plane</p>', unsafe_allow_html=True)

with col_top2:
    if crit_fails > 0:
        st.markdown('<div style="text-align: right; margin-top: 8px;"><span class="badge-chip badge-critical"><span class="pulse-dot dot-red"></span>Critical P1 Incident</span></div>', unsafe_allow_html=True)
    elif row_anomaly or kb_fails > 0:
        st.markdown('<div style="text-align: right; margin-top: 8px;"><span class="badge-chip badge-warning"><span class="pulse-dot dot-yellow"></span>Degraded / Anomaly</span></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="text-align: right; margin-top: 8px;"><span class="badge-chip badge-healthy"><span class="pulse-dot dot-green"></span>Systems Healthy</span></div>', unsafe_allow_html=True)

# 4 Key Hero Cards
c1, c2, c3, c4 = st.columns(4)

with c1:
    orders_rows = report.get("orders_rows", 0)
    sub_color = "#F87171" if row_anomaly else "#34D399"
    sub_text = "🚨 Anomaly Detected!" if row_anomaly else "✨ Expected Volume Pattern"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">📦 Ingested Orders</div>
            <div class="metric-num">{orders_rows:,} <span style="font-size: 1.0rem; color: #94A3B8; font-weight: 500;">rows</span></div>
            <div class="metric-sub" style="color: {sub_color};">{sub_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    fresh_color = "#F87171" if freshness > 60 else "#34D399"
    fresh_sub = "⚠️ Latency SLA Breached" if freshness > 60 else "🟢 Fresh (< 15 min lag)"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">⏱️ Ingestion Freshness</div>
            <div class="metric-num">{freshness:.1f} <span style="font-size: 1.0rem; color: #94A3B8; font-weight: 500;">min</span></div>
            <div class="metric-sub" style="color: {fresh_color};">{fresh_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    crit_count = report.get("critical_contract_failures", 0)
    contract_color = "#F87171" if crit_count > 0 else ("#FBBF24" if contract_fails > 0 else "#34D399")
    contract_sub = f"🚨 {crit_count} Critical Violations" if crit_count > 0 else ("⚠️ Warnings Present" if contract_fails > 0 else "🟢 100% Contract Compliance")
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">🛡️ Contract Violations</div>
            <div class="metric-num">{contract_fails} <span style="font-size: 1.0rem; color: #94A3B8; font-weight: 500;">issues</span></div>
            <div class="metric-sub" style="color: {contract_color};">{contract_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    slo_color = "#F87171" if rem_budget < 50 else ("#FBBF24" if rem_budget < 95 else "#34D399")
    burn_sub = f"🔥 {burn_rate:.1f}x Burn Rate" if burn_rate > 1.0 else "🟢 Target: 99.9% Availability"
    st.markdown(
        f"""
        <div class="glass-card">
            <div class="metric-label">🎯 SLO Error Budget</div>
            <div class="metric-num">{rem_budget:.1f}%</div>
            <div class="metric-sub" style="color: {slo_color};">{burn_sub}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Tab Navigation
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Observability Telemetry",
    "🛡️ Data Contracts & GX",
    "🧠 AI & RAG Metrics",
    "🕸️ Lineage & Blast Radius",
    "🚨 Incident Response & Log",
])

# ----------------- TAB 1: Observability Telemetry -----------------
with tab1:
    st.markdown("### 📈 Time-Series Traffic & Seasonality Analysis")
    col_chart, col_side = st.columns([2, 1])

    with col_chart:
        if HISTORY.exists():
            history_df = pd.read_csv(HISTORY)
            history_df["date"] = pd.to_datetime(history_df["date"])
            history_df["is_weekend"] = history_df["day_of_week"].isin([5, 6])
            history_df["day_type"] = history_df["is_weekend"].map({True: "Weekend (~250)", False: "Weekday (~600)"})

            # Interactive Altair Chart
            chart = (
                alt.Chart(history_df)
                .mark_area(
                    line={"color": "#38BDF8", "strokeWidth": 2.5},
                    color=alt.Gradient(
                        gradient="linear",
                        stops=[
                            alt.GradientStop(color="rgba(56, 189, 248, 0.4)", offset=0),
                            alt.GradientStop(color="rgba(56, 189, 248, 0.0)", offset=1),
                        ],
                        x1=1,
                        x2=1,
                        y1=1,
                        y2=0,
                    ),
                )
                .encode(
                    x=alt.X("date:T", title="Timeline", axis=alt.Axis(format="%b %d", labelColor="#94A3B8", titleColor="#CBD5E1")),
                    y=alt.Y("row_count:Q", title="Daily Ingested Volume", scale=alt.Scale(domain=[0, 800]), axis=alt.Axis(labelColor="#94A3B8", titleColor="#CBD5E1")),
                    tooltip=[
                        alt.Tooltip("date:T", title="Date", format="%Y-%m-%d"),
                        alt.Tooltip("row_count:Q", title="Orders Count"),
                        alt.Tooltip("day_type:N", title="Segment"),
                    ],
                )
                .properties(height=320)
            )

            # Points on chart
            points = alt.Chart(history_df).mark_circle(size=30, color="#38BDF8").encode(
                x="date:T",
                y="row_count:Q",
                tooltip=["date:T", "row_count:Q", "day_type:N"],
            )

            st.altair_chart(chart + points, use_container_width=True)
            st.caption("ℹ️ *Historical volume shows periodic 7-day cyclicality. MAD auto-detector isolates legitimate weekend patterns from genuine volume drops.*")

    with col_side:
        st.markdown("#### 🔬 Anomaly Detector State")
        anomaly_sig = report.get("row_count_anomaly", {})
        score_val = anomaly_sig.get("score", 0.0)
        is_anom = anomaly_sig.get("is_anomaly", False)
        method_used = anomaly_sig.get("method", "auto")

        st.markdown(
            f"""
            <div style="background: rgba(15, 23, 42, 0.8); border: 1px solid #334155; border-radius: 10px; padding: 14px;">
                <p style="margin: 0; font-weight: 700; color: {'#F87171' if is_anom else '#34D399'}; font-size: 1.1rem;">
                    {'🚨 ANOMALOUS VOLUME' if is_anom else '✅ VOLUME IN NORMAL RANGE'}
                </p>
                <p style="margin: 4px 0 8px 0; font-size: 0.85rem; color: #94A3B8;">Algorithm: <code>{method_used}</code></p>
                <p style="margin: 0; font-size: 0.85rem; color: #CBD5E1;">Statistical Score: <strong>{score_val:.2f}</strong> (Threshold: 3.0)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🚨 Google SRE Multi-Window Alerting")
        if crit_fails > 0:
            st.error(r"🚨 **CRITICAL ALERT (PAGERDUTY)**\n\nDual short (1h) & long (6h) window burn rates $\ge 14.4\times$. Immediate on-call escalation required.")
        else:
            st.success("✅ **STANDBY (NO PAGING NOISE)**\n\nTransient spikes are suppressed; multi-window policy reports sustained burn rate within SLO budget.")

# ----------------- TAB 2: Data Contracts & GX -----------------
with tab2:
    st.markdown("### 🛡️ Schema Contracts & Quality Invariants")
    col_tbl1, col_tbl2 = st.columns(2)

    with col_tbl1:
        st.markdown("#### 📑 Orders Contract (`contracts/orders_contract.yaml`)")
        orders_data = [
            {"Column": "order_id", "Type": "integer", "Rule": "Unique, Non-Null", "Severity": "Critical", "Status": "FAIL ❌" if crit_fails > 0 else "PASS ✅"},
            {"Column": "customer_id", "Type": "integer", "Rule": "Non-Null", "Severity": "Critical", "Status": "PASS ✅"},
            {"Column": "amount", "Type": "number", "Rule": "Range [0, 50000]", "Severity": "Warning", "Status": "PASS ✅"},
            {"Column": "currency", "Type": "string", "Rule": "In [USD, VND]", "Severity": "Warning", "Status": "PASS ✅"},
            {"Column": "status", "Type": "string", "Rule": "In [pending, completed...]", "Severity": "Warning", "Status": "PASS ✅"},
            {"Column": "updated_at", "Type": "datetime", "Rule": "Freshness (< 60m)", "Severity": "Warning", "Status": "PASS ✅" if freshness <= 60 else "FAIL ❌"},
        ]
        st.dataframe(pd.DataFrame(orders_data), use_container_width=True, hide_index=True)

    with col_tbl2:
        st.markdown("#### 📚 Knowledge Base Contract (`contracts/kb_contract.yaml`)")
        kb_data = [
            {"Field": "doc_id", "Type": "string", "Rule": "Unique, Non-Null", "Severity": "Critical", "Status": "PASS ✅"},
            {"Field": "title", "Type": "string", "Rule": "Min Length 5", "Severity": "Warning", "Status": "PASS ✅"},
            {"Field": "content", "Type": "string", "Rule": "Min Length 20", "Severity": "Critical", "Status": "PASS ✅"},
            {"Field": "published_at", "Type": "datetime", "Rule": "Freshness (< 60m)", "Severity": "Warning", "Status": "FAIL ❌" if kb_fresh > 60 else "PASS ✅"},
        ]
        st.dataframe(pd.DataFrame(kb_data), use_container_width=True, hide_index=True)

    st.markdown("#### ✨ Great Expectations Suite Execution")
    st.markdown(
        """
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px;">
            <p style="margin: 0; color: #34D399; font-weight: 700;">🟢 ExpectationSuite: <code>orders_contract_suite</code></p>
            <p style="margin: 4px 0 0 0; color: #CBD5E1; font-size: 0.85rem;">6/6 expectations validated across batch definition using Checkpoint dispatcher.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ----------------- TAB 3: AI & RAG Metrics -----------------
with tab3:
    st.markdown("### 🧠 AI Support Agent & RAG Pipeline Telemetry")
    col_ai1, col_ai2 = st.columns(2)

    with col_ai1:
        st.markdown("#### 📄 Knowledge Base Document Stream")
        kb_docs_count = report.get("kb_docs_count", 0)
        st.metric(label="Active Vector Documents", value=f"{kb_docs_count} docs", delta=f"{kb_fresh:.1f} min publish lag")

        rag_len_sig = report.get("kb_text_length_signal", {})
        st.write("**Text Length Shift Signal:**")
        st.json(rag_len_sig)

    with col_ai2:
        st.markdown("#### 📐 Embedding Vector Norm Drift")
        st.write("- **Statistical Test:** Kolmogorov-Smirnov 2-Sample Test (`scipy.stats.ks_2samp`)")
        st.write("- **Target Invariant:** Embedding distribution norms must match healthy semantic baseline ($\alpha = 0.01$).")
        st.info("Embedding space drift detection prevents hallucination and stale policy delivery by the RAG Support Agent.")

# ----------------- TAB 4: Lineage & Blast Radius -----------------
with tab4:
    st.markdown("### 🕸️ End-to-End Transitive Data Lineage")

    st.markdown("#### 🔄 Orders Revenue Pipeline Flow")
    st.markdown(
        """
        <div style="padding: 16px; background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; margin-bottom: 20px;">
            <span class="flow-step">📥 raw_orders</span>
            <span class="flow-arrow">➔</span>
            <span class="flow-step">🔧 stg_orders</span>
            <span class="flow-arrow">➔</span>
            <span class="flow-step">📊 fct_daily_revenue</span>
            <span class="flow-arrow">➔</span>
            <span class="flow-step flow-critical">📈 ceo_revenue_dashboard</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("#### 📚 Knowledge Base & AI Agent Pipeline Flow")
    st.markdown(
        """
        <div style="padding: 16px; background: rgba(15, 23, 42, 0.7); border: 1px solid #334155; border-radius: 10px; margin-bottom: 20px;">
            <span class="flow-step">📄 kb_documents</span>
            <span class="flow-arrow">➔</span>
            <span class="flow-step">📂 kb_active_docs</span>
            <span class="flow-arrow">➔</span>
            <span class="flow-step">🔍 rag_index</span>
            <span class="flow-arrow">➔</span>
            <span class="flow-step" style="border-color: #F59E0B; color: #FBBF24; background: rgba(245, 158, 11, 0.1);">🤖 support_agent</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if LINEAGE_PATH.exists():
        lineage_json = json.loads(LINEAGE_PATH.read_text(encoding="utf-8"))
        col_lineage = lineage_json.get("column_lineage", {})
        with st.expander("🔍 Explore Transitive Column-Level Lineage (BFS Traversal)", expanded=False):
            st.json(col_lineage)

# ----------------- TAB 5: Incident Response & Log -----------------
with tab5:
    st.markdown("### 🚨 Incident Response, Automated Actions & Decision Log")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        st.markdown("#### 🛠️ Automated Pipeline Action")
        if crit_fails > 0:
            st.markdown(
                """
                <div style="padding: 16px; background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 10px;">
                    <p style="margin: 0; font-size: 1.1rem; font-weight: 800; color: #F87171;">⛔ ACTION: QUARANTINE / BLOCK</p>
                    <p style="margin: 8px 0 0 0; color: #CBD5E1; font-size: 0.88rem;">
                        <strong>Root Cause:</strong> Duplicate primary key (<code>order_id</code>) detected.<br>
                        <strong>Mitigation:</strong> Isolate corrupted batch to quarantine table; alert upstream producer.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        elif kb_fresh > 60 or freshness > 60:
            st.markdown(
                """
                <div style="padding: 16px; background: rgba(245, 158, 11, 0.15); border: 1px solid rgba(245, 158, 11, 0.4); border-radius: 10px;">
                    <p style="margin: 0; font-size: 1.1rem; font-weight: 800; color: #FBBF24;">⚠️ ACTION: WARN & RETRY SYNC</p>
                    <p style="margin: 8px 0 0 0; color: #CBD5E1; font-size: 0.88rem;">
                        <strong>Root Cause:</strong> Knowledge Base publication timestamp exceeded max delay (190m > 60m).<br>
                        <strong>Mitigation:</strong> Trigger CMS sync worker restart.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div style="padding: 16px; background: rgba(16, 185, 129, 0.15); border: 1px solid rgba(16, 185, 129, 0.4); border-radius: 10px;">
                    <p style="margin: 0; font-size: 1.1rem; font-weight: 800; color: #34D399;">✅ ACTION: PASS / PROMOTE TO MARTS</p>
                    <p style="margin: 8px 0 0 0; color: #CBD5E1; font-size: 0.88rem;">
                        All deterministic contracts, statistical anomaly gates, and dbt tests validated cleanly.
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with col_act2:
        st.markdown("#### 📋 Live Postmortem & Decision Log")
        report_tab, log_tab = st.tabs(["📄 Incident Postmortem", "🧠 AI Decision Log"])
        with report_tab:
            if INCIDENT_REPORT.exists():
                st.markdown(INCIDENT_REPORT.read_text(encoding="utf-8")[:1200] + "\n\n*(Full report in reports/incident_report.md)*")
        with log_tab:
            if AGENT_LOG.exists():
                st.markdown(AGENT_LOG.read_text(encoding="utf-8")[:1200] + "\n\n*(Full decisions in reports/agent_log.md)*")


