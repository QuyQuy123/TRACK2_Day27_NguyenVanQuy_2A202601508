from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "reports" / "latest_metrics.json"
HISTORY = ROOT / "data" / "history" / "metrics_history.csv"

st.set_page_config(page_title="Data Reliability Lab", layout="wide")
st.title("Data Reliability Game Day")
st.caption("Live Data Observability & Reliability Control Plane")

if not REPORT.exists():
    st.warning("Run `make baseline` first to generate reports/latest_metrics.json")
    st.stop()

report = json.loads(REPORT.read_text(encoding="utf-8"))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Orders rows", report.get("orders_rows", 0))
c2.metric("Orders Freshness", f"{report.get('freshness_minutes', 0):.1f} min")
c3.metric("Contract Failures", report.get("failed_contract_checks", 0))
c4.metric("Critical Failures", report.get("critical_contract_failures", 0))

k1, k2, k3 = st.columns(3)
k1.metric("KB Docs Count", report.get("kb_docs_count", 0))
k2.metric("KB Freshness", f"{report.get('kb_freshness_minutes', 0):.1f} min")
k3.metric("KB Failed Checks", report.get("kb_failed_checks", 0))

st.subheader("Observability & Signals")
s1, s2, s3 = st.columns(3)
with s1:
    st.write("**Row Count Anomaly Signal**")
    st.json(report.get("row_count_anomaly", {}))
with s2:
    st.write("**Knowledge Base Signals**")
    st.json(report.get("kb_text_length_signal", {}))
with s3:
    st.write("**SLO & Error Budget**")
    st.json(report.get("contract_slo", {}))

if HISTORY.exists():
    history = pd.read_csv(HISTORY)
    st.subheader("Historical Row Count")
    st.line_chart(history.set_index("date")[["row_count"]])

st.subheader("Transitive Blast Radius")
if "sample_blast_radius_from_stg_orders" in report:
    st.write("**Orders Pipeline:** `raw_orders` -> `stg_orders` -> " + " -> ".join(f"`{x}`" for x in report["sample_blast_radius_from_stg_orders"]))
if "sample_blast_radius_from_kb_documents" in report:
    st.write("**KB Pipeline:** `kb_documents` -> " + " -> ".join(f"`{x}`" for x in report["sample_blast_radius_from_kb_documents"]))

